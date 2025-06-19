import asyncio
import os
import warnings
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

# === COMPLETE ERROR SUPPRESSION ===
logging.getLogger('pyrogram').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
warnings.filterwarnings('ignore', category=RuntimeWarning, module='asyncio')

# Configure clean main logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Monkey patch to suppress pyrogram errors
original_handle_updates = Client.handle_updates
async def patched_handle_updates(self, updates):
    try:
        await original_handle_updates(self, updates)
    except (ValueError, KeyError):
        pass
    except Exception as e:
        if "Peer id invalid" not in str(e) and "ID not found" not in str(e):
            logger.error(f"Unexpected error: {e}")
Client.handle_updates = patched_handle_updates

class TelegramDualAccountBotWithForward:
    def __init__(self):
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')

        # Session strings
        self.string_session_account1 = os.getenv('ACCOUNT1_SESSION')
        self.string_session_account2 = os.getenv('ACCOUNT2_SESSION')

        # Bot and channel settings
        self.bot_username = os.getenv('BOT_USERNAME')
        self.forward_channel = os.getenv('FORWARD_CHANNEL')  # Your channel to forward to

        # Messages
        self.message_account1 = os.getenv('MESSAGE_ACCOUNT1', 'Hello from Account 1! 🚀')
        self.message_account2 = os.getenv('MESSAGE_ACCOUNT2', 'Hello from Account 2! 🎯')

        # Options
        self.add_counter = os.getenv('ADD_COUNTER', 'false').lower() == 'true'
        self.add_timestamp = os.getenv('ADD_TIMESTAMP', 'false').lower() == 'true'
        self.execution_mode = os.getenv('EXECUTION_MODE', 'concurrent').lower()
        self.send_on_start = os.getenv('SEND_ON_START', 'false').lower() == 'true'

        # Auto-forward settings
        self.auto_forward_enabled = os.getenv('AUTO_FORWARD', 'true').lower() == 'true'
        self.forward_videos_only = os.getenv('FORWARD_VIDEOS_ONLY', 'true').lower() == 'true'

        # Validate required variables
        if not all([self.api_id, self.api_hash, self.bot_username]):
            raise ValueError("Missing required: API_ID, API_HASH, BOT_USERNAME")

        if not all([self.string_session_account1, self.string_session_account2]):
            raise ValueError("Both ACCOUNT1_SESSION and ACCOUNT2_SESSION are required")

        if self.auto_forward_enabled and not self.forward_channel:
            raise ValueError("FORWARD_CHANNEL is required when AUTO_FORWARD is enabled")

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

        # Setup message handlers for auto-forwarding
        if self.auto_forward_enabled:
            self.setup_message_handlers()

        # Log configuration
        logger.info("🎭 Telegram Dual Account Bot with Auto-Forward Starting...")
        logger.info(f"⚙️ Mode: {self.execution_mode.upper()} | Target: {self.bot_username}")
        logger.info(f"🚀 Send on Start: {'YES' if self.send_on_start else 'NO'}")
        logger.info(f"📨 Auto Forward: {'YES' if self.auto_forward_enabled else 'NO'}")
        if self.auto_forward_enabled:
            logger.info(f"📤 Forward Channel: {self.forward_channel}")
            logger.info(f"🎥 Videos Only: {'YES' if self.forward_videos_only else 'NO'}")

    def setup_message_handlers(self):
        """Setup message handlers for both accounts"""

        # Handler for Account 1
        @self.client_account1.on_message(
            filters.chat(self.bot_username) & 
            (filters.video | filters.document | filters.photo | filters.text)
        )
        async def handle_bot_response_account1(client: Client, message: Message):
            await self.handle_bot_response(client, message, "Account 1")

        # Handler for Account 2
        @self.client_account2.on_message(
            filters.chat(self.bot_username) & 
            (filters.video | filters.document | filters.photo | filters.text)
        )
        async def handle_bot_response_account2(client: Client, message: Message):
            await self.handle_bot_response(client, message, "Account 2")

    async def handle_bot_response(self, client: Client, message: Message, account_name: str):
        """Handle responses from the bot and forward them"""
        try:
            # Check if we should forward this message
            should_forward = False

            if self.forward_videos_only:
                # Only forward if it's a video or video document
                should_forward = (
                    message.video or 
                    (message.document and message.document.mime_type and 
                     message.document.mime_type.startswith('video/'))
                )
            else:
                # Forward any media or text
                should_forward = True

            if should_forward:
                # Forward the message to your channel
                await client.forward_messages(
                    chat_id=self.forward_channel,
                    from_chat_id=message.chat.id,
                    message_ids=message.id
                )

                media_type = "video" if message.video else "file" if message.document else "message"
                logger.info(f"📤 {account_name}: Forwarded {media_type} to {self.forward_channel}")

        except Exception as e:
            logger.error(f"❌ {account_name}: Forward error - {e}")

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
        if self.auto_forward_enabled:
            logger.info("📨 Auto-forward is active - waiting for bot responses...")

    async def start(self):
        """Start clients and scheduler"""
        try:
            # Start clients
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

            # Keep running to handle incoming messages
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
    bot = TelegramDualAccountBotWithForward()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
