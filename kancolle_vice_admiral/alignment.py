"""
Alignment & calibration utilities for mapping image/canvas pixels to CSS (viewport) pixels.

All click actions in Playwright expect CSS (device-independent) pixels relative to the viewport.
Screenshots are typically in device pixels (scaled by devicePixelRatio).

This module provides helpers to convert coordinates accordingly.
"""

from typing import Tuple


def device_pixels_to_css_pixels(x_px: float, y_px: float, device_pixel_ratio: float) -> Tuple[float, float]:
    """Convert device-pixel coordinates (e.g., from screenshots) to CSS pixels using DPR.

    Args:
        x_px: X coordinate in device pixels
        y_px: Y coordinate in device pixels
        device_pixel_ratio: window.devicePixelRatio

    Returns:
        (x_css, y_css) in CSS pixels
    """
    if device_pixel_ratio <= 0:
        device_pixel_ratio = 1.0
    return x_px / device_pixel_ratio, y_px / device_pixel_ratio


def canvas_point_to_viewport(
    canvas_point_x: float,
    canvas_point_y: float,
    canvas_image_width_px: float,
    canvas_image_height_px: float,
    element_bbox_x_css: float,
    element_bbox_y_css: float,
    element_bbox_width_css: float,
    element_bbox_height_css: float,
    device_pixel_ratio: float,
) -> Tuple[float, float]:
    """Map a point in a canvas screenshot (device pixels) to viewport CSS pixels.

    The canvas screenshot dimensions (canvas_image_width_px/height) are device-pixel sized.
    The element bounding box is in CSS pixels.

    We first convert screenshot-space (device px) to element-relative CSS by scaling by DPR and
    the ratio of element bbox to screenshot in CSS units.
    """
    if device_pixel_ratio <= 0:
        device_pixel_ratio = 1.0

    # Convert device px -> CSS px within the element coordinate system
    canvas_x_css = canvas_point_x / device_pixel_ratio
    canvas_y_css = canvas_point_y / device_pixel_ratio

    # Some environments may capture screenshots at DPR-scaled size that already matches the element size * DPR.
    # We assume 1:1 mapping after DPR normalization, so we just offset by the element's top-left.
    # If further scaling were applied (e.g., CSS transforms), that should be accounted for before calling this.
    viewport_x_css = element_bbox_x_css + min(max(canvas_x_css, 0.0), element_bbox_width_css)
    viewport_y_css = element_bbox_y_css + min(max(canvas_y_css, 0.0), element_bbox_height_css)

    return viewport_x_css, viewport_y_css


