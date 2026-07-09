import os
import aiohttp
import asyncio
import mimetypes
import uuid

from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message

TOKEN = "7174467593:AAFGZyqJT5LE_NkjnFVQfmB_iZIu2Aneqek"

bot = AsyncTeleBot(TOKEN)


@bot.message_handler(func=lambda m: True)
async def download_and_send(message: Message):
    url = message.text.strip()

    if not url.startswith(("http://", "https://")):
        await bot.reply_to(message, "لینک معتبر نیست.")
        return

    try:
        msg = await bot.reply_to(message, "درحال دانلود...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()

                # Get content type
                content_type = response.headers.get("Content-Type", "")
                ext = mimetypes.guess_extension(content_type.split(';')[0]) or ""
                
                # Determine filename
                filename_from_url = url.split("/")[-1].split("?")[0]
                if not filename_from_url or "." not in filename_from_url:
                    filename = f"file_{uuid.uuid4().hex[:8]}{ext}"
                else:
                    name, base_ext = os.path.splitext(filename_from_url)
                    if len(name) > 20:
                        name = name[:20] + "_" + uuid.uuid4().hex[:4]
                    filename = f"{name}{base_ext or ext}"

                total_size = int(response.headers.get('Content-Length', 0))
                downloaded_size = 0
                last_progress = -1

                with open(filename, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            if progress // 10 > last_progress:  # Update every 10%
                                last_progress = progress // 10
                                try:
                                    await bot.edit_message_text(f"درحال دانلود... {progress}%", message.chat.id, msg.message_id)
                                except:
                                    pass

        await bot.edit_message_text("درحال ارسال...", message.chat.id, msg.message_id)
        with open(filename, "rb") as f:
            await bot.send_document(
                chat_id=message.chat.id,
                document=f
            )
        await bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        await bot.reply_to(message, f"خطا:\n{e}")

    finally:
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)


async def main():
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(main())
