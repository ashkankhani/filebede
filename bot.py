"""Telegram Bot for file downloading with Local Bot API support."""
import os
import logging
import asyncio
from datetime import datetime

import aiohttp
from telebot.async_telebot import AsyncTeleBot
from telebot import asyncio_helper
from telebot.types import Message

from config import config
from downloader import downloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/filebede.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Monkey-patch for Local Bot API
asyncio_helper.API_URL = f"{config.BOT_API_SERVER}/bot{{0}}/{{1}}"

# Initialize bot
bot = AsyncTeleBot(config.BOT_TOKEN)


@bot.message_handler(func=lambda m: True)
async def handle_message(message: Message):
    """Handle incoming messages with URLs."""
    url = message.text.strip()
    start_time = datetime.now()
    
    logger.info(f"Request from {message.from_user.id}: {url}")

    if not url.startswith(("http://", "https://")):
        await bot.reply_to(message, "لینک معتبر نیست.")
        return

    progress_msg = None
    filepath = None
    
    try:
        progress_msg = await bot.reply_to(message, "درحال دانلود...")
        
        # Progress callback
        async def progress_callback(downloaded: int, total: int, percentage: float):
            nonlocal progress_msg
            try:
                if total > 0:
                    downloaded_mb = downloaded / 1024 / 1024
                    total_mb = total / 1024 / 1024
                    text = f"درحال دانلود... {percentage:.0f}% | {downloaded_mb:.1f} MB / {total_mb:.1f} MB"
                else:
                    downloaded_mb = downloaded / 1024 / 1024
                    text = f"درحال دانلود... {downloaded_mb:.1f} MB"
                
                await bot.edit_message_text(text, message.chat.id, progress_msg.message_id)
            except Exception as e:
                logger.warning(f"Progress update failed: {e}")
        
        # Download file
        result = await downloader.download(url, progress_callback)
        
        if not result.success:
            await bot.edit_message_text(f"خطا: {result.error}", message.chat.id, progress_msg.message_id)
            return
        
        filepath = result.filepath
        filename = result.filename
        file_size = result.total_size
        
        logger.info(f"Download complete: {filename} ({file_size} bytes)")
        
        # Send file
        await bot.edit_message_text("درحال ارسال...", message.chat.id, progress_msg.message_id)
        
        # Use Local Bot API for large files
        if file_size > 50 * 1024 * 1024:  # > 50MB
            logger.info(f"Using Local Bot API for {file_size} bytes")
            try:
                async with aiohttp.ClientSession() as session:
                    with open(filepath, "rb") as file_data:
                        form = aiohttp.FormData()
                        form.add_field('chat_id', str(message.chat.id))
                        form.add_field('document', file_data, filename=filename)
                        
                        async with session.post(
                            f"{config.BOT_API_SERVER}/bot{config.BOT_TOKEN}/sendDocument",
                            data=form
                        ) as resp:
                            result = await resp.json()
                            if not result.get('ok'):
                                logger.error(f"Local Bot API failed: {result}")
                                # Fallback to normal API
                                with open(filepath, "rb") as f:
                                    await bot.send_document(chat_id=message.chat.id, document=f)
                            else:
                                logger.info("File sent via Local Bot API")
            except Exception as e:
                logger.error(f"Local Bot API error: {e}")
                with open(filepath, "rb") as f:
                    await bot.send_document(chat_id=message.chat.id, document=f)
        else:
            logger.info(f"Using Normal API for {file_size} bytes")
            with open(filepath, "rb") as f:
                await bot.send_document(chat_id=message.chat.id, document=f)
            logger.info("File sent via Normal API")
        
        await bot.delete_message(message.chat.id, progress_msg.message_id)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Success: {filename} sent in {elapsed:.1f}s")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        try:
            await bot.reply_to(message, f"خطا: {str(e)[:200]}")
        except Exception:
            pass

    finally:
        # Cleanup temp file
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Cleanup: {filepath}")


async def main():
    """Start the bot."""
    logger.info(f"Bot starting with Local Bot API: {config.BOT_API_SERVER}")
    logger.info(f"Download directory: {config.DOWNLOAD_DIR}")
    
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(main())
