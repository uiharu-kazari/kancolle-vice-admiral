# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KanColle Vice Admiral is an AI-powered browser automation system for 艦隊これくしょん (Kantai Collection). It leverages the `browser-use` library with Google Gemini AI to generate and execute browser automation scripts for daily, weekly, and seasonal tasks in the game.

**Current Status**: Early development - core features are still being implemented.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync
uv run playwright install chromium

# Environment configuration
cp .env.example .env
# Edit .env with your credentials
```

### Running the Application

```bash
# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Validate environment setup
uv run python main.py validate

# Login to DMM and KanColle
uv run python main.py login

# Generate automation scripts
uv run python main.py generate "daily expeditions"

# Execute specific tasks
uv run python main.py execute "collect daily missions"

# Run daily automation tasks
uv run python main.py daily

# Playwright demo (no LLM control, with LLM vision assist)
uv run python playwright_demo.py
```

### Testing & Code Quality
```bash
# Run tests (dev dependencies)
pytest

# Code formatting
black .

# Linting
flake8

# Type checking
mypy
```

## Architecture

### Core Components

1. **KanColleBrowserAutomation** (`kancolle_vice_admiral/browser_automation.py`)
   - Main automation class using browser-use library with Gemini AI
   - Handles DMM login and game navigation
   - Executes automation tasks with AI intervention
   - Implements LLM fallback strategy with rate limit handling via LLMManager

2. **LLMManager** (`kancolle_vice_admiral/browser_automation.py`)
   - Manages multiple Gemini models with automatic fallback (2.5-flash → 1.5-flash → 2.0-flash)
   - Handles rate limiting with cooldown tracking
   - Extracts retry delays from API errors and switches models when rate limited
   - Implements exponential backoff with configurable retry logic

3. **Image Recognition** (`kancolle_vice_admiral/image_recognition.py`)
   - Template matching using OpenCV (`find_button_coordinates`)
   - Gemini Vision-based detection (`find_button_coordinates_via_gemini`, `detect_targets_with_gemini`)
   - Returns button coordinates for automated clicking

4. **Custom Tools** (`kancolle_vice_admiral/tools.py`)
   - Browser-use tools for deterministic canvas/iframe screenshot capture
   - `capture_canvas_frame`: Screenshot using Playwright element.screenshot()
   - `capture_canvas_js`: Screenshot using JS canvas.toDataURL()

5. **Configuration** (`kancolle_vice_admiral/config.py`)
   - Pydantic-based configuration management
   - Loads from environment variables (.env file)
   - Validates API keys and credentials
   - Auto-creates required directories

6. **State Store** (`kancolle_vice_admiral/state_store.py`)
   - Persistence for automation state

7. **Alignment** (`kancolle_vice_admiral/alignment.py`)
   - Device pixel to CSS pixel conversion utilities

### Security Features

The browser automation implements several security measures:
- Uses `sensitive_data` parameter to securely handle DMM credentials without exposing them to the LLM
- Restricts browser session to only DMM and KanColle domains via `allowed_domains`
- Disables vision mode during login to prevent credentials from being visible in screenshots
- Enables vision mode only for game tasks where no sensitive data is expected
- Saves authentication state to `logs/dmm_auth.json` for session reuse

### Key Workflows

**Login Flow**:
1. Browser session created with domain restrictions
2. Agent navigates to KanColle URL
3. If login form present, fills credentials (securely via sensitive_data)
4. Waits for "GAME START" button to appear
5. Optionally clicks GAME START and captures canvas screenshot
6. Saves authentication state for future reuse

**Task Execution Flow**:
1. Creates Agent with task description
2. Agent uses vision to analyze game interface
3. Navigates menus and performs actions
4. Handles canvas-based game elements with coordinate-based clicking
5. Implements retry logic with LLM fallback on failures

**Script Generation Flow**:
1. Agent explores game interface for specified task
2. Documents each step with UI element details
3. Saves automation guide to `generated_scripts/`

## Environment Variables

Required:
- `GEMINI_API_KEY`: Google Gemini API key (get from https://aistudio.google.com/)
- `DMM_EMAIL`: DMM account email
- `DMM_PASSWORD`: DMM account password

Optional (with defaults):
- `GEMINI_MODEL`: Primary AI model (default: gemini-2.5-flash-preview-05-20)
- `AUTO_RETRY_COUNT`: Retry attempts (default: 3)
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENABLE_AI_INTERVENTION`: Enable AI error recovery (default: true)
- `MAX_AUTOMATION_TIME_MINUTES`: Max automation duration (default: 60)
- `PAUSE_BETWEEN_ACTIONS_MS`: Delay between actions (default: 1000)

