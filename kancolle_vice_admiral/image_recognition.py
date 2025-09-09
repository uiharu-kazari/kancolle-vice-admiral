import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from loguru import logger

try:
    import google.generativeai as genai
except Exception:
    genai = None  # Will check at runtime

from .config import config

def find_button_coordinates(screenshot: np.ndarray, template_path: str) -> Optional[Tuple[int, int]]:
    """
    Finds the center coordinates of a button in a screenshot using template matching.

    Args:
        screenshot: The screenshot image as a NumPy array (in BGR format).
        template_path: The path to the template image of the button.

    Returns:
        A tuple (x, y) of the center coordinates of the button, or None if not found.
    """
    try:
        if not Path(template_path).exists():
            logger.error(f"Template image not found at: {template_path}")
            return None

        template = cv2.imread(template_path, cv2.IMREAD_COLOR)
        if template is None:
            logger.error(f"Failed to load template image: {template_path}")
            return None

        # Convert images to grayscale for template matching
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Perform template matching
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # Set a threshold for matching
        threshold = 0.8
        if max_val >= threshold:
            logger.info(f"Button found with confidence: {max_val:.2f}")
            template_height, template_width = template_gray.shape
            top_left = max_loc
            center_x = top_left[0] + template_width // 2
            center_y = top_left[1] + template_height // 2
            return (center_x, center_y)
        else:
            logger.warning(f"Button not found. Maximum confidence: {max_val:.2f} (Threshold: {threshold})")
            return None

    except Exception as e:
        logger.error(f"An error occurred during image recognition: {e}")
        return None


# -----------------------------
# Gemini-based detection module
# -----------------------------

class Box(Tuple[int, int, int, int]):
    pass


def _encode_image_to_png_bytes(image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Failed to encode image to PNG bytes")
    return buf.tobytes()


def _ensure_image(image: Union[np.ndarray, bytes, str]) -> np.ndarray:
    if isinstance(image, np.ndarray):
        return image
    if isinstance(image, (bytes, bytearray)):
        arr = np.frombuffer(image, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image bytes")
        return img
    if isinstance(image, str):
        img = cv2.imread(image, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not read image from path: {image}")
        return img
    raise TypeError("Unsupported image type")


def _configure_gemini_if_needed() -> None:
    if genai is None:
        raise RuntimeError("google-generativeai is not installed. Please install it.")
    api_key = config.ai.api_key
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured.")
    genai.configure(api_key=api_key)


def detect_targets_with_gemini(
    image: Union[np.ndarray, bytes, str],
    hints: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, Union[str, float, int, List[int]]]]]:
    """
    Run Gemini Vision to detect targets and return a structured dict:
    {
      "boxes": [{"label": str, "xywh": [x,y,w,h], "score": float}],
      "centers": [{"label": str, "cx": int, "cy": int, "score": float}],
      "polygons": [{"label": str, "points": [[x,y],...], "score": float}]
    }
    """
    _configure_gemini_if_needed()

    img = _ensure_image(image)
    h, w = img.shape[:2]
    png_bytes = _encode_image_to_png_bytes(img)

    model_name = config.ai.model
    try:
        model = genai.GenerativeModel(model_name)
    except Exception:
        # Fallback to a broadly available model name
        model = genai.GenerativeModel("gemini-1.5-flash")

    hints = hints or []
    labels_text = ", ".join(hints) if hints else "targets of interest such as 'GAME START'"

    system_prompt = (
        "You are an image analyzer. Return only JSON. "
        "Detect UI targets in the provided image. Prefer labels from the hints if present. "
        "All coordinates must be integer pixel values relative to this image (width={} height={})."
    ).format(w, h)

    schema = {
        "type": "object",
        "properties": {
            "boxes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "xywh": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 4,
                            "maxItems": 4,
                        },
                        "score": {"type": "number"},
                    },
                    "required": ["label", "xywh"],
                },
            },
            "centers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "cx": {"type": "integer"},
                        "cy": {"type": "integer"},
                        "score": {"type": "number"},
                    },
                    "required": ["label", "cx", "cy"],
                },
            },
            "polygons": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "points": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                        },
                        "score": {"type": "number"},
                    },
                    "required": ["label", "points"],
                },
            },
        },
        "required": ["boxes", "centers", "polygons"],
    }

    prompt = (
        f"Detect and localize: {labels_text}. "
        f"Return JSON with arrays: boxes (xywh), centers (cx,cy), polygons. "
        f"Use integer pixel coords relative to the provided image size (w={w}, h={h}). "
        f"If unsure, omit the item rather than hallucinating."
    )

    try:
        response = model.generate_content(
            [
                {"mime_type": "text/plain", "text": system_prompt},
                {"mime_type": "image/png", "data": png_bytes},
                {"mime_type": "text/plain", "text": prompt},
            ],
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
        json_text = response.text or "{}"
        data = json.loads(json_text)
        # Normalize presence
        data.setdefault("boxes", [])
        data.setdefault("centers", [])
        data.setdefault("polygons", [])
        return data
    except Exception as e:
        logger.error(f"Gemini detection failed: {e}")
        return {"boxes": [], "centers": [], "polygons": []}


def find_label_center(
    detection: Dict[str, List[Dict[str, Union[str, int, float, List[int]]]]],
    label_aliases: List[str],
) -> Optional[Tuple[int, int]]:
    labels_norm = [s.lower() for s in label_aliases]

    # Prefer explicit centers
    for c in detection.get("centers", []):
        lbl = str(c.get("label", "")).lower()
        if lbl in labels_norm:
            try:
                return int(c.get("cx")), int(c.get("cy"))
            except Exception:
                continue

    # Fallback to boxes' centers
    for b in detection.get("boxes", []):
        lbl = str(b.get("label", "")).lower()
        if lbl in labels_norm:
            try:
                x, y, w, h = b.get("xywh", [0, 0, 0, 0])
                return int(x + w // 2), int(y + h // 2)
            except Exception:
                continue
    return None


def find_button_coordinates_via_gemini(
    screenshot: Union[np.ndarray, bytes, str],
    hints: Optional[List[str]] = None,
) -> Optional[Tuple[int, int]]:
    """Find a target center using Gemini detection with label hints.

    Example hints for game start: ["game start", "start", "play", "login"]
    """
    hints = hints or ["game start", "start", "play", "login"]
    detection = detect_targets_with_gemini(screenshot, hints=hints)
    center = find_label_center(detection, hints)
    if center:
        logger.info(f"Gemini detected center at: {center}")
    else:
        logger.warning("Gemini could not find a center for provided hints")
    return center
