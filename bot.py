import asyncio
import aiohttp
import os
from aiogram import Bot

# Берем токен и ID канала из твоих настроек
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def scan_to_channel():
    # Ссылка на живую линию Фонбета
    url = "https://line01i.bkfon-resources.com/live/eventsList"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                
                text = "🔍 **СПИСОК ЛИГ ИЗ ФОНБЕТА:**\n\n"
                found = False
                
                # Собираем только хоккей
                for sport in data.get('sports', []):
                    # Отсеиваем всё, кроме хоккея
                    if 'хоккей' in sport.get('name', '').lower():
                        l_id = sport.get('id')
                        l_name = sport.get('name')
                        text += f"🆔 `{l_id}` — {l_name}\n"
                        found = True
                
                if not found:
                    text += "В данный момент хоккейных лиг в лайве не найдено."
                else:
                    text += "\n\n**Напиши мне ID нужных лиг из этого списка!**"

                # Отправляем прямо в твой канал
                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                print("Список отправлен в канал!")

        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(scan_to_channel())
