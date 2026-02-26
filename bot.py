import asyncio
import aiohttp
import logging
import os
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ключи
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_KEY = os.getenv("FOOTBALL_API_KEY")

bot = Bot(token=TOKEN)

# Ссылка на все LIVE матчи по хоккею
URL = "https://v1.hockey.api-sports.io/games?live=all"
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v1.hockey.api-sports.io'
}

async def check_all_games():
    logger.info("--- ЗАПУСК ПОЛНОГО ТЕСТА ВСЕХ ИГР ---")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, headers=HEADERS) as resp:
                logger.info(f"Статус API: {resp.status}")
                data = await resp.json()
                
                if data.get('errors'):
                    error_msg = f"Ошибка API: {data['errors']}"
                    logger.error(error_msg)
                    await bot.send_message(CHANNEL_ID, f"❌ {error_msg}")
                    return

                games = data.get('response', [])
                
                if not games:
                    msg = "В данный момент активных LIVE-игр в API нет."
                    logger.info(msg)
                    await bot.send_message(CHANNEL_ID, f"ℹ️ {msg}")
                    return

                logger.info(f"Найдено игр: {len(games)}. Начинаю публикацию...")
                
                await bot.send_message(CHANNEL_ID, f"🚀 **НАЙДЕНО {len(games)} LIVE-ИГР:**")

                for game in games:
                    teams = f"{game['teams']['home']['name']} — {game['teams']['away']['name']}"
                    league = game['league']['name']
                    scores = game['scores']
                    h_score = scores['home'] if scores['home'] is not None else 0
                    a_score = scores['away'] if scores['away'] is not None else 0
                    status = game['status']['long']

                    text = (
                        f"🏒 **{teams}**\n"
                        f"🏆 {league}\n"
                        f"📊 Счет: {h_score}:{a_score}\n"
                        f"⏱ Статус: {status}\n"
                        f"----------------------------"
                    )
                    
                    await bot.send_message(CHANNEL_ID, text)
                    logger.info(f"Опубликован матч: {teams}")
                    await asyncio.sleep(0.5) # Пауза, чтобы телега не забанила за спам

                await bot.send_message(CHANNEL_ID, "✅ Весь список LIVE-игр выгружен.")

        except Exception as e:
            err = f"Критическая ошибка: {e}"
            logger.error(err)
            await bot.send_message(CHANNEL_ID, f"⚠️ {err}")

if __name__ == "__main__":
    asyncio.run(check_all_games())
