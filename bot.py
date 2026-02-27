import aiohttp
import asyncio
import os
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def pro_parser():
    # Мы имитируем запрос от мобильного приложения Flashscore
    url = "https://d.flashscore.com/x/feed/f_4_0_2_ru-ru_1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
        "x-fsign": "SW9D1eZo", # Ключ, который ты нашел
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # Если Норильск есть в этом куске текста — отправляем сигнал
                    if "Norilsk" in text or "Норильск" in text:
                        await bot.send_message(CHANNEL_ID, "🎯 **PRO-СИГНАЛ: МАТЧ НАЙДЕН!**\nСвязь с фидом Flashscore стабильна.")
                else:
                    print(f"Ошибка: {resp.status}. Пора менять прокси или ключ.")
        except Exception as e:
            print(f"Ошибка коннекта: {e}")

async def main():
    while True:
        await pro_parser()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
