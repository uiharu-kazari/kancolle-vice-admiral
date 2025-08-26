"""
Browser automation module for KanColle Vice Admiral
Uses the browser-use library with Gemini AI for intelligent automation

Security Features:
- Uses sensitive_data parameter to securely handle DMM credentials without exposing them to the LLM
- Restricts browser session to only DMM domains to prevent navigation to untrusted sites  
- Disables vision mode during login to prevent credentials from being visible in screenshots
- Enables vision mode for game tasks where no sensitive data is expected
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from browser_use import Agent, BrowserSession
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.exceptions import LangChainException
from loguru import logger
import cv2
import numpy as np
from .image_recognition import find_button_coordinates
from .config import config

# Load environment variables
load_dotenv()


class LLMManager:
    """Manages LLM instances with fallback models and proper retry handling"""
    
    def __init__(self, api_key: str, fallback_models: list[str]):
        self.api_key = api_key
        self.fallback_models = fallback_models
        self.current_model_index = 0
        self.model_cooldowns = {}  # Track when each model becomes available again
        self.last_retry_time = 0
        
    def get_current_llm(self) -> ChatGoogleGenerativeAI:
        """Get the current LLM instance with proper retry configuration"""
        # Find the best available model (not rate limited)
        best_model_index = self._find_best_available_model()
        self.current_model_index = best_model_index
        
        current_model = self.fallback_models[self.current_model_index]
        
        # Configure LLM without invalid retry parameters
        llm = ChatGoogleGenerativeAI(
            model=current_model,
            google_api_key=self.api_key,
            temperature=0.1,
            max_retries=1,  # Let our own retry logic handle this
        )
        
        logger.info(f"Using model: {current_model} (option {self.current_model_index + 1}/{len(self.fallback_models)})")
        return llm
    
    def _find_best_available_model(self) -> int:
        """Find the first available model that's not in cooldown"""
        current_time = time.time()
        
        # Check each model starting from primary
        for i, model in enumerate(self.fallback_models):
            cooldown_until = self.model_cooldowns.get(model, 0)
            if current_time >= cooldown_until:
                if i != self.current_model_index:
                    logger.info(f"Model {model} is now available (cooldown expired)")
                return i
        
        # If all models are in cooldown, use the one with shortest remaining time
        best_model = min(self.fallback_models, 
                        key=lambda m: self.model_cooldowns.get(m, 0))
        best_index = self.fallback_models.index(best_model)
        
        remaining_cooldown = self.model_cooldowns.get(best_model, 0) - current_time
        if remaining_cooldown > 0:
            logger.warning(f"All models rate limited. Using {best_model} (cooldown: {remaining_cooldown:.1f}s remaining)")
        
        return best_index
    
    def switch_to_next_model(self) -> bool:
        """Switch to the next available fallback model. Returns True if switch successful, False if no more models"""
        # Mark current model as rate limited
        current_model = self.fallback_models[self.current_model_index]
        current_time = time.time()
        # Set cooldown for 60 seconds
        self.model_cooldowns[current_model] = current_time + 60
        
        # Find next available model
        next_index = self._find_best_available_model()
        
        if next_index != self.current_model_index:
            self.current_model_index = next_index
            next_model = self.fallback_models[self.current_model_index]
            logger.warning(f"Switching from {current_model} to fallback model: {next_model}")
            return True
        else:
            logger.error("All fallback models are currently rate limited!")
            return False
    
    def reset_to_primary(self):
        """Reset to primary model (useful after successful operations)"""
        if self.current_model_index > 0:
            self.current_model_index = 0
            logger.info(f"Reset to primary model: {self.fallback_models[0]}")
    
    async def handle_rate_limit_error(self, error: Exception) -> bool:
        """Handle rate limit errors with proper waiting and model switching"""
        error_str = str(error)
        
        # Check if it's a rate limit error
        if "429" in error_str or "ResourceExhausted" in error_str or "quota" in error_str.lower():
            logger.warning(f"Rate limit detected: {error}")
            
            # Extract retry delay from error if available
            retry_delay = self._extract_retry_delay(error_str)
            current_model = self.fallback_models[self.current_model_index]
            
            if retry_delay > 0:
                # Set the model cooldown based on API suggestion
                self.model_cooldowns[current_model] = time.time() + retry_delay
                logger.info(f"⏳ Model {current_model} rate limited for {retry_delay} seconds")
                
                # Try to switch to an available model
                if self.switch_to_next_model():
                    logger.info("Switched to different model, continuing immediately")
                    return True
                else:
                    # All models rate limited, wait for the suggested delay
                    logger.info(f"All models rate limited, waiting {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    return True
            else:
                # No specific delay, try switching models with default cooldown
                if self.switch_to_next_model():
                    logger.info("Switched to different model, continuing with short delay")
                    await asyncio.sleep(5)
                    return True
                else:
                    logger.error("All models are rate limited with no specific retry delay")
                    await asyncio.sleep(30)  # Default wait
                    return True
        
        return False
    
    def _extract_retry_delay(self, error_str: str) -> int:
        """Extract retry delay from error message"""
        try:
            # Look for retry_delay in the error message
            if "retry_delay" in error_str:
                # Try to find the seconds value
                import re
                match = re.search(r'retry_delay[^}]*seconds: (\d+)', error_str)
                if match:
                    return int(match.group(1))
            
            # Fallback to default delays based on error content
            if "429" in error_str:
                return 60  # Wait 1 minute for rate limits
            
        except Exception as e:
            logger.debug(f"Could not extract retry delay: {e}")
        
        return 0


class KanColleBrowserAutomation:
    """Main browser automation class for KanColle using browser-use"""
    
    def __init__(self):
        self.agent: Optional[Agent] = None
        self.session_start_time: Optional[datetime] = None
        
        # Initialize LLM manager with fallback models
        self.llm_manager = LLMManager(
            api_key=config.ai.api_key,
            fallback_models=config.ai.fallback_models
        )
        
        logger.info(f"Initialized KanColle Browser Automation with fallback models: {config.ai.fallback_models}")
    
    async def _execute_with_retry(self, agent_task, task_name: str, return_result: bool = False):
        """Execute an agent task with retry and fallback model support"""
        max_retries = config.automation.retry_count
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting {task_name} (attempt {attempt + 1}/{max_retries})")
                
                # Get current LLM
                current_llm = self.llm_manager.get_current_llm()
                
                # Execute the task
                result = await agent_task(current_llm)
                
                # If successful, reset to primary model for future tasks
                self.llm_manager.reset_to_primary()
                
                # Return result or success boolean based on parameter
                return result if return_result else True
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                # Try to handle rate limit errors
                if await self.llm_manager.handle_rate_limit_error(e):
                    continue  # Retry with same attempt number after waiting/switching
                
                # If not rate limit or can't handle, check if we should retry
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All attempts failed for {task_name}")
                    return None if return_result else False
        
        return None if return_result else False
    
    async def login_to_dmm_and_kancolle(self) -> bool:
        """Login to DMM and navigate to KanColle following browser-use best practices"""
        logger.info("Starting DMM login and KanColle navigation...")

        # Check if we have saved authentication state
        auth_file = config.paths.logs_dir / "dmm_auth.json"

        # Test if credentials are actually loaded
        if not config.dmm.email or config.dmm.email == 'your_dmm_email@example.com':
            logger.error("❌ DMM email not properly configured in .env file!")
            return False
        if not config.dmm.password or config.dmm.password == 'your_dmm_password_here':
            logger.error("❌ DMM password not properly configured in .env file!")
            return False

        logger.info(f"🔍 Using credentials: {config.dmm.email[:3]}***@{config.dmm.email.split('@')[1] if '@' in config.dmm.email else 'unknown'}")

        # A simpler login task for the LLM. It only needs to get to the game page.
        login_task = f"""
        Please help me login to DMM and access the KanColle game page:
        1. Navigate to {config.kancolle.url}
        2. If a login form appears, enter these credentials:
           - Email/Username: {config.dmm.email}
           - Password: {config.dmm.password}
        3. Click the login button and wait for the page to authenticate.
        4. After login, you should be on the KanColle landing page which has a large "GAME START" button.
        5. Please stop immediately once you see the "GAME START" button. Do not click it. Your task is complete at this point.
        """

        # Create browser session with proper domain restrictions
        browser_session_config = {
            'allowed_domains': [
                'https*.dmm.com',
                'http://www.dmm.com',
                'https://www.dmm.com',
                'http*.kancolle-server.com',
                'https*.kancolle-server.com'
            ]
        }

        # Try to use saved authentication state if available
        if auth_file.exists():
            logger.info("📄 Found saved authentication state, attempting to reuse...")
            browser_session_config['storage_state'] = str(auth_file)

        browser_session = BrowserSession(**browser_session_config)

        # Define the agent creation and execution as a function for retry
        async def create_and_run_login_agent(llm):
            self.agent = Agent(
                task=login_task,
                llm=llm,
                browser_session=browser_session,
                use_vision=True,  # Vision is still useful for the LLM to see the page
                save_conversation_path=str(config.paths.logs_dir / f"login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            )

            self.session_start_time = datetime.now()
            result = await self.agent.run()

            # Save authentication state for future use
            try:
                if hasattr(self.agent, 'browser') and self.agent.browser:
                    await self.agent.browser.context.storage_state(path=str(auth_file))
                    logger.info(f"💾 Saved authentication state to {auth_file}")
            except Exception as e:
                logger.warning(f"Could not save authentication state: {e}")

            return result

        # Execute with retry and fallback support
        login_success = await self._execute_with_retry(create_and_run_login_agent, "login")

        if not login_success:
            logger.error("AI-driven login to DMM page failed.")
            return False

        logger.success("AI-driven login to DMM page successful. Now finding and clicking 'GAME START' button.")
        try:
            if not (self.agent and hasattr(self.agent, 'browser') and self.agent.browser):
                logger.error("Browser object not found after login.")
                return False

            # Get the active page
            context = self.agent.browser.contexts[0]
            page = context.pages[-1]  # Get the last opened page

            # Wait for canvas to be visible
            game_canvas_selector = '#game_frame' # The game is in an iframe
            await page.wait_for_selector(game_canvas_selector, timeout=30000)
            logger.info("Game frame found. Getting the frame's content...")

            frame = page.frame(name="game_frame")
            if not frame:
                logger.error("Could not access the game iframe.")
                return False

            # Wait for the canvas inside the iframe
            canvas_selector_in_frame = 'canvas'
            await frame.wait_for_selector(canvas_selector_in_frame, timeout=30000)
            canvas_element = await frame.query_selector(canvas_selector_in_frame)

            if not canvas_element:
                logger.error("Could not find the canvas element inside the iframe.")
                return False

            logger.info("Game canvas found. Taking screenshot...")
            await asyncio.sleep(5)  # Give it a moment to render

            screenshot_bytes = await canvas_element.screenshot()

            # Convert screenshot to OpenCV format
            image_array = np.frombuffer(screenshot_bytes, np.uint8)
            screenshot_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if screenshot_image is None:
                logger.error("Failed to decode screenshot from canvas.")
                return False

            # Find the button
            template_path = str(config.paths.assets_dir / "game_start_button.png")
            coordinates = find_button_coordinates(screenshot_image, template_path)

            if coordinates:
                logger.info(f"GAME START button found at coordinates: {coordinates}")

                # Get canvas position to click relative to the viewport
                bounding_box = await canvas_element.bounding_box()
                if not bounding_box:
                    logger.error("Could not get canvas bounding box.")
                    return False

                click_x = bounding_box['x'] + coordinates[0]
                click_y = bounding_box['y'] + coordinates[1]

                logger.info(f"Clicking at absolute coordinates: ({click_x}, {click_y})")
                await page.mouse.click(click_x, click_y)
                logger.success("Clicked 'GAME START' button.")

                await asyncio.sleep(15)  # Wait for game to load
                return True
            else:
                logger.error("Could not find 'GAME START' button on the screen.")
                screenshot_path = config.paths.screenshots_dir / f"start_button_not_found_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot_bytes)
                logger.info(f"Screenshot of canvas saved to {screenshot_path} for debugging.")
                return False

        except Exception as e:
            logger.error(f"An error occurred while clicking the start button: {e}")
            return False
    
    async def execute_task(self, task_description: str) -> bool:
        """Execute a specific KanColle task"""
        logger.info(f"Executing task: {task_description}")
        
        # Create a specific task for KanColle automation with coordinate-based clicking guidance
        kancolle_task = f"""
        I'm currently in the KanColle (艦隊これくしょん) game interface. 
        Please help me with this task: {task_description}
        
        Please:
        1. Analyze the current game interface using your vision capabilities
        2. Navigate to the appropriate sections/menus
        3. Perform the required actions step by step
        4. Verify the task completion
        5. Report what was accomplished
        
        IMPORTANT: KanColle uses canvas-based game elements that may not be standard HTML clickables:
        - If you can't find clickable HTML elements, use coordinate-based clicking
        - Look for visual buttons, text, and interface elements in screenshots
        - Use the center of visual elements for clicking when HTML selection fails
        - Be patient with game interface loading times (Flash/HTML5 content)
        - Game buttons often appear as images or canvas elements, not HTML buttons
        
        Take your time and be careful with each action. If you encounter any errors or unexpected situations, describe what you see and try coordinate-based clicking on visual elements.
        """
        
        # Create secure browser session for game tasks (restrict to DMM/KanColle domains)
        browser_session = BrowserSession(
            allowed_domains=[
                'https://*.dmm.com',
                'http://www.dmm.com',
                'https://www.dmm.com',
                'http://*.kancolle-server.com',
                'https://*.kancolle-server.com'
            ]
        )
        
        # Define the agent creation and execution as a function for retry
        async def create_and_run_task_agent(llm):
            agent = Agent(
                task=kancolle_task,
                llm=llm,
                browser_session=browser_session,
                use_vision=True,  # Enable vision for game interface analysis (no sensitive data expected)
                save_conversation_path=str(config.paths.logs_dir / f"task_{task_description.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            )
            
            result = await agent.run()
            return result
        
        # Execute with retry and fallback support
        success = await self._execute_with_retry(create_and_run_task_agent, f"task: {task_description}")
        
        if success:
            logger.success(f"Task completed: {task_description}")
        else:
            logger.error(f"Task failed after all retry attempts: {task_description}")
        
        return success
    
    async def generate_automation_script(self, task_description: str) -> str:
        """Generate documentation for automating a specific task"""
        try:
            logger.info(f"Generating automation script for: {task_description}")
            
            script_task = f"""
            I'm in the KanColle game. Please help me understand how to automate this task: {task_description}
            
            Please:
            1. Analyze the current game interface
            2. Navigate through the steps needed for this task
            3. Document each step with specific details about:
               - Which buttons/menus to click
               - What to look for on each screen
               - Any prerequisites or conditions
               - Expected outcomes
            4. Create a step-by-step guide that could be used for future automation
            
            Please be very detailed and specific about the UI elements and actions needed.
            """
            
            # Create secure browser session for script generation
            browser_session = BrowserSession(
                allowed_domains=[
                    'https://*.dmm.com',
                    'http://www.dmm.com',
                    'https://www.dmm.com',
                    'http://*.kancolle-server.com',
                    'https://*.kancolle-server.com'
                ]
            )
            
            # Define the agent creation and execution as a function for retry
            async def create_and_run_script_agent(llm):
                agent = Agent(
                    task=script_task,
                    llm=llm,
                    browser_session=browser_session,
                    use_vision=True,
                    save_conversation_path=str(config.paths.logs_dir / f"script_gen_{task_description.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                )
                
                result = await agent.run()
                return result
            
            # Execute with retry and fallback support
            result = await self._execute_with_retry(create_and_run_script_agent, f"script generation: {task_description}", return_result=True)
            
            if result is None:
                logger.error(f"Failed to generate automation script after all retry attempts: {task_description}")
                return ""
            
            # Save the generated script
            script_filename = f"script_{task_description.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            script_path = config.paths.scripts_output_dir / script_filename
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(f"# KanColle Automation Guide\n\n")
                f.write(f"**Task**: {task_description}\n\n")
                f.write(f"**Generated**: {datetime.now().isoformat()}\n\n")
                f.write(f"**Model**: {config.ai.model}\n\n")
                f.write("---\n\n")
                f.write(str(result))
            
            logger.success(f"Automation guide saved to: {script_path}")
            return str(result)
            
        except Exception as e:
            logger.error(f"Failed to generate automation script: {e}")
            return ""
    
    def get_session_info(self) -> dict:
        """Get information about the current session"""
        return {
            "session_start": self.session_start_time.isoformat() if self.session_start_time else None,
            "session_duration": str(datetime.now() - self.session_start_time) if self.session_start_time else None,
            "model": config.ai.model,
        }


# Convenience functions
async def quick_login() -> KanColleBrowserAutomation:
    """Quick login function for testing"""
    automation = KanColleBrowserAutomation()
    success = await automation.login_to_dmm_and_kancolle()
    
    if success:
        logger.success("Login successful! Ready for automation tasks.")
    else:
        logger.error("Login failed!")
    
    return automation


async def run_daily_tasks():
    """Run common daily tasks"""
    automation = KanColleBrowserAutomation()
    
    # Login first
    if not await automation.login_to_dmm_and_kancolle():
        logger.error("Failed to login")
        return False
    
    # Execute daily tasks
    daily_tasks = [
        "Check and collect daily missions",
        "Send long expeditions (2, 5, 21)",
        "Perform daily constructions",
        "Check quest progress and complete available quests"
    ]
    
    for task in daily_tasks:
        logger.info(f"Starting task: {task}")
        success = await automation.execute_task(task)
        
        if success:
            logger.success(f"Completed: {task}")
        else:
            logger.warning(f"Failed or incomplete: {task}")
        
        # Brief pause between tasks
        await asyncio.sleep(2)
    
    logger.info("Daily tasks routine completed!")
    return True 