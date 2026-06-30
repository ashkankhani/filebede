import os
import aiohttp
import asyncio

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

    filename = url.split("/")[-1] or "file"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()

                with open(filename, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)

        with open(filename, "rb") as f:
            await bot.send_document(
                chat_id=message.chat.id,
                document=f
            )

    except Exception as e:
        await bot.reply_to(message, f"خطا:\n{e}")

    finally:
        if os.path.exists(filename):
            os.remove(filename)


async def main():
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(main())
