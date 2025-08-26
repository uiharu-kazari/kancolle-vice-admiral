import cv2
import numpy as np
from typing import Optional, Tuple
from pathlib import Path
from loguru import logger

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
