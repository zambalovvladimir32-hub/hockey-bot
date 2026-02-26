import asyncio
import aiohttp
import os
import logging
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_KEY = os.getenv("FOOTBALL_API_KEY") # Твой ключ RapidAPI

bot = Bot(token=TOKEN)

# Используем официальный мост RapidAPI - он не блокируется хостингами
URL = "https://flashscore-pro.p.rapidapi.com/v1/hockey/live"
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "flashscore-pro.p.rapidapi.com"
}

async def get_flashscore_live():
    logger.info("Запрос к Flashscore через мост RapidAPI...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, headers=HEADERS, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Формат RapidAPI обычно возвращает список в ключе 'data' или напрямую
                    games = data if isinstance(data, list) else data.get('data', [])
                    
                    if not games:
                        await bot.send_message(CHANNEL_ID, "🏒 **Связь с Flashscore через RapidAPI ОК!**\n\nНочных матчей в лайве сейчас нет. Жду утра.")
                        return

                    text = "🏒 **МАТЧИ В LIVE (FLASHSCORE):**\n\n"
                    for g in games[:10]:
                        home = g.get('home_name')
                        away = g.get('away_name')
                        score = f"{g.get('score_home', 0)}:{g.get('score_away', 0)}"
                        league = g.get('league_name', 'Хоккей')
                        text += f"🏆 {league}\n⚔️ {home} — {away}\n📊 Счет: `{score}`\n\n"
                    
                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                    logger.info("Успешно! Данные отправлены в канал.")
                else:
                    logger.error(f"Ошибка RapidAPI: {resp.status}")
                    await bot.send_message(CHANNEL_ID, f"⚠️ RapidAPI ответил ошибкой: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await bot.send_message(CHANNEL_ID, "🚫 Даже RapidAPI заблокирован. Amvera ограничивает внешние связи.")

if __name__ == "__main__":
    asyncio.run(get_flashscore_live())
