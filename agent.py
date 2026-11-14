#!/usr/bin/env python3
"""Local HTTP agent for exposing a project directory to CodeBridge."""

import argparse
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MAX_FILE_BYTES = 1024 * 1024
MAX_FILES = 2000


class CodeBridgeHandler(BaseHTTPRequestHandler):
    server_version = "CodeBridge/1.0"

    def _extension_origin(self):
        origin = self.headers.get("Origin", "")
        return origin if re.fullmatch(r"chrome-extension://[a-p]{32}", origin) else None

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        origin = self._extension_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        origin = self._extension_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"ok": True, "root": str(self.server.root)})
            return
        if parsed.path == "/files":
            self._list_files(parse_qs(parsed.query).get("path", [""])[0])
            return
        if parsed.path == "/file":
            self._read_file(parse_qs(parsed.query).get("path", [""])[0])
            return
        self._send_json(404, {"error": "Not found"})

    def _safe_path(self, relative):
        root = self.server.root
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("Path is outside the configured project")
        return candidate

    def _list_files(self, relative):
        try:
            directory = self._safe_path(relative)
            if not directory.is_dir():
                raise ValueError("Directory not found")
            files = []
            for path in directory.rglob("*"):
                if len(files) >= MAX_FILES:
                    break
                if any(part.startswith(".") for part in path.relative_to(self.server.root).parts):
                    continue
                if path.is_file():
                    files.append(str(path.relative_to(self.server.root)))
            self._send_json(200, {"files": sorted(files)})
        except (OSError, ValueError) as error:
            self._send_json(400, {"error": str(error)})

    def _read_file(self, relative):
        try:
            path = self._safe_path(relative)
            if not path.is_file():
                raise ValueError("File not found")
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError("File is larger than 1 MiB")
            content = path.read_text(encoding="utf-8")
            self._send_json(
                200,
                {
                    "path": str(path.relative_to(self.server.root)),
                    "content": content,
                    "language": mimetypes.guess_type(path.name)[0] or "text/plain",
                },
            )
        except (OSError, UnicodeDecodeError, ValueError) as error:
            self._send_json(400, {"error": str(error)})

    def log_message(self, *_):
        return


def create_server(root, host, port):
    server = ThreadingHTTPServer((host, port), CodeBridgeHandler)
    server.root = Path(root).expanduser().resolve()
    if not server.root.is_dir():
        raise ValueError("Project root must be a directory")
    return server


def main():
    parser = argparse.ArgumentParser(description="Serve project files to the CodeBridge extension")
    parser.add_argument("--root", default=".", help="Project directory to expose")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.root, args.host, args.port)
    print(f"CodeBridge serving {server.root} at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
