"""Logs what LibreChat actually sends, and answers like an OpenAI endpoint.

The smoke test of design 021 D-G. The note's claims about which
`{{LIBRECHAT_USER_*}}` placeholders resolve, and to what, come from reading the
image's source. This is the part that watches a request instead.

It prints every header whose name starts with `x-diffuse-`, raw and in the order
they arrived, then answers with the smallest thing an OpenAI client accepts so
the conversation completes and the test can send another.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        self.rfile.read(length)

        print("=== request ===", flush=True)
        for name, value in self.headers.items():
            if name.lower().startswith("x-diffuse-"):
                # `repr` on purpose: an empty header and an absent one are
                # different answers, and so are a literal template and a value.
                print(f"  {name}: {value!r}", flush=True)
        print("=== end ===", flush=True)

        body = {
            "id": "chatcmpl-smoke",
            "object": "chat.completion",
            "created": 0,
            "model": "diffuse-smoke",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        """Silent: the only output that matters is the header dump above."""


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8099), Receiver).serve_forever()
