import asyncio
import os
from datetime import datetime
from pyrogram import Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

        # Default values - no need to set during deployment
        self.execution_mode = os.getenv('EXECUTION_MODE', 'concurrent').lower()
        self.send_on_start = os.getenv('SEND_ON_START', 'false').lower() == 'true'

        # Validate required variables only
        if not all([self.api_id, self.api_hash, self.bot_username]):
            raise ValueError("Missing required: API_ID, API_HASH, BOT_USERNAME")

        if not all([self.string_session_account1, self.string_session_account2]):
            raise ValueError("Both ACCOUNT1_SESSION and ACCOUNT2_SESSION are required")

        # Initialize clients for both accounts
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

        # Log configuration
        logger.info(f"⚙️ Configuration loaded:")
        logger.info(f"   📋 Execution Mode: {self.execution_mode.upper()}")
        logger.info(f"   🚀 Send on Start: {'YES' if self.send_on_start else 'NO'}")
        logger.info(f"   🎯 Target Bot: {self.bot_username}")

    async def send_messages_account1(self):
        """Send 3 messages from Account 1 with 10-second intervals"""
        try:
            logger.info(f"🚀 Account 1: Starting to send messages to {self.bot_username}")

            for i in range(3):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                message_text = f"{self.message_account1} - Message {i+1}/3 at {timestamp}"

                await self.client_account1.send_message(
                    chat_id=self.bot_username,
                    text=message_text
                )

                logger.info(f"✅ Account 1: Sent message {i+1}/3 to {self.bot_username}")

                # Wait 10 seconds before next message (except for the last one)
                if i < 2:
                    await asyncio.sleep(10)

            logger.info("🎉 Account 1: All 3 messages sent successfully")

        except Exception as e:
            logger.error(f"❌ Account 1 Error: {e}")

    async def send_messages_account2(self):
        """Send 3 messages from Account 2 with 10-second intervals"""
        try:
            logger.info(f"🎯 Account 2: Starting to send messages to {self.bot_username}")

            for i in range(3):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                message_text = f"{self.message_account2} - Message {i+1}/3 at {timestamp}"

                await self.client_account2.send_message(
                    chat_id=self.bot_username,
                    text=message_text
                )

                logger.info(f"✅ Account 2: Sent message {i+1}/3 to {self.bot_username}")

                # Wait 10 seconds before next message (except for the last one)
                if i < 2:
                    await asyncio.sleep(10)

            logger.info("🎉 Account 2: All 3 messages sent successfully")

        except Exception as e:
            logger.error(f"❌ Account 2 Error: {e}")

    async def execute_concurrent_mode(self):
        """Both accounts send messages simultaneously"""
        logger.info("🔄 Executing CONCURRENT mode - Both accounts sending simultaneously")

        # Create tasks for both accounts
        task1 = asyncio.create_task(self.send_messages_account1())
        task2 = asyncio.create_task(self.send_messages_account2())

        # Run both accounts concurrently
        results = await asyncio.gather(task1, task2, return_exceptions=True)

        # Log results
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.error(f"Account {i} failed: {result}")
            else:
                logger.info(f"Account {i} completed successfully")

    async def execute_sequential_mode(self):
        """Accounts send messages one after another"""
        logger.info("⏭️ Executing SEQUENTIAL mode - Accounts sending one after another")

        # Account 1 first
        await self.send_messages_account1()

        # 30-second delay between accounts
        logger.info("⏱️ Waiting 30 seconds before Account 2...")
        await asyncio.sleep(30)

        # Account 2 second
        await self.send_messages_account2()

    async def daily_message_routine(self):
        """Main routine to send messages based on execution mode"""
        logger.info(f"🎬 Starting daily message routine in {self.execution_mode.upper()} mode")

        if self.execution_mode == 'sequential':
            await self.execute_sequential_mode()
        else:
            await self.execute_concurrent_mode()

        logger.info("✨ Daily message routine completed")

    async def start(self):
        """Start both clients and scheduler"""
        try:
            # Start Account 1 client
            await self.client_account1.start()
            logger.info("🚀 Account 1 client started successfully")

            # Start Account 2 client
            await self.client_account2.start()
            logger.info("🎯 Account 2 client started successfully")

            # Schedule daily execution at 9:00 AM UTC
            self.scheduler.add_job(
                self.daily_message_routine,
                'cron',
                hour=9,
                minute=0,
                timezone='UTC'
            )

            # Execute immediately if send_on_start is True
            if self.send_on_start:
                logger.info("🧪 SEND_ON_START enabled: Executing immediately for testing")
                await self.daily_message_routine()
            else:
                logger.info("⏰ SEND_ON_START disabled: Waiting for scheduled time (9:00 AM UTC)")

            self.scheduler.start()
            logger.info(f"📅 Scheduler started - Daily messages at 9:00 AM UTC in {self.execution_mode.upper()} mode")
            logger.info("🤖 Bot is running... Press Ctrl+C to stop")

            # Keep the script running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour

        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"💥 Critical error: {e}")
        finally:
            # Stop both clients
            try:
                await self.client_account1.stop()
                logger.info("🚀 Account 1 client stopped")
            except:
                pass

            try:
                await self.client_account2.stop()
                logger.info("🎯 Account 2 client stopped")
            except:
                pass

async def main():
    logger.info("🎭 Telegram Dual Account Bot Starting...")
    bot = TelegramDualAccountBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
