"""一键启动两版网页。

用法（项目根目录）：
    .venv\\Scripts\\python.exe start.py

同时启动：
- 第一版 app.py     -> http://localhost:8501
- 第二版 app_v2.py  -> http://localhost:8502（含结果标签页服务 8800）

按 Ctrl+C 结束两个服务。
"""
import os
import subprocess
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
APPS = [("app.py", 8501), ("app_v2.py", 8502)]


def main() -> None:
    procs = []
    for script, port in APPS:
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", script,
             "--server.port", str(port), "--server.headless", "true"],
            cwd=ROOT,
        ))

    # 等服务起来后再打开两个页面的标签
    def open_tabs() -> None:
        time.sleep(8)
        for _, port in APPS:
            webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=open_tabs, daemon=True).start()

    print("第一版：http://localhost:8501")
    print("第二版：http://localhost:8502")
    print("按 Ctrl+C 停止全部服务")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()
        print("已停止。")


if __name__ == "__main__":
    main()
