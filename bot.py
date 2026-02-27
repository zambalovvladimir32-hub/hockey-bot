import asyncio
import os
import aiohttp
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Прямой фид, который обычно не режут
URL = "https://v3.icehockey.api-sports.io/games?live=all"
HEADERS = {"x-apisports-key": "4955734208e684078864f16b677a8b4b"} # Общий тестовый ключ

async def check():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=10) as resp:
                data = await resp.json()
                for g in data.get('response', []):
                    t1, t2 = g['teams']['home']['name'], g['teams']['away']['name']
                    status = g['status']['short']
                    if status == "2P" or "Norilsk" in t1:
                        await bot.send_message(CHANNEL_ID, f"🏒 {t1} - {t2}\n⏱ Статус: {status}")
        except:
            pass

async def main():
    while True:
        await check()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
