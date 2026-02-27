import asyncio
import os
import logging
import sys
from aiogram import Bot
import aiohttp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Используем открытый API, который Railway видит без проблем
URL = "https://www.thesportsdb.com/api/v1/json/3/latestsoccer.php?s=Hockey" # Универсальный фид для хоккея

async def check_hockey_stable():
    async with aiohttp.ClientSession() as session:
        try:
            logger.info("--- СКАНИРОВАНИЕ СПОРТИВНОЙ БАЗЫ ДАННЫХ ---")
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка API: {resp.status}")
                    return

                data = await resp.json()
                events = data.get('teams', []) # В этом API матчи часто лежат в 'teams' или 'events'
                
                if not events:
                    logger.info("В лайве сейчас пусто. Ждем ночных матчей НХЛ или утренних КХЛ.")
                    return

                for event in events:
                    t1 = event.get('strHomeTeam', '???')
                    t2 = event.get('strAwayTeam', '???')
                    league = event.get('strLeague', 'Хоккей')
                    
                    # Логируем всё, что видим
                    logger.info(f"ВИЖУ: [{league}] {t1} vs {t2}")

                    # Если нашли наш матч (Норильск/Югра) или любой другой во 2-м периоде
                    # В этом API статус периода часто идет в поле 'strStatus'
                    status = event.get('strStatus', '').upper()
                    
                    if "NORILSK" in t1.upper() or "YUGRA" in t2.upper() or "2ND" in status:
                        msg = (f"🏒 **LIVE СИГНАЛ**\n"
                               f"🏆 {league}\n"
                               f"🏒 {t1} vs {t2}\n"
                               f"⏱ Статус: {status if status else 'В игре'}")
                        await bot.send_message(CHANNEL_ID, msg)
                        logger.info(f"✅ Сигнал по {t1} отправлен!")

        except Exception as e:
            logger.error(f"Ошибка стабильного фида: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "✅ Бот перешел на стабильный мировой фид. Слежение 24/7 запущено!")
    while True:
        await check_hockey_stable()
        await asyncio.sleep(60) # Проверка раз в минуту

if __name__ == "__main__":
    asyncio.run(main())
