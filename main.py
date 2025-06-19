import asyncio
import os
import warnings
from datetime import datetime
from pyrogram import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# === COMPLETE ERROR SUPPRESSION ===
# Suppress all pyrogram and asyncio noise
logging.getLogger('pyrogram').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

# Suppress asyncio task warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, module='asyncio')

# Configure clean main logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Monkey patch to suppress specific pyrogram errors
original_handle_updates = Client.handle_updates

async def patched_handle_updates(self, updates):
    try:
        await original_handle_updates(self, updates)
    except (ValueError, KeyError):
        # Silently ignore peer resolution errors
        pass
    except Exception as e:
        # Only log non-peer errors
        if "Peer id invalid" not in str(e) and "ID not found" not in str(e):
            logger.error(f"Unexpected error: {e}")

Client.handle_updates = patched_handle_updates

class TelegramDualAccountBot:
    def __init__(self):
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')

        # Two account session strings
        self.string_session_account1 = os.getenv('ACCOUNT1_SESSION')
        self.string_session_account2 = os.getenv('ACCOUNT2_SESSION')

        self.bot_username = os.getenv('BOT_USERNAME')
        self.message_account1 = os.getenv('MESSAGE_ACCOUNT1', 'Hello from Account 1! 🚀')
        self.message_account2 = os.getenv('MESSAGE_ACCOUNT2', 'Hello from Account 2! 🎯')

        # Message format options
        self.add_counter = os.getenv('ADD_COUNTER', 'false').lower() == 'true'
        self.add_timestamp = os.getenv('ADD_TIMESTAMP', 'false').lower() == 'true'

        # Default values
        self.execution_mode = os.getenv('EXECUTION_MODE', 'concurrent').lower()
        self.send_on_start = os.getenv('SEND_ON_START', 'false').lower() == 'true'

        # Validate required variables
        if not all([self.api_id, self.api_hash, self.bot_username]):
            raise ValueError("Missing required: API_ID, API_HASH, BOT_USERNAME")

        if not all([self.string_session_account1, self.string_session_account2]):
            raise ValueError("Both ACCOUNT1_SESSION and ACCOUNT2_SESSION are required")

        # Initialize clients
        self.client_account1 = Client(
            "account1_session",
            api_id=self.api_id,
            api_hash=self.api_hash,
            session_string=self.string_session_account1
        )

        self.client_account2 = Client(
            "account2_session",
            api_id=self.api_id,
            api_hash=self.api_hash,
            session_string=self.string_session_account2
        )

        self.scheduler = AsyncIOScheduler()

        # Clean configuration log
        logger.info("🎭 Telegram Dual Account Bot Starting...")
        logger.info(f"⚙️ Mode: {self.execution_mode.upper()} | Target: {self.bot_username}")
        logger.info(f"🚀 Send on Start: {'YES' if self.send_on_start else 'NO'}")

    def format_message(self, base_message, message_number, account_name):
        """Format message based on settings"""
        message = base_message

        if self.add_counter:
            message += f" - Message {message_number}/3"

        if self.add_timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message += f" at {timestamp}"

        return message

    async def send_messages_account1(self):
        """Send 3 messages from Account 1"""
        try:
            logger.info("🚀 Account 1: Sending messages...")

            for i in range(3):
                message_text = self.format_message(self.message_account1, i+1, "Account 1")

                await self.client_account1.send_message(
                    chat_id=self.bot_username,
                    text=message_text
                )

                if i < 2:
                    await asyncio.sleep(10)

            logger.info("✅ Account 1: All messages sent successfully")

        except Exception as e:
            logger.error(f"❌ Account 1 Error: {e}")

    async def send_messages_account2(self):
        """Send 3 messages from Account 2"""
        try:
            logger.info("🎯 Account 2: Sending messages...")

            for i in range(3):
                message_text = self.format_message(self.message_account2, i+1, "Account 2")

                await self.client_account2.send_message(
                    chat_id=self.bot_username,
                    text=message_text
                )

                if i < 2:
                    await asyncio.sleep(10)

            logger.info("✅ Account 2: All messages sent successfully")

        except Exception as e:
            logger.error(f"❌ Account 2 Error: {e}")

    async def execute_concurrent_mode(self):
        """Both accounts send messages simultaneously"""
        logger.info("🔄 Executing CONCURRENT mode...")

        task1 = asyncio.create_task(self.send_messages_account1())
        task2 = asyncio.create_task(self.send_messages_account2())

        await asyncio.gather(task1, task2, return_exceptions=True)

    async def execute_sequential_mode(self):
        """Accounts send messages one after another"""
        logger.info("⏭️ Executing SEQUENTIAL mode...")

        await self.send_messages_account1()
        logger.info("⏱️ Waiting 30 seconds...")
        await asyncio.sleep(30)
        await self.send_messages_account2()

    async def daily_message_routine(self):
        """Main routine to send messages"""
        logger.info("🎬 Starting daily message routine...")

        if self.execution_mode == 'sequential':
            await self.execute_sequential_mode()
        else:
            await self.execute_concurrent_mode()

        logger.info("✨ Daily routine completed successfully")

    async def start(self):
        """Start clients and scheduler"""
        try:
            # Start clients silently
            await self.client_account1.start()
            await self.client_account2.start()
            logger.info("🔗 Both accounts connected successfully")

            # Schedule daily execution
            self.scheduler.add_job(
                self.daily_message_routine,
                'cron',
                hour=9,
                minute=0,
                timezone='UTC'
            )

            # Execute immediately if enabled
            if self.send_on_start:
                logger.info("🧪 Testing mode activated")
                await self.daily_message_routine()

            self.scheduler.start()
            logger.info("📅 Scheduler started - Daily messages at 9:00 AM UTC")
            logger.info("🤖 Bot is running smoothly...")

            # Keep running
            while True:
                await asyncio.sleep(3600)

        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"💥 Critical error: {e}")
        finally:
            try:
                await self.client_account1.stop()
                await self.client_account2.stop()
                logger.info("🛑 All clients stopped")
            except:
                pass

async def main():
    bot = TelegramDualAccountBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
