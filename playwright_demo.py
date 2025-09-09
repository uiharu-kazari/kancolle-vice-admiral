import os
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types
from loguru import logger


def detect_game_start_center(img_path: Path) -> tuple[int, int] | None:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY/GOOGLE_API_KEY not set; skipping LLM detection")
        return None

    client = genai.Client(api_key=api_key)

    response_schema = {
        'type': 'OBJECT',
        'properties': {
            'boxes': {
                'type': 'ARRAY',
                'items': {
                    'type': 'OBJECT',
                    'properties': {
                        'label': {'type': 'STRING'},
                        'xywh': {'type': 'ARRAY', 'items': {'type': 'INTEGER'}},
                        'score': {'type': 'NUMBER'},
                    },
                },
            },
            'centers': {
                'type': 'ARRAY',
                'items': {
                    'type': 'OBJECT',
                    'properties': {
                        'label': {'type': 'STRING'},
                        'cx': {'type': 'INTEGER'},
                        'cy': {'type': 'INTEGER'},
                        'score': {'type': 'NUMBER'},
                    },
                },
            },
        },
        'required': ['boxes', 'centers'],
    }

    with open(img_path, 'rb') as f:
        image_bytes = f.read()

    image_part = types.Part.from_bytes(data=image_bytes, mime_type='image/png')
    prompt = "Return JSON with the 'game start' button location. Include centers (cx,cy). Label as 'game start'."
    resp = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image_part, prompt],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_json_schema=response_schema,
        ),
    )
    text = resp.text or '{}'
    try:
        data = json.loads(text)
    except Exception:
        logger.warning(f"LLM returned non-JSON: {text[:200]}")
        return None

    centers = data.get('centers') or []
    if centers:
        c0 = centers[0]
        cx, cy = c0.get('cx'), c0.get('cy')
        if isinstance(cx, int) and isinstance(cy, int):
            logger.info(f"LLM center: ({cx}, {cy})")
            return cx, cy

    boxes = data.get('boxes') or []
    if boxes:
        b0 = boxes[0]
        xywh = b0.get('xywh') or [0, 0, 0, 0]
        if len(xywh) == 4:
            x, y, w, h = xywh
            cx, cy = int(x + w // 2), int(y + h // 2)
            logger.info(f"LLM box center: ({cx}, {cy})")
            return cx, cy
    return None


def overlay_click_marker(page, x: int, y: int, radius: int = 20, duration_ms: int = 4000):
    """Draws crosshair + circle at (x,y) in top document for visual feedback."""
    try:
        page.evaluate(
            """
            ([x, y, r, ms]) => {
              let root = document.getElementById('kva-overlay-root');
              if (!root) {
                root = document.createElement('div');
                root.id = 'kva-overlay-root';
                Object.assign(root.style, {
                  position: 'fixed', left: '0', top: '0', width: '100vw', height: '100vh',
                  zIndex: 2147483647, pointerEvents: 'none'
                });
                document.body.appendChild(root);
              }
              const marker = document.createElement('div');
              marker.className = 'kva-click-marker';
              Object.assign(marker.style, {
                position: 'fixed', left: (x - r) + 'px', top: (y - r) + 'px',
                width: (2*r) + 'px', height: (2*r) + 'px', borderRadius: '50%',
                border: '3px solid #ff3030', background: 'rgba(255,48,48,0.2)'
              });

              const hline = document.createElement('div');
              Object.assign(hline.style, {
                position: 'fixed', left: '0', top: y + 'px', width: '100vw', height: '2px',
                background: 'rgba(255,48,48,0.5)'
              });
              const vline = document.createElement('div');
              Object.assign(vline.style, {
                position: 'fixed', top: '0', left: x + 'px', width: '2px', height: '100vh',
                background: 'rgba(255,48,48,0.5)'
              });

              const label = document.createElement('div');
              label.textContent = `(${x}, ${y})`;
              Object.assign(label.style, {
                position: 'fixed', left: (x + r + 8) + 'px', top: (y - r - 8) + 'px',
                color: '#ff3030', fontWeight: '600', fontFamily: 'monospace',
                background: 'rgba(255,255,255,0.7)', padding: '2px 6px', borderRadius: '6px',
                boxShadow: '0 1px 4px rgba(0,0,0,0.2)'
              });

              root.appendChild(hline); root.appendChild(vline);
              root.appendChild(marker); root.appendChild(label);
              setTimeout(() => {
                marker.remove(); hline.remove(); vline.remove(); label.remove();
              }, ms);
            }
            """,
            [x, y, radius, duration_ms],
        )
    except Exception as e:
        logger.debug(f"overlay_click_marker failed: {e}")


def main():
    load_dotenv()

    dmm_email = os.getenv("DMM_EMAIL")
    dmm_password = os.getenv("DMM_PASSWORD")
    if not dmm_email or not dmm_password:
        raise SystemExit("DMM_EMAIL and DMM_PASSWORD must be set in environment")

    screenshots = Path("./screenshots")
    screenshots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        # Launch a large window to see the full canvas area
        browser = pw.chromium.launch(headless=False, args=["--start-maximized", "--window-size=1920,1080"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1.0)
        page = context.new_page()

        # Go to KanColle app page
        page.goto("http://www.dmm.com/netgame/social/-/gadgets/=/app_id=854854", wait_until="load")
        # Refresh once before starting login to ensure layout/canvas are in a stable state
        page.reload(wait_until="load")
        page.evaluate("window.scrollTo(0,0)")
        page.screenshot(path=str(screenshots / f"step_1_loaded_{int(time.time())}.png"))

        # If redirected to login, fill credentials
        # DMM login fields (may change; adjust selectors if needed)
        try:
            # Wait if login form present
            page.wait_for_selector("input[type=email], input[name='login_id']", timeout=5000)
            # Fill email
            email_input = page.query_selector("input[type=email], input[name='login_id']")
            if email_input:
                email_input.fill(dmm_email)

            # Fill password
            pwd_input = page.query_selector("input[type=password], input[name='password']")
            if pwd_input:
                pwd_input.fill(dmm_password)

            # Click login button
            # Try common button texts/selectors
            btn = page.query_selector("button[type=submit], button:has-text('ログイン'), input[type=submit]")
            if btn:
                btn.click()
        except Exception:
            # Maybe already logged in via cookies
            pass

        # Wait for navigation back to app page
        page.wait_for_load_state("load")
        time.sleep(3)
        page.screenshot(path=str(screenshots / f"step_2_post_login_{int(time.time())}.png"))

        # Scroll to reveal GAME START if necessary
        page.mouse.wheel(0, 800)
        time.sleep(1)
        step3_path = screenshots / f"step_3_scrolled_{int(time.time())}.png"
        page.screenshot(path=str(step3_path))

        # Ask LLM for center of GAME START in the screenshot and click it
        try:
            center = detect_game_start_center(step3_path)
            if center:
                cx, cy = center
                logger.info(f"Clicking at LLM-provided coords: ({cx}, {cy})")
                page.mouse.move(cx, cy, steps=12)
                overlay_click_marker(page, cx, cy, radius=22, duration_ms=5000)
                page.screenshot(path=str(screenshots / f"step_4_before_click_{int(time.time())}.png"))
                page.mouse.click(cx, cy)
                page.screenshot(path=str(screenshots / f"step_5_after_click_{int(time.time())}.png"))
                # wait a bit for navigation/loading
                page.wait_for_load_state("load")
                time.sleep(3)
        except Exception as e:
            logger.warning(f"LLM coordinate click skipped: {e}")

        # Try to capture iframe/canvas screenshot
        try:
            page.wait_for_selector("#game_frame", timeout=10000)
            frame = page.frame(name="game_frame")
            if frame:
                frame.wait_for_selector("canvas", timeout=10000)
                canvas = frame.query_selector("canvas")
                if canvas:
                    canvas.screenshot(path=str(screenshots / f"canvas_{int(time.time())}.png"))
        except Exception:
            pass

        # Keep the browser open for inspection and further steps
        logger.info("Keeping browser open. Press Ctrl+C to exit...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()


