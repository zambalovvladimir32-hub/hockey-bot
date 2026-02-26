import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timezone, timedelta
from aiogram import Bot

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Данные из Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_KEY = os.getenv("FOOTBALL_API_KEY")

bot = Bot(token=TOKEN)

# Хост для хоккея
HOST = 'v1.hockey.api-sports.io'
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': HOST
}

async def check_live_games():
    # Получаем сегодняшнюю дату (МСК)
    today = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%Y-%m-%d')
    url = f"https://{HOST}/games?date={today}"
    
    logger.info(f"--- ЗАПРОС ИГР НА СЕГОДНЯ: {today} ---")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=HEADERS) as resp:
                data = await resp.json()
                
                if data.get('errors'):
                    logger.error(f"Ошибка API: {data['errors']}")
                    return

                all_games = data.get('response', [])
                if not all_games:
                    logger.info("На сегодня матчей в базе не найдено.")
                    return

                # Фильтруем те, что идут в LIVE (статусы периодов или просто LIVE)
                live_statuses = ['P1', 'P2', 'P3', 'OT', 'PSS', 'LIVE']
                live_games = [g for g in all_games if g.get('status', {}).get('short') in live_statuses]

                if not live_games:
                    msg = "В лайве сейчас пусто (в базе API нет активных игр)."
                    logger.info(msg)
                    # Можно не спамить в канал, если пусто, либо отправить один раз
                    return

                await bot.send_message(CHANNEL_ID, f"🏒 **НАЙДЕНО {len(live_games)} ИГР В ЛАЙВЕ:**")

                for game in live_games:
                    home = game['teams']['home']['name']
                    away = game['teams']['away']['name']
                    league = game['league']['name']
                    status = game['status']['long']
                    
                    scores = game.get('scores', {})
                    h_s = scores.get('home', 0) if scores.get('home') is not None else 0
                    a_s = scores.get('away', 0) if scores.get('away') is not None else 0

                    text = (
                        f"🏒 **{home} — {away}**\n"
                        f"🏆 {league}\n"
                        f"📊 Счет: {h_s}:{a_s}\n"
                        f"⏱ Статус: {status}"
                    )
                    await bot.send_message(CHANNEL_ID, text)
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Ошибка в коде: {e}")

if __name__ == "__main__":
    # Запускаем один раз для теста. Для постоянной работы нужно обернуть в while True
    asyncio.run(check_live_games())
