"""Measure horizontal overflow at mobile/desktop widths via Chrome DevTools Protocol.

Launches headless Chrome with remote debugging, sets a mobile device metric
override, navigates to the page, and reports documentElement.scrollWidth vs the
viewport width. scrollWidth > innerWidth => horizontal overflow (bad on mobile).
"""
import json
import subprocess
import time
import urllib.request

import websocket  # websocket-client

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://localhost:3000/"
PORT = 9333
WIDTHS = [360, 390, 414, 768]

proc = subprocess.Popen(
    [CHROME, "--headless", "--disable-gpu", f"--remote-debugging-port={PORT}",
     "--remote-allow-origins=*",
     "--no-first-run", "--user-data-dir=" + r"C:\Users\shaan\AppData\Local\Temp\cdp-overflow",
     "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
try:
    # Wait for the debugging endpoint.
    ws_url = None
    for _ in range(50):
        try:
            data = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            pages = [t for t in data if t["type"] == "page"]
            if pages:
                ws_url = pages[0]["webSocketDebuggerUrl"]
                break
        except Exception:
            time.sleep(0.2)
    if not ws_url:
        raise SystemExit("could not reach CDP endpoint")

    ws = websocket.create_connection(ws_url, max_size=None)
    mid = 0

    def cmd(method, params=None):
        global mid
        mid += 1
        ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == mid:
                return msg

    cmd("Page.enable")
    for w in WIDTHS:
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": w, "height": 844, "deviceScaleFactor": 0, "mobile": w < 768})
        cmd("Page.navigate", {"url": URL})
        time.sleep(2.5)  # let it compile/render
        r = cmd("Runtime.evaluate", {
            "expression": "JSON.stringify({sw:document.documentElement.scrollWidth,"
                          "iw:window.innerWidth,"
                          "over:document.documentElement.scrollWidth-window.innerWidth})",
            "returnByValue": True})
        val = json.loads(r["result"]["result"]["value"])
        flag = "  <-- OVERFLOW" if val["over"] > 0 else "  ok"
        print(f"width={w:>4}  scrollWidth={val['sw']:>4}  innerWidth={val['iw']:>4}  overflow={val['over']:>3}px{flag}")
    ws.close()
finally:
    proc.terminate()
