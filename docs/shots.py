"""
Capture the two README images from the running production site.

Drives the Chrome that is already on this machine over the DevTools Protocol:
no install, no headless browser download, and no staging. The feed shot waits
until the four tiles carry real numbers, because a capture mid load shows
dashes. The linter shot types the promise that payment p-000014 ran on chain
and waits for the refusal, so the image, the README's linter section and the
case record tell one story.
"""

from __future__ import annotations

import asyncio
import base64
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333
SITE = "http://localhost:4500/"
PROMISE = "Returns accurate market data."
OUT = pathlib.Path("G:/GenLayer Works/GenLayer Cards/GenLayerCard/Recourse/docs/images")
PROFILE = pathlib.Path("C:/Users/Mahdi/AppData/Local/Temp/claude/shot-profile")


class Tab:
    def __init__(self, ws):
        self.ws = ws
        self.n = 0

    async def send(self, method: str, **params):
        self.n += 1
        await self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            message = json.loads(await self.ws.recv())
            if message.get("id") == self.n:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    async def js(self, expression: str):
        result = await self.send(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"].get("text", "js failed"))
        return result["result"].get("value")

    async def wait_for(self, expression: str, what: str, seconds: int = 60):
        deadline = time.time() + seconds
        while time.time() < deadline:
            if await self.js(expression):
                return
            await asyncio.sleep(0.5)
        raise TimeoutError(f"timed out waiting for {what}")

    async def shot(self, box: dict, path: pathlib.Path, scale: float = 2.0):
        result = await self.send(
            "Page.captureScreenshot",
            format="png",
            captureBeyondViewport=True,
            clip={
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"],
                "scale": scale,
            },
        )
        path.write_bytes(base64.b64decode(result["data"]))
        print(f"  wrote {path.name}  {box['width']:.0f}x{box['height']:.0f} css px at {scale}x")


# React tracks its own value on the input node, so assigning .value directly is
# ignored on the next render. This is the documented way round it.
SET_VALUE = """
(() => {
  const box = document.querySelector('#rc-promise');
  const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
  setter.call(box, %s);
  box.dispatchEvent(new Event('input', { bubbles: true }));
  return box.value;
})()
"""


async def main() -> int:
    PROFILE.mkdir(parents=True, exist_ok=True)
    chrome = subprocess.Popen([
        CHROME,
        "--headless=new",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFILE}",
        "--window-size=1600,1200",
        "--force-device-scale-factor=1",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        endpoint = None
        for _ in range(40):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1) as reply:
                    endpoint = json.loads(reply.read())["webSocketDebuggerUrl"]
                break
            except Exception:
                time.sleep(0.5)
        if not endpoint:
            print("chrome did not open its debugging port")
            return 1

        # Newer Chrome requires PUT for /json/new.
        open_tab = urllib.request.Request(
            f"http://127.0.0.1:{PORT}/json/new?{SITE}", method="PUT",
        )
        with urllib.request.urlopen(open_tab, timeout=5) as reply:
            target = json.loads(reply.read())
        async with websockets.connect(target["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024) as ws:
            tab = Tab(ws)
            await tab.send("Page.enable")
            await tab.send("Runtime.enable")
            await tab.send("Emulation.setDeviceMetricsOverride",
                           width=1600, height=1200, deviceScaleFactor=1, mobile=False)

            # --- the feed ---------------------------------------------------
            await tab.send("Page.navigate", url=SITE)
            await asyncio.sleep(3)
            await tab.wait_for(
                "!!document.getElementById('feed') && "
                "/\\d/.test(document.getElementById('feed').textContent) && "
                "!document.getElementById('feed').textContent.includes('Reading the chain')",
                "the feed tiles to carry numbers",
            )
            # Each tile is a number with its label beneath it.
            tiles = await tab.js(
                "[...document.querySelectorAll('#feed div')]"
                ".filter(d => d.style.fontVariantNumeric === 'tabular-nums')"
                ".slice(0,4).map(d => [d.nextElementSibling.textContent.trim(), d.textContent.trim()])"
            )
            print(f"  feed tiles read: {' '.join(value for _, value in tiles)}")
            await asyncio.sleep(1.5)
            box = await tab.js(
                "(() => { const r = document.getElementById('feed').getBoundingClientRect();"
                " return { x: r.x + window.scrollX, y: r.y + window.scrollY,"
                " width: r.width, height: r.height }; })()"
            )
            await tab.shot(box, OUT / "feed.png")
            # A photograph of the chain is true the day it is taken and goes
            # false with nothing failing. What it shows is written beside it,
            # so tests/direct/test_snapshot.py can hold it to the snapshot.
            (OUT / "feed.json").write_text(json.dumps({
                "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tiles": dict(tiles),
            }, indent=2) + "\n", encoding="utf-8")
            print("  wrote feed.json  what the tiles read")

            # --- the linter, refusing ---------------------------------------
            await tab.send("Page.navigate", url=SITE)
            await asyncio.sleep(3)
            # The textarea is in the server rendered HTML before React has
            # hydrated it, so waiting for the element is waiting too early:
            # anything typed then is discarded on hydration. Wait for React to
            # have claimed the node.
            await tab.wait_for(
                "(() => { const box = document.querySelector('#rc-promise');"
                " return !!box && !!Object.keys(box).find(k => k.startsWith('__react')); })()",
                "the linter panel to hydrate",
                seconds=30,
            )
            # Typed the way a person types it. Setting .value and firing an
            # input event is the usual trick and React ignored it here, so this
            # goes through the input pipeline instead and is closer to the
            # thing being photographed anyway.
            await tab.js("document.querySelector('#rc-promise').focus()")
            await tab.send("Input.insertText", text=PROMISE)
            await asyncio.sleep(0.5)
            typed = await tab.js("document.querySelector('#rc-promise').value")
            print(f"  typed: {typed}")
            await tab.wait_for(
                "(() => { const b = document.querySelector('#rc-promise').closest('form')"
                ".querySelector('button[type=submit]'); return b && !b.disabled; })()",
                "the submit button to enable",
                seconds=15,
            )
            clicked = await tab.js(
                "(() => { const b = document.querySelector('#rc-promise').closest('form')"
                ".querySelector('button[type=submit]'); b.click();"
                " return b.textContent.trim(); })()"
            )
            print(f"  clicked: {clicked}")
            await tab.wait_for(
                "document.body.textContent.includes('Not judgeable')",
                "the refusal",
                seconds=90,
            )
            reason = await tab.js(
                "(() => { const t = document.body.textContent;"
                " const i = t.indexOf('Not judgeable');"
                " return t.slice(i, i + 180).trim(); })()"
            )
            print(f"  panel says: {reason[:120]}")
            await asyncio.sleep(1.0)
            # The panel from the form down, not from the wordmark: the
            # picture is of the linter refusing, and the hero's headline is a
            # different picture.
            box = await tab.js(
                "(() => {"
                " const form = document.querySelector('#rc-promise').closest('form');"
                " const panel = form.parentElement;"
                " const f = form.getBoundingClientRect();"
                " const p = panel.getBoundingClientRect();"
                " const pad = 26;"
                " return { x: Math.max(0, p.x + window.scrollX - pad),"
                " y: f.y + window.scrollY - pad,"
                " width: p.width + pad * 2,"
                " height: (p.bottom - f.top) + pad * 2 }; })()"
            )
            await tab.shot(box, OUT / "linter.png")
        return 0
    finally:
        chrome.terminate()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
