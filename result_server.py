"""生成结果标签页服务。

给第二版网页提供"生成完成后在新标签页展示结果"的能力：
- GET  /r/<token>     结果页（生成中则自动轮询，完成后刷新出内容）
- GET  /wait/<token>  状态 JSON，供结果页轮询
- GET  /a/<token>     结果页里的音频
- POST /close/<token> 标签页关闭通知；3 秒内没有新的页面请求则清理内容
                      （留出 3 秒是为了区分"刷新页面"与"关闭标签页"）
"""
import html
import json
import os
import shutil
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST, PORT = "127.0.0.1", 8800

_LOCK = threading.Lock()
_RESULTS: dict[str, dict] = {}        # token -> 结果记录
_CLOSE_TIMERS: dict[str, threading.Timer] = {}


def result_url(token: str) -> str:
    return f"http://{HOST}:{PORT}/r/{token}"


def create_result() -> str:
    """开始执行时占位：先开标签页再慢慢生成。"""
    token = uuid.uuid4().hex[:10]
    with _LOCK:
        _RESULTS[token] = {"status": "pending", "state": {}, "audio": ""}
    return token


def publish_result(token: str, state: dict) -> None:
    """生成完成后填充内容；音频复制一份独立文件，便于随标签页一起删除。"""
    audio = ""
    src = state.get("audio_path") or ""
    if src and os.path.exists(src):
        dst = os.path.join(os.path.dirname(os.path.abspath(src)), f"result_{token}.mp3")
        shutil.copyfile(src, dst)
        audio = dst
    with _LOCK:
        rec = _RESULTS.get(token)
        if rec is None:      # 标签页在生成期间就被关闭了
            return
        rec.update(status="ready", state=dict(state), audio=audio)


def _purge(token: str) -> None:
    """真正删除：结果记录 + 音频副本。"""
    with _LOCK:
        _CLOSE_TIMERS.pop(token, None)
        rec = _RESULTS.pop(token, None)
    if rec and rec.get("audio") and os.path.exists(rec["audio"]):
        try:
            os.remove(rec["audio"])
        except OSError:
            pass


def _request_close(token: str) -> None:
    with _LOCK:
        old = _CLOSE_TIMERS.pop(token, None)
        if old:
            old.cancel()
        timer = threading.Timer(3.0, _purge, args=(token,))
        _CLOSE_TIMERS[token] = timer
    timer.start()


def _cancel_close(token: str) -> None:
    """页面又请求了一次（如刷新），取消待删除状态。"""
    with _LOCK:
        timer = _CLOSE_TIMERS.pop(token, None)
    if timer:
        timer.cancel()


