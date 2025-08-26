import cv2
import numpy as np
import requests
import pytest
from pathlib import Path
from kancolle_vice_admiral.image_recognition import find_button_coordinates

# URL of the full screenshot image for testing
SCREENSHOT_URL = "https://i.ibb.co/wFzjW5ZF/Screenshot-2025-08-25-at-22-18-45.png"
TEMPLATE_PATH = Path(__file__).parent.parent / "kancolle_vice_admiral/assets/game_start_button.png"

@pytest.fixture(scope="module")
def screenshot_image():
    """Downloads the screenshot image for testing."""
    try:
        response = requests.get(SCREENSHOT_URL, timeout=10)
        response.raise_for_status()
        image_array = np.frombuffer(response.content, np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return image
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to download screenshot for testing: {e}")
    except Exception as e:
        pytest.fail(f"Failed to process screenshot for testing: {e}")


def test_find_button_coordinates_success(screenshot_image):
    """
    Tests that find_button_coordinates successfully finds the button
    in the screenshot and returns the correct coordinates.
    """
    assert TEMPLATE_PATH.exists(), f"Template image not found at {TEMPLATE_PATH}"
    assert screenshot_image is not None, "Screenshot image could not be loaded."

    coordinates = find_button_coordinates(screenshot_image, str(TEMPLATE_PATH))

    assert coordinates is not None, "The 'GAME START' button was not found in the screenshot."

    # The expected center coordinates are based on the 640x324 image dimensions
    # and the new crop coordinates y=170:185, x=275:365
    # Center of crop is roughly x=320, y=178
    expected_x, expected_y = 320, 178
    tolerance = 10  # Allow for a small tolerance in detection

    assert abs(coordinates[0] - expected_x) <= tolerance, f"X coordinate {coordinates[0]} is out of tolerance from {expected_x}"
    assert abs(coordinates[1] - expected_y) <= tolerance, f"Y coordinate {coordinates[1]} is out of tolerance from {expected_y}"


def test_find_button_coordinates_not_found():
    """
    Tests that find_button_coordinates returns None when the button
    is not present in the image.
    """
    # Create a blank black image that does not contain the button
    blank_image = np.zeros((480, 640, 3), dtype=np.uint8)

    assert TEMPLATE_PATH.exists(), f"Template image not found at {TEMPLATE_PATH}"

    coordinates = find_button_coordinates(blank_image, str(TEMPLATE_PATH))

    assert coordinates is None, "The function found a button in a blank image, which should not happen."
