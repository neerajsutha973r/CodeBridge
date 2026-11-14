import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import json
import shutil
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765

ALLOWED_ORIGIN = "chrome-extension://bgpbkggfcbeghfbfknomhlkgencjplgk"


def get_safe_file_path(project_folder, requested_file):
    project_root = Path(project_folder).resolve()
    requested_path = (project_root / requested_file).resolve()

    try:
        requested_path.relative_to(project_root)
    except ValueError:
        raise ValueError("Access outside the selected project is forbidden.")

    if requested_path == project_root:
        raise ValueError("A file path is required.")

    return requested_path


def create_backup(file_path):
    if not file_path.exists():
        return None

    if not file_path.is_file():
        raise ValueError("Target path is not a file.")

    backup_folder = file_path.parent / ".codebridge_backups"
    backup_folder.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    backup_path = backup_folder / (
        file_path.name + "." + timestamp + ".bak"
    )

    shutil.copy2(file_path, backup_path)

    print("Backup created:", backup_path)

    return backup_path


import ast


def replace_python_code(file_path, target, new_code):
    if file_path.suffix.lower() != ".py":
        raise ValueError("Currently only Python files are supported.")

    # Validate the incoming Python code before modifying anything.
    try:
        new_tree = ast.parse(new_code)
    except SyntaxError as error:
        raise ValueError(
            f"New code contains a syntax error: {error}"
        )

    if target == "entire_file":
        updated_content = new_code.rstrip() + "\n"

    else:
        try:
            original_content = file_path.read_text(encoding="utf-8")
            original_tree = ast.parse(original_content)
        except SyntaxError as error:
            raise ValueError(
                f"Existing file has a syntax error: {error}"
            )

        matching_functions = [
            node for node in ast.walk(original_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == target
        ]

        if len(matching_functions) != 1:
            raise ValueError(
                f"Expected exactly one function named '{target}', "
                f"found {len(matching_functions)}."
            )

        new_functions = [
            node for node in ast.walk(new_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == target
        ]

        if len(new_functions) != 1:
            raise ValueError(
                f"New code must contain exactly one function named '{target}'."
            )

        function = matching_functions[0]

        start_line = function.lineno

        if function.decorator_list:
            start_line = min(
                decorator.lineno for decorator in function.decorator_list
            )

        lines = original_content.splitlines(keepends=True)

        updated_lines = (
            lines[:start_line - 1]
            + new_code.rstrip().splitlines(keepends=True)
            + ["\n"]
            + lines[function.end_lineno:]
        )

        updated_content = "".join(updated_lines)

    # Validate the complete updated file before saving.
    try:
        ast.parse(updated_content)
    except SyntaxError as error:
        raise ValueError(
            f"Updated file would contain a syntax error: {error}"
        )

    backup_path = create_backup(file_path)

    file_path.write_text(updated_content, encoding="utf-8")

    return backup_path



def insert_python_code(file_path, target, new_code):
    if file_path.suffix.lower() != ".py":
        raise ValueError("Currently only Python files are supported.")

    # Validate incoming Python code.
    try:
        new_tree = ast.parse(new_code)
    except SyntaxError as error:
        raise ValueError(f"New code contains a syntax error: {error}")

    # Read and validate the existing file.
    try:
        original_content = file_path.read_text(encoding="utf-8")
        original_tree = ast.parse(original_content)
    except SyntaxError as error:
        raise ValueError(f"Existing file has a syntax error: {error}")

    # Find function names in the new code.
    new_function_names = {
        node.name
        for node in ast.walk(new_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    # Prevent duplicate function names anywhere in the existing file.
    existing_function_names = {
        node.name
        for node in ast.walk(original_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    duplicates = new_function_names & existing_function_names

    if duplicates:
        raise ValueError(
            "Function already exists: " + ", ".join(sorted(duplicates))
        )

    lines = original_content.splitlines(keepends=True)
    new_code_block = new_code.strip() + "\n"

    if target == "beginning":
        updated_content = new_code_block + "\n" + original_content

    elif target == "end":
        separator = (
            "\n"
            if original_content and not original_content.endswith("\n\n")
            else ""
        )
        updated_content = original_content + separator + new_code_block

    elif target.startswith("after:"):
        function_name = target[len("after:"):].strip()

        if not function_name:
            raise ValueError("Function name is missing after 'after:'.")

        # Only allow a top-level function as the insertion target.
        matching_functions = [
            node for node in original_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ]

        if len(matching_functions) != 1:
            raise ValueError(
                f"Expected exactly one top-level function named "
                f"'{function_name}', found {len(matching_functions)}."
            )

        function = matching_functions[0]
        insert_index = function.end_lineno

        updated_lines = (
            lines[:insert_index]
            + ["\n"]
            + (new_code_block + "\n").splitlines(keepends=True)
            + lines[insert_index:]
        )

        updated_content = "".join(updated_lines)

    else:
        raise ValueError(
            "Invalid INSERT target. Use beginning, end, or after:function_name."
        )

    # Validate the complete updated file before saving.
    try:
        ast.parse(updated_content)
    except SyntaxError as error:
        raise ValueError(
            f"Inserted code would cause a syntax error: {error}"
        )

    # Create backup before modifying the file.
    backup_path = create_backup(file_path)

    file_path.write_text(updated_content, encoding="utf-8")

    return backup_path


def create_python_file(file_path, new_code):
    # Only Python files are supported for now.
    if file_path.suffix.lower() != ".py":
        raise ValueError("Currently only Python files are supported.")

    # Validate Python syntax before creating anything.
    try:
        ast.parse(new_code)
    except SyntaxError as error:
        raise ValueError(
            f"New file contains a syntax error: {error}"
        )

    # Refuse to overwrite an existing file.
    if file_path.exists():
        raise ValueError(
            f"File already exists: {file_path.name}"
        )

    # Create missing parent directories.
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Use exclusive creation to prevent accidental overwriting.
    try:
        with file_path.open("x", encoding="utf-8") as new_file:
            new_file.write(new_code.rstrip() + "\n")
    except FileExistsError:
        raise ValueError(
            f"File already exists: {file_path.name}"
        )

    return None

def get_project_tree(project_folder, max_depth=4):
    ignored_folders = {
        ".git",
        ".codebridge_backups",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv"
    }

    def scan_folder(folder, depth):
        items = []

        if depth > max_depth:
            return items

        try:
            entries = sorted(
                folder.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower())
            )
        except PermissionError:
            return items

        for entry in entries:
            if entry.is_symlink():
                continue

            if entry.is_dir():
                if entry.name in ignored_folders:
                    continue

                items.append({
                    "name": entry.name,
                    "type": "folder",
                    "children": scan_folder(entry, depth + 1)
                })

            elif entry.is_file():
                items.append({
                    "name": entry.name,
                    "type": "file"
                })

        return items

    return {
        "project": project_folder.name,
        "tree": scan_folder(project_folder, 0)
    }

class CodeBridgeHandler(BaseHTTPRequestHandler):

    def send_json(self, status, data):
        response = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_json(200, {"status": "ok"})


    def do_GET(self):
        if self.path == "/":
            self.send_json(200, {
                "status": "running",
                "agent": "CodeBridge"
            })

        elif self.path == "/project-tree":
            try:
                project_data = get_project_tree(PROJECT_FOLDER)

                self.send_json(200, {
                    "status": "DONE",
                    **project_data
                })

            except Exception as error:
                self.send_json(500, {
                    "status": "ERROR",
                    "error": str(error)
                })

        else:
            self.send_json(404, {
                "status": "ERROR",
                "error": "Unknown endpoint"
            })



    def do_POST(self):
        if self.path != "/instruction":
            self.send_json(404, {"error": "Unknown endpoint"})
            return

        origin = self.headers.get("Origin")

        if origin != ALLOWED_ORIGIN:
            self.send_json(403, {"error": "Origin not allowed"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))

            if length <= 0 or length > 1024 * 1024:
                self.send_json(400, {"error": "Invalid request size"})
                return

            body = self.rfile.read(length)
            instruction = json.loads(body.decode("utf-8"))

            action = instruction.get("action")
            file = instruction.get("file")
            target = instruction.get("target")
            code = instruction.get("code")

            if action not in ("INSERT", "REPLACE","CREATE","DELETE"):
                raise ValueError("Invalid action")

            if not all(
                isinstance(value, str) and value.strip()
                for value in (file, target, code)
            ):
                raise ValueError("Missing instruction details")

            print("\n--- CodeBridge instruction received ---")
            print("Action:", action)
            print("File:", file)
            print("Target:", target)

            # Resolve and validate the requested file path.
            file_path = get_safe_file_path(PROJECT_FOLDER, file)

            if action != "CREATE" and not file_path.parent.is_dir():
                raise ValueError("Target directory does not exist.")

            # Execute the requested operation.
            if action == "REPLACE":
                backup_path = replace_python_code(
                    file_path,
                    target,
                    code
                )

            elif action == "INSERT":
                backup_path = insert_python_code(
                    file_path,
                    target,
                    code
                )

            elif action == "CREATE":
                if target != "new_file":
                    raise ValueError("CREATE target must be 'new_file'.")

                backup_path = create_python_file(
                    file_path,
                    code
                )

            elif action == "DELETE":
                if target != "confirm_delete":
                    raise ValueError("DELETE target must be 'confirm_delete'.")

                if code != "CONFIRM":
                    raise ValueError("DELETE requires code CONFIRM.")

                backup_path = delete_python_file(file_path)

            print("Code successfully updated!")
            print("File:", file_path)
            print("Backup:", backup_path)

            self.send_json(200, {
                "status": "DONE",
                "message": "File updated successfully",
                "file": str(file_path),
                "target": target,
                "backup": str(backup_path) if backup_path else None
            })

        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError
        ) as error:
            print("CodeBridge error:", error)
            self.send_json(400, {"error": str(error)})


    def log_message(self, format, *args):
        print("[CodeBridge]", format % args)


def delete_python_file(file_path):
    # Only Python files are supported.
    if file_path.suffix.lower() != ".py":
        raise ValueError("Currently only Python files can be deleted.")

    # Refuse to delete missing files.
    if not file_path.exists():
        raise ValueError(f"File does not exist: {file_path.name}")

    # Refuse to delete directories.
    if not file_path.is_file():
        raise ValueError("Target path is not a file.")

    # Create a backup before deletion.
    backup_path = create_backup(file_path)

    if backup_path is None:
        raise ValueError("Backup creation failed. File was not deleted.")

    # Delete only after backup succeeds.
    file_path.unlink()

    print("File deleted:", file_path)
    print("Backup preserved:", backup_path)

    return backup_path


def select_project_folder():
    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(
        title="Select your CodeBridge project folder"
    )

    root.destroy()

    if not folder:
        print("No project folder selected. Exiting.")
        return None

    project_path = Path(folder).resolve()

    print("\nProject folder selected:")
    print(project_path)
    return project_path

if __name__ == "__main__":
    PROJECT_FOLDER = select_project_folder()

    if PROJECT_FOLDER is None:
        raise SystemExit("CodeBridge stopped.")

    server = ThreadingHTTPServer((HOST, PORT), CodeBridgeHandler)

    print("================================")
    print("       CodeBridge Agent")
    print("================================")
    print("Selected project:", PROJECT_FOLDER)
    print(f"Server running at http://{HOST}:{PORT}")
    print("Waiting for Chrome instructions...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping CodeBridge...")
    finally:
        server.server_close()
