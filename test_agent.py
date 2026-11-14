import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from agent import create_server


class AgentApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        (root / "src").mkdir()
        (root / "src/main.py").write_text("print('hello')", encoding="utf-8")
        (root / ".secret").write_text("hidden", encoding="utf-8")
        self.server = create_server(root, "127.0.0.1", 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.connection = HTTPConnection("127.0.0.1", self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def get(self, path):
        self.connection.request("GET", path)
        response = self.connection.getresponse()
        return response.status, json.loads(response.read())

    def test_lists_and_reads_project_files(self):
        status, listing = self.get("/files")
        self.assertEqual(status, 200)
        self.assertEqual(listing["files"], ["src/main.py"])

        status, file_data = self.get("/file?path=src/main.py")
        self.assertEqual(status, 200)
        self.assertEqual(file_data["content"], "print('hello')")

    def test_rejects_path_traversal(self):
        status, payload = self.get("/file?path=../outside")
        self.assertEqual(status, 400)
        self.assertIn("outside", payload["error"])


if __name__ == "__main__":
    unittest.main()
