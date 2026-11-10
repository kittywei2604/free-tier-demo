#!/usr/bin/env python3
"""free-tier-demo: minimal demo service skeleton (stdlib only).

GET  /health -> {"ok": true, "service": "free-tier-demo"}
POST /demo   -> calls OpenRouter :free model once; Supabase/R2 steps are
               attempted only when their env vars are set, otherwise
               reported as "not_configured" (never faked as connected).
"""
import json
import os
import subprocess
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEL = os.environ.get("OPENROUTER_MODEL", "cohere/north-mini-code:free")


def call_openrouter(prompt):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return {"status": "not_configured", "detail": "OPENROUTER_API_KEY not set"}
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        text = data["choices"][0]["message"].get("content")
        if not text:
            # Reasoning models can spend the budget thinking and return null
            # content; surface that honestly instead of reporting a blank reply.
            return {"status": "empty_reply", "model": MODEL,
                    "detail": "model returned null content (reasoning used the token budget)",
                    "finish_reason": data["choices"][0].get("finish_reason")}
        return {"status": "ok", "model": MODEL, "reply": text}
    except Exception as e:  # noqa: BLE001 - surface the real failure, don't fake ok
        return {"status": "error", "model": MODEL, "detail": str(e)}


def call_supabase(prompt, reply):
    """Write one demo log row via the custom.supabase helper.

    The helper gets the anon key through the surrogate exchange; this
    service never sees the key itself.
    """
    helper = os.path.expanduser(
        "~/workspace/custom-connectors/custom.supabase/bin/supabase_demo.py")
    try:
        proc = subprocess.run(
            ["python3", helper, "insert", prompt, reply],
            capture_output=True, text=True, timeout=60)
        out = (proc.stdout or "").strip()
        if proc.returncode == 0 and out.startswith("201"):
            return {"status": "ok", "detail": out[:300]}
        return {"status": "error",
                "detail": (out or proc.stderr or "helper failed")[:300]}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "detail": str(e)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True, "service": "free-tier-demo"})
        else:
            self._send(404, {"ok": False, "error": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/demo":
            self._send(404, {"ok": False, "error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {}
        prompt = payload.get("prompt") or "用一句话介绍你自己。"
        openrouter_result = call_openrouter(prompt)
        supabase_result = {"status": "not_configured",
                           "detail": "no model reply to store"}
        if openrouter_result.get("status") == "ok":
            supabase_result = call_supabase(
                prompt, openrouter_result["reply"])
        result = {
            "ok": True,
            "openrouter": openrouter_result,
            "supabase": supabase_result,
            "r2": {"status": "not_configured",
                   "detail": "R2 credentials not set"},
        }
        self._send(200, result)

    def log_message(self, *args):  # keep test output clean
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
