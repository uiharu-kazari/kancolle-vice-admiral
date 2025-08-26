"""
Configuration module for KanColle Vice Admiral
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from loguru import logger

# Load environment variables from .env file
load_dotenv()


class AIConfig(BaseModel):
    """AI model configuration"""
    api_key: str = Field(..., description="Google API key")
    model: str = Field(default="gemini-2.5-flash-preview-05-20", description="Primary AI model to use")
    fallback_models: list[str] = Field(
        default=[
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.5-flash-preview-04-17", 
            "gemini-2.0-flash"
        ],
        description="Fallback models to try when rate limited"
    )


class DMMConfig(BaseModel):
    """DMM account configuration"""
    email: str = Field(..., description="DMM account email")
    password: str = Field(..., description="DMM account password")


class AutomationConfig(BaseModel):
    """Automation settings"""
    retry_count: int = Field(default=3, description="Number of retries for failed actions")
    screenshot_on_error: bool = Field(default=True, description="Take screenshot on error")
    log_level: str = Field(default="INFO", description="Logging level")
    enable_ai_intervention: bool = Field(default=True, description="Enable AI intervention on errors")
    max_automation_time_minutes: int = Field(default=60, description="Maximum automation time")
    pause_between_actions_ms: int = Field(default=1000, description="Pause between actions")


class PathConfig(BaseModel):
    """File path configuration"""
    scripts_output_dir: Path = Field(default=Path("./generated_scripts"))
    logs_dir: Path = Field(default=Path("./logs"))
    screenshots_dir: Path = Field(default=Path("./screenshots"))
    assets_dir: Path = Field(default=Path("./kancolle_vice_admiral/assets"))

    def create_directories(self) -> None:
        """Create all required directories if they don't exist"""
        for path in [self.scripts_output_dir, self.logs_dir, self.screenshots_dir]:
            path.mkdir(parents=True, exist_ok=True)


class KanColleConfig(BaseModel):
    """KanColle game configuration"""
    url: str = Field(default="http://www.dmm.com/netgame/social/-/gadgets/=/app_id=854854")
    region: str = Field(default="jp")


class Config:
    """Main configuration class"""
    
    def __init__(self):
        try:
            self.ai = AIConfig(
                api_key=self._get_required_env("GEMINI_API_KEY"),
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-05-20")
            )
            
            self.dmm = DMMConfig(
                email=self._get_required_env("DMM_EMAIL"),
                password=self._get_required_env("DMM_PASSWORD")
            )
            
            self.automation = AutomationConfig(
                retry_count=int(os.getenv("AUTO_RETRY_COUNT", "3")),
                screenshot_on_error=os.getenv("SCREENSHOT_ON_ERROR", "true").lower() == "true",
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                enable_ai_intervention=os.getenv("ENABLE_AI_INTERVENTION", "true").lower() == "true",
                max_automation_time_minutes=int(os.getenv("MAX_AUTOMATION_TIME_MINUTES", "60")),
                pause_between_actions_ms=int(os.getenv("PAUSE_BETWEEN_ACTIONS_MS", "1000"))
            )
            
            self.paths = PathConfig(
                scripts_output_dir=Path(os.getenv("SCRIPTS_OUTPUT_DIR", "./generated_scripts")),
                logs_dir=Path(os.getenv("LOGS_DIR", "./logs")),
                screenshots_dir=Path(os.getenv("SCREENSHOTS_DIR", "./screenshots")),
                assets_dir=Path(os.getenv("ASSETS_DIR", "./kancolle_vice_admiral/assets"))
            )
            
            self.kancolle = KanColleConfig(
                url=os.getenv("KANCOLLE_URL", "http://www.dmm.com/netgame/social/-/gadgets/=/app_id=854854"),
                region=os.getenv("GAME_REGION", "jp")
            )
            
            # Create necessary directories
            self.paths.create_directories()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _get_required_env(self, key: str) -> str:
        """Get required environment variable"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Validate API key format (basic check)
            if not self.ai.api_key.startswith("AI"):
                logger.warning("Google API key might be in incorrect format")
            
            # Validate email format (basic check)
            if "@" not in self.dmm.email:
                logger.error("DMM email appears to be invalid")
                return False
            
            # Security reminder about credential handling
            logger.info("🔒 Security: DMM credentials will be handled securely using browser-use sensitive_data feature")
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Global configuration instance
config = Config() 