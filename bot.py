import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

# Используем "всеохватывающий" эндпоинт
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"

async def check_matches():
    # Имитируем запрос от официального приложения
    headers = {
        "User-Agent": "LiveScore/5.3.1 (iPhone; iOS 15.4.1)",
        "X-Requested-With": "com.livescore.app"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                data = await resp.json()
                found_vhl = False
                
                for stage in data.get('Stages', []):
                    # Проверяем, есть ли Россия в названии лиги
                    league_name = stage.get('Snm', '')
                    for event in stage.get('Events', []):
                        t1 = event['T1'][0]['Nm']
                        t2 = event['T2'][0]['Nm']
                        status = event.get('Eps', '') # Период
                        score1 = event.get('Tr1', '0')
                        score2 = event.get('Tr2', '0')
                        
                        # Печатаем вообще всё, что видим в лайве для теста
                        logger.info(f"ВИЖУ В ЛАЙВЕ: {t1} {score1}:{score2} {t2} ({status})")

                        # Если это наш Омск или любая ВХЛ
                        if "Omskie" in t1 or "Dinamo" in t2 or "VHL" in league_name:
                            found_vhl = True
                            logger.info(f"🎯 ЦЕЛЬ НАЙДЕНА: {t1} - {t2}")
                            # Тут логика отправки сигнала...

                if not found_vhl:
                    logger.info("ВХЛ сейчас нет в активной фазе API. Ждем обновлений.")

        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🚀 Бот на Railway перешел в режим глубокого сканирования!")
    while True:
        await check_matches()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
