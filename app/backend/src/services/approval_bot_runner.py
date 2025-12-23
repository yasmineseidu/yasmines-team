"""
Production approval bot runner.

Runs the approval bot with long-polling, connecting the Telegram callback
handler to the PostgreSQL database for persistent approval workflows.

Usage:
    # Run directly:
    python -m src.services.approval_bot_runner

    # Or import and run:
    from src.services.approval_bot_runner import run_approval_bot
    asyncio.run(run_approval_bot())

Environment Variables Required:
    - TELEGRAM_BOT_TOKEN: Telegram bot API token
    - DATABASE_URL: PostgreSQL connection URL
    - APPROVAL_FORM_BASE_URL: Base URL for edit forms (optional)
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Reduce SQLAlchemy noise
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class ApprovalBotRunner:
    """
    Production runner for the approval bot.

    Handles:
    - Database connection management
    - Telegram long-polling
    - Graceful shutdown
    - Error recovery
    """

    def __init__(
        self,
        bot_token: str,
        edit_form_base_url: str = "https://app.example.com/approvals",
        poll_timeout: int = 30,
    ) -> None:
        """
        Initialize the bot runner.

        Args:
            bot_token: Telegram bot API token.
            edit_form_base_url: Base URL for edit forms.
            poll_timeout: Long-polling timeout in seconds.
        """
        self.bot_token = bot_token
        self.edit_form_base_url = edit_form_base_url
        self.poll_timeout = poll_timeout
        self._running = False
        self._last_update_id = 0

        # Will be initialized in start()
        self.telegram_client = None
        self.db = None
        self.approval_service = None
        self.handler = None

    async def start(self) -> None:
        """Initialize all components."""
        from src.database import AsyncDatabaseAdapter
        from src.integrations.approval_handler import ApprovalBotHandler
        from src.integrations.telegram import TelegramClient
        from src.services.approval_service import ApprovalService

        logger.info("Starting Approval Bot Runner...")

        # Initialize database
        logger.info("Connecting to database...")
        self.db = AsyncDatabaseAdapter()
        logger.info("Database connected")

        # Initialize Telegram client
        logger.info("Initializing Telegram client...")
        self.telegram_client = TelegramClient(bot_token=self.bot_token)

        # Verify bot connection
        me = await self.telegram_client.get_me()
        username = (
            getattr(me, "username", None) or me.get("username", "unknown")
            if isinstance(me, dict)
            else getattr(me, "username", "unknown")
        )
        logger.info(f"Bot connected: @{username}")

        # Initialize approval service with database
        logger.info("Initializing ApprovalService...")
        self.approval_service = ApprovalService(
            telegram_client=self.telegram_client,
            db=self.db,
            edit_form_base_url=self.edit_form_base_url,
        )

        # Initialize handler
        logger.info("Initializing callback handler...")
        self.handler = ApprovalBotHandler(
            telegram_client=self.telegram_client,
            approval_service=self.approval_service,
        )

        self._running = True
        logger.info("Approval Bot Runner started successfully!")
        logger.info(f"Edit form base URL: {self.edit_form_base_url}")

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        logger.info("Stopping Approval Bot Runner...")
        self._running = False

        if self.telegram_client:
            await self.telegram_client.close()
            logger.info("Telegram client closed")

        logger.info("Approval Bot Runner stopped")

    async def poll_updates(self) -> None:
        """
        Long-poll for Telegram updates and process them.

        Runs continuously until stopped.
        """
        logger.info("Starting long-polling for updates...")

        consecutive_errors = 0
        max_consecutive_errors = 10

        while self._running:
            try:
                # Get updates from Telegram
                updates = await self.telegram_client.get_updates(
                    offset=self._last_update_id + 1,
                    timeout=self.poll_timeout,
                    allowed_updates=["message", "callback_query"],
                )

                # Reset error counter on success
                consecutive_errors = 0

                # Process each update (already Update objects from get_updates)
                for update in updates:
                    update_id = update.update_id
                    self._last_update_id = max(self._last_update_id, update_id)

                    try:
                        # Process through handler
                        await self.handler.process_update(update)

                    except Exception as e:
                        logger.error(f"Error processing update {update_id}: {e}", exc_info=True)

            except asyncio.CancelledError:
                logger.info("Polling cancelled")
                break

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error polling updates: {e}", exc_info=True)

                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"Too many consecutive errors ({consecutive_errors}), stopping")
                    self._running = False
                    break

                # Exponential backoff
                wait_time = min(2**consecutive_errors, 60)
                logger.info(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)

    async def run(self) -> None:
        """Run the bot (start + poll)."""
        await self.start()

        try:
            await self.poll_updates()
        finally:
            await self.stop()


async def run_approval_bot() -> None:
    """
    Main entry point for running the approval bot.

    Loads configuration from environment and runs the bot.
    """
    # Load environment
    from dotenv import load_dotenv

    # Try to find .env file
    env_paths = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path.cwd().parent.parent / ".env",
        Path(__file__).parents[3] / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_path}")
            break

    # Get configuration
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.critical("TELEGRAM_BOT_TOKEN environment variable is required")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.critical("DATABASE_URL environment variable is required")
        sys.exit(1)

    edit_form_base_url = os.getenv("APPROVAL_FORM_BASE_URL", "https://app.example.com/approvals")

    # Create runner
    runner = ApprovalBotRunner(
        bot_token=bot_token,
        edit_form_base_url=edit_form_base_url,
    )

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        runner._running = False

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Run the bot
    logger.info("=" * 60)
    logger.info("APPROVAL BOT STARTING")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    await runner.run()


if __name__ == "__main__":
    asyncio.run(run_approval_bot())
