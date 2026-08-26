"""An OpenAI-shaped stub that records what LibreChat actually sends.

The smoke test of design 021 D-G. The note's claims about which
`{{LIBRECHAT_USER_*}}` placeholders resolve come from reading the image's
source; this watches a request instead.

It records **whole requests** — headers and body — because the question is not
"do our headers arrive" but "what per-user signal reaches the endpoint at all":
our `X-Diffuse-User-*` headers, the body's own `user` field, both, or nothing.

It answers like an OpenAI endpoint so nothing upstream stalls: a mute receiver
makes a model picker hang, which looks like a UI problem and is not one.
Streaming is supported because a chat client asks for it by default.
"""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEL = "diffuse-smoke"
CAPTURE = "/capture/requests.jsonl"


def record(entry: dict) -> None:
    """Appends one request, and prints it, so both a file and the log have it."""
    line = json.dumps(entry, ensure_ascii=False)
    try:
        with open(CAPTURE, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass
    print(f"CAPTURED {line}", flush=True)


class Stub(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/").endswith("/models"):
            record({"at": time.time(), "path": self.path, "method": "GET",
                    "headers": dict(self.headers), "body": None})
            self._json({
                "object": "list",
                "data": [{"id": MODEL, "object": "model", "created": 0, "owned_by": "diffuse"}],
            })
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length).decode("utf-8", "replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw

        record({"at": time.time(), "path": self.path, "method": "POST",
                "headers": dict(self.headers), "body": body})

        wants_stream = isinstance(body, dict) and body.get("stream") is True
        if wants_stream:
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("cache-control", "no-cache")
            self.send_header("connection", "close")
            self.end_headers()
            for chunk in (
                {"id": "chatcmpl-smoke", "object": "chat.completion.chunk", "created": 0,
                 "model": MODEL,
                 "choices": [{"index": 0, "delta": {"role": "assistant", "content": "ok"},
                              "finish_reason": None}]},
                {"id": "chatcmpl-smoke", "object": "chat.completion.chunk", "created": 0,
                 "model": MODEL,
                 "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
            ):
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            return

        self._json({
            "id": "chatcmpl-smoke",
            "object": "chat.completion",
            "created": 0,
            "model": MODEL,
            "choices": [{"index": 0,
                         "message": {"role": "assistant", "content": "ok"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    def log_message(self, *args: object) -> None:
        """Silent: the capture above is the only output that matters."""


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8099), Stub).serve_forever()
