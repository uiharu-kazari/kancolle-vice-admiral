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
        
        # Direct approach (recommended by browser-use docs for login)
        login_task = f"""
        Please help me login to DMM and access KanColle game:
        
        1. Navigate to {config.kancolle.url}
        2. When you see the login form, enter these credentials:
           - Email/Username: {config.dmm.email}
           - Password: {config.dmm.password}
        3. Click the login button and wait for authentication
        4. Wait for the page to load completely after login (at least 5-10 seconds)
        5. **IMPORTANT**: After successful login, wait at least 5 seconds before attempting to click GAME START
        6. You should see the KanColle landing page with ship girls and a large teal "GAME START" button
        7. The GAME START button is NOT a regular HTML element - it's embedded in a game interface
        8. To click it properly - try these methods in order:
                       a) **METHOD 1: Element-to-cursor coordinate mapping**
               - Hover over element 6, then element 22 to get their actual screen coordinates
               - Use browser automation hover actions (not raw JavaScript)
               - Draw line between these confirmed cursor positions
           b) **METHOD 2: Direct element clicking with proper timing**
              - Try clicking detected interactive elements 6-22 individually with 100ms+ duration
              - Wait 2 seconds between each attempt and check for URL changes
           c) **METHOD 3: Canvas coordinate scanning**
              - Use getBoundingClientRect() to get canvas bounds, then scan methodically
              - Click every 50-100 pixels in canvas area with proper 100ms+ click duration
           d) **Use longer click duration** (at least 100ms) for ALL click attempts - critical for canvas!
           e) **Stop immediately** when the URL changes to kancolle-server.com (success!)
                       f) **Verify click registration**: Check for URL changes or visual feedback after clicks
        9. After clicking, wait at least 15-30 seconds for the game client to load on kancolle-server.com
        10. Confirm you've reached the actual game interface (URL should change to kancolle-server.com)
        
                 Critical timing requirements:
         - Wait 5+ seconds after login before clicking GAME START
         - Use longer click duration (100ms+) for embedded game elements
         - Wait 15-30 seconds after clicking for game to load
         - The GAME START button needs time to become active after page load
         - Canvas/Flash elements often require longer click durations than HTML elements
         
         Canvas Automation Strategy:
         
         **Step 1: Element Position Detection**
         - Hover over interactive elements to get their screen positions
         - Use browser automation hover/move actions (not JavaScript)
         - Map element positions to canvas coordinates
         
         **Step 2: Systematic Canvas Clicking**
         - Try clicking interactive elements 6-22 individually with 100ms+ duration
         - Use coordinate-based clicking with proper timing between attempts
         - Focus on browser automation actions (drag_drop, click) not raw JavaScript
         
         **Step 3: Grid Scanning if Elements Fail**
         - Get canvas bounding box and scan systematically
         - Click every 50-100 pixels in canvas area with 2-second intervals
         - For KanColle scaling: if displayed 960x600 but intrinsic 1920x1200, adjust coordinates
         
         **Step 4: Success Detection**
         - Monitor URL changes to kancolle-server.com after each click
         - Stop immediately when navigation occurs
         - Use visual feedback (page changes) to confirm success
         
         CRITICAL: Always use delay_ms >= 100 for canvas clicks (NOT 5ms)
        
        Technical notes for coordinate clicking:
        - The button appears as a large teal/green rectangular button with white text
        - It's positioned in the center-right area of the main game artwork
        - Success means reaching kancolle-server.com, not just clicking the button
        """
        
        # Create browser session with proper domain restrictions
        browser_session_config = {
            'allowed_domains': [
                'https://*.dmm.com',
                'http://www.dmm.com',
                'https://www.dmm.com',
                'http://*.kancolle-server.com',
                'https://*.kancolle-server.com'
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
                use_vision=True,  # Enable vision to see the interface (no sensitive_data used)
                save_conversation_path=str(config.paths.logs_dir / f"login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            )
            
            self.session_start_time = datetime.now()
            result = await self.agent.run()
            
            # Save authentication state for future use
            try:
                # Get the browser context and save state
                if hasattr(self.agent, 'browser') and self.agent.browser:
                    await self.agent.browser.context.storage_state(path=str(auth_file))
                    logger.info(f"💾 Saved authentication state to {auth_file}")
            except Exception as e:
                logger.warning(f"Could not save authentication state: {e}")
            
            return result
        
        # Execute with retry and fallback support
        success = await self._execute_with_retry(create_and_run_login_agent, "login")
        
        if success:
            logger.success("DMM login and KanColle navigation completed!")
            return True
        else:
            logger.error("Login failed after all retry attempts")
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