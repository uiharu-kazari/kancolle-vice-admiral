#!/usr/bin/env python3
"""
KanColle Vice Admiral - Main Entry Point
An intelligent automation system for 艦隊これくしょん (Kantai Collection)
"""

import asyncio
import argparse
import sys
from pathlib import Path
from loguru import logger
from kancolle_vice_admiral.config import config
from kancolle_vice_admiral.browser_automation import KanColleBrowserAutomation, quick_login, run_daily_tasks


def setup_logging():
    """Setup logging configuration"""
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stderr,
        level=config.automation.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # File logging
    log_file = config.paths.logs_dir / "kancolle_automation.log"
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="30 days",
        compression="gz"
    )
    
    logger.info("Logging setup completed")


async def login_command():
    """Login to DMM and navigate to KanColle"""
    logger.info("🚢 Starting KanColle Vice Admiral - Login Command")
    
    try:
        automation = await quick_login()
        logger.success("✅ Login completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        return False


async def generate_script_command(task: str):
    """Generate automation script for a specific task"""
    logger.info(f"🤖 Generating automation script for: {task}")
    
    try:
        automation = KanColleBrowserAutomation()
        
        # Login first
        if not await automation.login_to_dmm_and_kancolle():
            logger.error("Failed to login")
            return False
        
        # Generate script
        script = await automation.generate_automation_script(task)
        
        if script:
            logger.success(f"✅ Script generated successfully for task: {task}")
            return True
        else:
            logger.error("❌ Failed to generate script")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script generation failed: {e}")
        return False


async def execute_task_command(task: str):
    """Execute a specific KanColle task"""
    logger.info(f"⚡ Executing task: {task}")
    
    try:
        automation = KanColleBrowserAutomation()
        
        # Login first
        if not await automation.login_to_dmm_and_kancolle():
            logger.error("Failed to login")
            return False
        
        # Execute task
        success = await automation.execute_task(task)
        
        if success:
            logger.success(f"✅ Task completed successfully: {task}")
            return True
        else:
            logger.error(f"❌ Task failed: {task}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Task execution failed: {e}")
        return False


async def daily_tasks_command():
    """Run daily tasks automatically"""
    logger.info("📅 Running daily KanColle tasks")
    
    try:
        await run_daily_tasks()
        logger.success("✅ Daily tasks completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Daily tasks failed: {e}")
        return False


def validate_environment():
    """Validate environment and configuration"""
    logger.info("🔍 Validating environment...")
    
    try:
        # Check if .env file exists
        env_file = Path(".env")
        if not env_file.exists():
            logger.warning("No .env file found. Please copy .env.example to .env and configure it.")
            logger.info("Example: cp .env.example .env")
            return False
        
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            return False
        
        logger.success("✅ Environment validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Environment validation failed: {e}")
        return False


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="KanColle Vice Admiral - Intelligent automation for 艦隊これくしょん",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py login                           # Login to DMM and KanColle
  python main.py generate "daily expeditions"   # Generate script for daily expeditions
  python main.py execute "collect daily missions" # Execute a specific task
  python main.py daily                          # Run all daily tasks
  python main.py validate                       # Validate environment setup

しまかぜ、出撃しまーす！ ⚓
        """
    )
    
    parser.add_argument(
        "command",
        choices=["login", "generate", "execute", "daily", "validate"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "task",
        nargs="?",
        help="Task description (required for 'generate' and 'execute' commands)"
    )
    

    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Override config with CLI arguments
    if args.debug:
        config.automation.log_level = "DEBUG"
    
    # Setup logging
    setup_logging()
    
    logger.info("🚢 KanColle Vice Admiral Starting...")
    logger.info(f"Command: {args.command}")
    
    # Validate environment unless it's the validate command
    if args.command != "validate" and not validate_environment():
        sys.exit(1)
    
    try:
        if args.command == "validate":
            success = validate_environment()
        elif args.command == "login":
            success = asyncio.run(login_command())
        elif args.command == "generate":
            if not args.task:
                logger.error("Task description is required for 'generate' command")
                parser.print_help()
                sys.exit(1)
            success = asyncio.run(generate_script_command(args.task))
        elif args.command == "execute":
            if not args.task:
                logger.error("Task description is required for 'execute' command")
                parser.print_help()
                sys.exit(1)
            success = asyncio.run(execute_task_command(args.task))
        elif args.command == "daily":
            success = asyncio.run(daily_tasks_command())
        else:
            logger.error(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)
        
        if success:
            logger.info("🎉 Command completed successfully!")
            logger.info("しまかぜ、出撃しまーす！ ⚓")
        else:
            logger.error("💥 Command failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 