import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timedelta, timezone
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_KEY = os.getenv("FOOTBALL_API_KEY")
bot = Bot(token=TOKEN)

HOST = 'v1.hockey.api-sports.io'
HEADERS = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': HOST}

# Твой список ID
ALLOWED_LEAGUES = [57, 40, 51, 41, 120, 110, 66, 114, 182, 185, 17]

async def check_all_live_leagues():
    logger.info("=== ЗАПУСК ДИАГНОСТИКИ ВСЕХ ЛИГ В LIVE ===")
    
    # Берем матчи за сегодня
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%Y-%m-%d')
    url = f"https://{HOST}/games?date={today}"
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get(url, headers=HEADERS) as resp:
                data = await resp.json()
                games = data.get('response', [])
                
                if not games:
                    logger.info("В API сейчас вообще нет матчей.")
                    return

                logger.info(f"Найдено матчей в базе: {len(games)}")
                
                for game in games:
                    l_id = game['league']['id']
                    l_name = game['league']['name']
                    status = game['status']['short']
                    teams = f"{game['teams']['home']['name']} - {game['teams']['away']['name']}"
                    score = f"{game['scores']['home']}:{game['scores']['away']}"
                    
                    # Помечаем те, что входят в наш список
                    match_marker = "⭐⭐⭐ [В ТВОЕМ СПИСКЕ]" if l_id in ALLOWED_LEAGUES else "[Другая лига]"
                    
                    # Выводим инфу по каждому матчу в консоль Amvera
                    logger.info(f"{match_marker} ID: {l_id} | Лига: {l_name} | Матч: {teams} | Статус: {status} | Счет: {score}")

                    # Если это наша лига и она в лайве — отправим тестовое сообщение в канал
                    if l_id in ALLOWED_LEAGUES and status not in ['FT', 'NS', 'AOT', 'CANC']:
                        test_msg = f"🔍 ТЕСТ: Вижу матч из списка!\nЛига ID: {l_id}\nЛига: {l_name}\nМатч: {teams}\nСтатус: {status}"
                        await bot.send_message(CHANNEL_ID, test_msg)

        except Exception as e:
            logger.error(f"Ошибка диагностики: {e}")

async def main():
    logger.info("Бот-детектор ID запущен.")
    while True:
        await check_all_live_leagues()
        await asyncio.sleep(300) # Проверка раз в 5 минут

if __name__ == "__main__":
    asyncio.run(main())