## File Structure

```
kancolle_vice_admiral/
├── __init__.py
├── config.py              # Configuration management
├── browser_automation.py  # Main automation logic
├── image_recognition.py   # OpenCV & Gemini vision detection
├── tools.py              # Custom browser-use tools
├── alignment.py          # Coordinate conversion utilities
└── state_store.py        # State persistence

main.py                   # CLI entry point
playwright_demo.py        # Playwright demo with LLM vision assist
llm_find_game_start.py   # Standalone Gemini detection utility

generated_scripts/        # Generated automation guides
logs/                     # Log files and saved auth state
screenshots/              # Screenshot artifacts
```

## Important Implementation Details

### KanColle Canvas Handling
- KanColle uses canvas-based rendering (Flash/HTML5)
- Many game elements are not standard HTML clickables
- Use coordinate-based clicking when HTML selectors fail
- The game runs inside `#game_frame` iframe
- Custom tools provide deterministic screenshot capture of canvas

### Rate Limiting Strategy
- LLMManager maintains a list of fallback models
- On 429 errors, automatically switches to next available model
- Tracks cooldown periods per model
- Extracts retry delays from API error messages
- Implements exponential backoff for non-rate-limit errors

### Playwright Demo Script
- `playwright_demo.py` provides a working reference implementation
- Logs in to DMM, navigates to KanColle app page
- Uses Gemini to detect "GAME START" button coordinates
- Overlays visual markers for click positions
- Captures step-by-step screenshots to `screenshots/`
- Keeps browser open for inspection (Ctrl+C to exit)

## Common Patterns

### Creating New Automation Tasks
1. Add task description to CLI parser in `main.py`
2. Implement task logic in `KanColleBrowserAutomation.execute_task()`
3. Use vision mode for game interface analysis
4. Handle canvas elements with coordinate-based clicking
5. Implement retry logic for reliability

### Adding New Image Recognition Templates
1. Place template images in `kancolle_vice_admiral/assets/`
2. Use `find_button_coordinates()` for OpenCV template matching
3. Use `find_button_coordinates_via_gemini()` for AI-based detection
4. Consider using `device_pixels_to_css_pixels()` for coordinate alignment

### Extending Browser-Use Tools
1. Add new tool functions in `kancolle_vice_admiral/tools.py`
2. Decorate with `@tools.action(description="...")`
3. Accept `browser` parameter for Playwright context access
4. Return `ActionResult` with success status and attachments

## Dependencies

- **Python 3.12+** (required)
- **UV package manager** for dependency management
- **browser-use**: AI-powered browser automation
- **playwright**: Browser automation library
- **langchain-google-genai**: Gemini AI integration
- **opencv-python-headless**: Image recognition
- **google-generativeai**: Gemini Vision API
- **loguru**: Logging
- **pydantic**: Configuration validation
- **python-dotenv**: Environment variable management

## Notes

- Project uses MIT License
- Not affiliated with DMM or official KanColle development team
- Use responsibly and comply with KanColle Terms of Service
- The automation respects rate limiting and includes error recovery
- Logs are rotated daily with 30-day retention (compressed)