_PENDING_PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>生成中…</title>
<style>
body{{margin:0;background:#f4f5f7;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#1f2328;}}
.wrap{{max-width:760px;margin:56px auto;background:#fff;border:1px solid #e3e6ea;border-radius:6px;
padding:40px 28px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.05);}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;background:#d97706;margin-right:8px;
animation:pulse 1.1s infinite;}}
h2{{font-size:17px;font-weight:600;margin:0 0 10px;}}
p{{color:#8b929c;font-size:13px;margin:0;}}
@keyframes pulse{{0%,100%{{opacity:.2;}}50%{{opacity:1;}}}}
</style></head><body>
<div class="wrap"><h2><span class="dot"></span>内容生成中…</h2>
<p>完成后本页会自动刷新；关闭本标签页会取消本次结果。</p></div>
<script>
(function poll(){{
  fetch('/wait/{token}').then(function(r){{return r.json();}}).then(function(d){{
    if (d.status === 'ready') {{ location.reload(); }}
    else if (d.status === 'gone') {{ document.querySelector('.wrap h2').textContent = '内容已删除'; }}
    else {{ setTimeout(poll, 1200); }}
  }}).catch(function(){{ setTimeout(poll, 1500); }});
}})();
</script></body></html>"""

_CLOSED_PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>内容已删除</title>
<style>
body{margin:0;background:#f4f5f7;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#1f2328;}
.wrap{max-width:760px;margin:56px auto;background:#fff;border:1px solid #e3e6ea;border-radius:6px;
padding:40px 28px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.05);}
h2{font-size:17px;font-weight:600;margin:0 0 10px;}
p{color:#8b929c;font-size:13px;margin:0;}
</style></head><body>
<div class="wrap"><h2>内容已删除</h2><p>结果页关闭后，本次生成的内容已自动清理。</p></div>
</body></html>"""


def _build_result_page(token: str, rec: dict) -> str:
    state = rec.get("state", {})
    theme = html.escape(str(state.get("theme") or "")).strip()
    copy = html.escape(str(state.get("copy_text") or "")).strip()
    image = state.get("image_url") or ""
    has_audio = bool(rec.get("audio"))

    image_html = (
        f'<img src="{html.escape(image)}" alt="配图">'
        if image else '<div class="empty">（本次未生成图片）</div>'
    )
    audio_html = (
        f'<audio controls src="/a/{token}"></audio>'
        if has_audio else '<div class="empty">（本次未生成语音）</div>'
    )
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>生成结果</title>
<style>
body{{margin:0;background:#f4f5f7;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#1f2328;}}
.wrap{{max-width:760px;margin:32px auto;background:#fff;border:1px solid #e3e6ea;border-radius:6px;
overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05);}}
.bar{{padding:14px 20px;border-bottom:1px solid #eef0f2;font-size:15px;font-weight:600;}}
.body{{padding:18px 20px 24px;}}
h3{{font-size:13px;color:#8b929c;font-weight:600;margin:18px 0 8px;}}
.txt{{white-space:pre-wrap;line-height:1.8;font-size:15px;}}
img{{width:100%;border-radius:8px;border:1px solid #eef0f2;}}
audio{{width:100%;}}
.empty{{color:#9aa3ad;font-size:13px;}}
.foot{{padding:12px 20px;border-top:1px solid #eef0f2;color:#9aa3ad;font-size:12px;}}
</style></head><body>
<div class="wrap">
  <div class="bar">生成结果</div>
  <div class="body">
    <h3>主题</h3><div class="txt">{theme or '（无）'}</div>
    <h3>文案</h3><div class="txt">{copy or '（无）'}</div>
    <h3>配图</h3>{image_html}
    <h3>语音</h3>{audio_html}
  </div>
  <div class="foot">关闭本标签页后，本次生成的内容会自动删除。</div>
</div>
<script>
window.addEventListener('pagehide', function(){{
  navigator.sendBeacon('/close/{token}');
}});
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静默，避免刷 Streamlit 终端
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, code: int, text: str) -> None:
        self._send(code, text.encode("utf-8"), "text/html; charset=utf-8")

    def _json(self, code: int, data: dict) -> None:
        self._send(code, json.dumps(data).encode("utf-8"), "application/json")

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path.startswith("/r/"):
            token = path[3:]
            _cancel_close(token)      # 刷新页面会重新请求，说明没关闭
            with _LOCK:
                rec = _RESULTS.get(token)
            if rec is None:
                self._html(200, _CLOSED_PAGE)
            elif rec["status"] != "ready":
                self._html(200, _PENDING_PAGE.format(token=token))
            else:
                self._html(200, _build_result_page(token, rec))
        elif path.startswith("/wait/"):
            token = path[6:]
            with _LOCK:
                rec = _RESULTS.get(token)
            status = "gone" if rec is None else rec["status"]
            self._json(200, {"status": status})
        elif path.startswith("/a/"):
            token = path[3:]
            with _LOCK:
                rec = _RESULTS.get(token)
            audio = rec.get("audio") if rec else ""
            if audio and os.path.exists(audio):
                with open(audio, "rb") as f:
                    self._send(200, f.read(), "audio/mpeg")
            else:
                self._send(404, b"", "audio/mpeg")
        else:
            self._html(404, _CLOSED_PAGE)

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path.startswith("/close/"):
            _request_close(path[7:])
        self.send_response(204)
        self.end_headers()


def _start_server() -> None:
    try:
        server = ThreadingHTTPServer((HOST, PORT), _Handler)
    except OSError:
        return  # 端口已被占用：说明服务已在运行
    threading.Thread(target=server.serve_forever, daemon=True).start()


_start_server()
