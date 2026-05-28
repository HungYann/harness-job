"""Browser connection module - Direct CDP connection to Chrome (no proxy needed)."""
from __future__ import annotations

import json
import time
import threading
import uuid
from typing import Any

import httpx
from rich.console import Console

console = Console()

CDP_PROXY_URL = "http://localhost:3456"
CDP_DIRECT_URL = "http://localhost:9222"

# Aliases used by browser/session.py
CDP_DEFAULT_URL = CDP_DIRECT_URL
NAV_TIMEOUT_MS = 30_000  # 30 seconds


def check_chrome_connection(cdp_url: str | None = None) -> dict | None:
    """Check if Chrome debug port is accessible."""
    targets = [cdp_url] if cdp_url else [CDP_PROXY_URL, CDP_DIRECT_URL]

    for base in targets:
        for path in ("/health", "/json/version"):
            try:
                resp = httpx.get(f"{base.rstrip('/')}{path}", timeout=3)
                if resp.status_code == 200:
                    return resp.json()
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
    return None


def get_page_targets() -> list[dict]:
    """Get list of page targets — tries CDP Proxy then falls back to direct Chrome port."""
    # Try CDP Proxy first
    try:
        resp = httpx.get(f"{CDP_PROXY_URL}/targets", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: query Chrome directly
    for path in ("/json/list", "/json"):
        try:
            resp = httpx.get(f"{CDP_DIRECT_URL}{path}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
    return []


def find_boss_tab() -> dict | None:
    """Find a 某直聘 tab in Chrome."""
    targets = get_page_targets()
    for target in targets:
        url = target.get("url", "")
        if "zhipin.com" in url:
            return target
    return None


def new_tab(url: str) -> str | None:
    """Open a new tab, navigate to url, and return target ID."""
    # Try CDP Proxy first
    try:
        resp = httpx.get(f"{CDP_PROXY_URL}/new", params={"url": url}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("targetId")
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: direct Chrome — open blank tab then navigate via CDP
    try:
        resp = httpx.put(f"{CDP_DIRECT_URL}/json/new", params={"url": "about:blank"}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            target_id = data.get("id")
            ws_url = data.get("webSocketDebuggerUrl")
            if target_id and ws_url:
                # Give Chrome a moment to set up the target
                time.sleep(0.3)
                _cdp_send(ws_url, "Page.navigate", {"url": url}, timeout=15)
                return target_id
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    return None


def close_tab(target_id: str) -> bool:
    """Close a tab by target ID."""
    # Try CDP Proxy first
    try:
        resp = httpx.get(f"{CDP_PROXY_URL}/close", params={"target": target_id}, timeout=5)
        if resp.status_code == 200:
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: direct Chrome
    try:
        resp = httpx.get(f"{CDP_DIRECT_URL}/json/close/{target_id}", timeout=5)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _get_ws_url(target_id: str) -> str | None:
    """Get WebSocket debugger URL for a target."""
    try:
        resp = httpx.get(f"{CDP_DIRECT_URL}/json/list", timeout=5)
        if resp.status_code == 200:
            for t in resp.json():
                if t.get("id") == target_id:
                    return t.get("webSocketDebuggerUrl")
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    return None


def _cdp_send(ws_url: str, method: str, params: dict | None = None, timeout: float = 30) -> Any:
    """Send a single CDP command over WebSocket and return the result."""
    try:
        import websocket  # websocket-client
    except ImportError:
        console.print("[red]缺少 websocket-client：pip3 install websocket-client[/red]")
        return None

    msg_id = 1
    payload = json.dumps({"id": msg_id, "method": method, "params": params or {}})
    result_holder: list[Any] = []
    done_event = threading.Event()

    def on_open(ws):
        ws.send(payload)

    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("id") == msg_id:
                if "result" in data:
                    result_holder.append(data["result"])
                done_event.set()
                ws.close()
        except Exception:
            pass

    def on_error(ws, error):
        done_event.set()

    def on_close(ws, *args):
        done_event.set()

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    t = threading.Thread(
        target=ws.run_forever,
        kwargs={"ping_interval": 0},
        daemon=True,
    )
    t.start()
    done_event.wait(timeout=timeout)

    if result_holder:
        return result_holder[0]
    return None


def navigate(target_id: str, url: str) -> bool:
    """Navigate a tab to a URL."""
    # Try CDP Proxy first
    try:
        resp = httpx.get(
            f"{CDP_PROXY_URL}/navigate",
            params={"target": target_id, "url": url},
            timeout=15
        )
        if resp.status_code == 200:
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: direct CDP WebSocket
    ws_url = _get_ws_url(target_id)
    if not ws_url:
        return False
    result = _cdp_send(ws_url, "Page.navigate", {"url": url}, timeout=15)
    return result is not None


def evaluate(target_id: str, expression: str, timeout: float = 30) -> Any:
    """Execute JavaScript in a tab."""
    # Try CDP Proxy first
    try:
        resp = httpx.post(
            f"{CDP_PROXY_URL}/eval",
            params={"target": target_id},
            content=expression,
            timeout=timeout
        )
        if resp.status_code == 200:
            if not resp.content:
                return None
            try:
                data = resp.json()
            except (ValueError, TypeError):
                return None
            return data.get("value")
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: direct CDP WebSocket
    ws_url = _get_ws_url(target_id)
    if not ws_url:
        return None
    result = _cdp_send(
        ws_url,
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": False},
        timeout=timeout,
    )
    if result is None:
        return None
    rv = result.get("result", {})
    if rv.get("type") == "string":
        return rv.get("value")
    return rv.get("value")


def click(target_id: str, selector: str) -> bool:
    """Click an element by CSS selector."""
    # Try CDP Proxy first
    try:
        resp = httpx.post(
            f"{CDP_PROXY_URL}/click",
            params={"target": target_id},
            content=selector,
            timeout=10
        )
        if resp.status_code == 200:
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: click via JS eval
    js = f"""
    (() => {{
        const el = document.querySelector({json.dumps(selector)});
        if (el) {{ el.click(); return true; }}
        return false;
    }})()
    """
    result = evaluate(target_id, js, timeout=10)
    return bool(result)


def scroll(target_id: str, y: int = 0, direction: str = "") -> bool:
    """Scroll a page."""
    # Try CDP Proxy first
    try:
        params: dict[str, Any] = {"target": target_id}
        if direction:
            params["direction"] = direction
        else:
            params["y"] = y
        resp = httpx.get(f"{CDP_PROXY_URL}/scroll", params=params, timeout=5)
        if resp.status_code == 200:
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: JS scroll
    if direction == "bottom":
        js = "window.scrollTo(0, document.body.scrollHeight); true"
    elif direction == "top":
        js = "window.scrollTo(0, 0); true"
    else:
        js = f"window.scrollTo(0, {y}); true"
    result = evaluate(target_id, js, timeout=5)
    return result is not None


def get_page_info(target_id: str) -> dict | None:
    """Get page title and URL."""
    # Try CDP Proxy first
    try:
        resp = httpx.get(
            f"{CDP_PROXY_URL}/info",
            params={"target": target_id},
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        pass
    # Fallback: JS eval
    js = """
    JSON.stringify({
        title: document.title,
        url: location.href,
        ready: document.readyState
    })
    """
    result = evaluate(target_id, js, timeout=5)
    if not result:
        return None
    try:
        data = json.loads(result) if isinstance(result, str) else result
        return data
    except (json.JSONDecodeError, TypeError):
        return None


def wait_for_load(target_id: str, timeout: float = 10.0) -> bool:
    """Wait for page to finish loading (skips about:blank intermediate states)."""
    start = time.time()
    while time.time() - start < timeout:
        info = get_page_info(target_id)
        if info and info.get("ready") == "complete":
            url = info.get("url", "")
            if url and url != "about:blank":
                return True
        time.sleep(0.5)
    return False
