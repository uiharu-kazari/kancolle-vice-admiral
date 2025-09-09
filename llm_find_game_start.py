import argparse
import glob
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from google import genai
from google.genai import types


def find_latest_step3(screenshots_dir: Path) -> Path | None:
    candidates = sorted(
        screenshots_dir.glob("step_3_scrolled_*.png"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return candidates[0] if candidates else None


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Send step_3 image to LLM for GAME START coordinates")
    parser.add_argument("image", nargs="?", help="Path to step_3 scrolled image (png)")
    args = parser.parse_args()

    screenshots_dir = Path("./screenshots")
    img_path: Path | None
    if args.image:
        img_path = Path(args.image)
    else:
        img_path = find_latest_step3(screenshots_dir)

    if not img_path or not img_path.exists():
        raise SystemExit("step_3 image not found. Pass a path or run the demo first.")

    logger.info(f"Using image: {img_path}")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY or GOOGLE_API_KEY must be set")

    client = genai.Client(api_key=api_key)

    # Build structured JSON response schema
    response_schema = {
        'type': 'OBJECT',
        'properties': {
            'boxes': {
                'type': 'ARRAY',
                'items': {
                    'type': 'OBJECT',
                    'properties': {
                        'label': {'type': 'STRING'},
                        'xywh': {
                            'type': 'ARRAY',
                            'items': {'type': 'INTEGER'},
                        },
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

    # Prepare image part using python-genai SDK
    # Read image as bytes and create an image part
    with open(img_path, 'rb') as f:
        image_bytes = f.read()

    image_part = types.Part.from_bytes(data=image_bytes, mime_type='image/png')

    resp = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image_part, "Return JSON with 'boxes' and 'centers' for the GAME START button only. Label it 'game start'."],
        config=types.GenerateContentConfig(
            response_mime_type='application/json',
            response_json_schema=response_schema,
        ),
    )

    text = resp.text or '{}'
    try:
        data = json.loads(text)
    except Exception:
        data = {'raw': text}

    print(json.dumps(data, ensure_ascii=False, indent=2))

    # Derive center if not directly provided
    center = None
    centers = data.get('centers') or []
    if centers:
        c0 = centers[0]
        center = (c0.get('cx'), c0.get('cy'))
    else:
        boxes = data.get('boxes') or []
        if boxes:
            b0 = boxes[0]
            xywh = b0.get('xywh') or [0, 0, 0, 0]
            if len(xywh) == 4:
                x, y, w, h = xywh
                center = (int(x + w // 2), int(y + h // 2))
    print('CENTER:', center)


if __name__ == "__main__":
    main()


