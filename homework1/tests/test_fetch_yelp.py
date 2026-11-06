"""Exercise interrupted HTTP range resume and nested gzip/tar extraction locally."""
import contextlib
import hashlib
import http.server
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location("fetch_yelp", Path(__file__).parents[1] / "src/fetch_yelp.py")
fetch_yelp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_yelp)


class YelpDownloadTests(unittest.TestCase):
    def test_interrupted_range_resumes_and_extracts_exact_reviews(self):
        review = b'{"text":"hello hadoop"}\n'
        nested = io.BytesIO()
        with tarfile.open(fileobj=nested, mode="w:gz") as archive:
            member = tarfile.TarInfo("yelp_academic_dataset_review.json")
            member.size = len(review)
            archive.addfile(member, io.BytesIO(review))
        package = io.BytesIO()
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("Yelp JSON/yelp_dataset.tar", nested.getvalue())
        data, starts = package.getvalue(), []

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_HEAD(self):
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("ETag", '"test-version"')
                self.end_headers()

            def do_GET(self):
                match = re.fullmatch(r"bytes=(\d+)-(\d+)", self.headers["Range"])
                start, end = map(int, match.groups())
                starts.append(start)
                self.send_response(206)
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, len(data)))
                self.send_header("Content-Length", str(end - start + 1))
                self.end_headers()
                # Deliberately close the first response before Content-Length.
                self.wfile.write(data[start:start + 31] if len(starts) == 1 else data[start:end + 1])

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "reviews.json"
                argv = ["fetch_yelp", "--directory", str(Path(directory) / "downloads"),
                        "--output", str(output), "--connections", "1"]
                url = "http://127.0.0.1:%d/input.zip" % server.server_port
                with mock.patch.object(fetch_yelp, "URL", url), mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                    fetch_yelp.main()
                self.assertEqual(starts, [0, 31])
                self.assertEqual(output.read_bytes(), review)
                manifest = json.loads(output.with_name(output.name + ".manifest.json").read_text())
                self.assertEqual(manifest["review_sha256"], hashlib.sha256(review).hexdigest())
                self.assertEqual(manifest["zip_sha256"], hashlib.sha256(data).hexdigest())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
