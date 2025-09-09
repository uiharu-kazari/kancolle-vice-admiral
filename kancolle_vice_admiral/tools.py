"""
Custom Browser Use tools.

Provides a deterministic canvas screenshot tool using CDP clip of the #game_frame iframe.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Optional

import asyncio
from loguru import logger

from .config import config

try:
    from browser_use.tools.service import Tools, ActionResult
except Exception as e:
    raise RuntimeError("browser-use Tools API not available") from e


tools = Tools()


@tools.action(description="Save a PNG screenshot of the #game_frame element after waiting a few seconds")
async def capture_canvas_frame(wait_seconds: int = 5, browser=None) -> ActionResult:
    """Deterministically screenshot the #game_frame iframe using Playwright element.screenshot()."""
    if browser is None:
        raise RuntimeError("Browser context not available for capture_canvas_frame")

    if wait_seconds and wait_seconds > 0:
        await asyncio.sleep(min(wait_seconds, 10))

    page = await browser.get_current_page()
    # Prefer the canvas inside the iframe to avoid top-level target CDP issues
    frame = page.frame(name="game_frame")
    if frame is None:
        raise RuntimeError("iframe 'game_frame' not accessible")
    canvas = await frame.query_selector('canvas')
    if canvas is None:
        # Fallback to visible iframe element if canvas not yet ready
        iframe_el = await page.query_selector('#game_frame')
        if iframe_el is None:
            raise RuntimeError("#game_frame not found")
        png = await iframe_el.screenshot()
    else:
        png = await canvas.screenshot()
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = config.paths.screenshots_dir / f"canvas_{ts}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(png)
    logger.info(f"🖼️ Canvas screenshot saved to {out_path}")
    return ActionResult(
        extracted_content=f"Saved canvas screenshot to {out_path}",
        include_in_memory=True,
        success=True,
        attachments=[str(out_path)],
    )


@tools.action(description="Save a PNG by executing JS canvas.toDataURL inside #game_frame")
async def capture_canvas_js(wait_seconds: int = 5, browser=None) -> ActionResult:
    """Use JS to extract the canvas pixels via toDataURL, avoiding CDP top-level constraints."""
    if browser is None:
        raise RuntimeError("Browser context not available for capture_canvas_js")

    if wait_seconds and wait_seconds > 0:
        await asyncio.sleep(min(wait_seconds, 10))

    page = await browser.get_current_page()
    frame = page.frame(name="game_frame")
    if frame is None:
        raise RuntimeError("iframe 'game_frame' not accessible")

    b64 = await frame.evaluate(
        "() => { const c = document.querySelector('canvas'); if (!c) return null; return c.toDataURL('image/png').split(',')[1]; }"
    )
    if not b64:
        raise RuntimeError("Canvas not found for JS capture")

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = config.paths.screenshots_dir / f"canvas_js_{ts}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(base64.b64decode(b64))

    logger.info(f"🖼️ Canvas (JS) screenshot saved to {out_path}")
    return ActionResult(
        extracted_content=f"Saved canvas (JS) screenshot to {out_path}",
        include_in_memory=True,
        success=True,
        attachments=[str(out_path)],
    )


