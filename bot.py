import asyncio
import aiohttp
import logging
import os
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_KEY = os.getenv("FOOTBALL_API_KEY")

bot = Bot(token=TOKEN)

# Основной хост для хоккея
HOST = 'v1.hockey.api-sports.io'
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': HOST
}

async def get_games(session, url):
    async with session.get(url, headers=HEADERS) as resp:
        return await resp.json()

async def check_all_games():
    logger.info("--- ЗАПУСК ЖЕСТКОГО ТЕСТА LIVE ИГР ---")
    
    async with aiohttp.ClientSession() as session:
        # Пробуем разные варианты запроса лайва, которые бывают у этого API
        urls = [
            f"https://{HOST}/games?live=all",
            f"https://{HOST}/games?live=1"
        ]
        
        data = None
        for url in urls:
            logger.info(f"Пробую URL: {url}")
            res = await get_games(session, url)
            if res.get('response'):
                data = res
                break
        
        if not data or not data.get('response'):
            error_info = data.get('errors') if data else "Нет ответа"
            msg = f"API не отдает LIVE. Ошибка: {error_info}"
            logger.error(msg)
            await bot.send_message(CHANNEL_ID, f"❌ {msg}\n(Возможно, в бесплатном тарифе хоккея лайв ограничен)")
            return

        games = data['response']
        logger.info(f"Найдено LIVE игр: {len(games)}")
        await bot.send_message(CHANNEL_ID, f"🔥 **ЕСТЬ КОНТАКТ! ВИЖУ {len(games)} ИГР В ЛАЙВЕ:**")

        for game in games:
            home = game['teams']['home']['name']
            away = game['teams']['away']['name']
            league = game['league']['name']
            
            # В хоккее счет лежит в 'scores'
            s = game.get('scores', {})
            h_s = s.get('home', 0) if s.get('home') is not None else 0
            a_s = s.get('away', 0) if s.get('away') is not None else 0
            
            # Период
            status = game.get('status', {}).get('short', 'LIVE')

            text = (
                f"🏒 **{home} — {away}**\n"
                f"🏆 {league}\n"
                f"📊 Счет: {h_s}:{a_s}\n"
                f"⏱ Период: {status}"
            )
            await bot.send_message(CHANNEL_ID, text)
            await asyncio.sleep(0.3)

if __name__ == "__main__":
    asyncio.run(check_all_games())
