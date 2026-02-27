import asyncio
import aiohttp
import os
import logging
import sys
import random
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

# Мобильный шлюз, который сложнее заблокировать
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"

async def check_matches():
    # Генерируем заголовки обычного iPhone, чтобы сервер не догадался, что это бот
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1",
        "X-Requested-With": "com.livescore.app",
        "Accept": "*/*"
    }
    
    logger.info("--- ПОПЫТКА ПРОРЫВА (MOBILE GATEWAY) ---")
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            # Добавляем случайный параметр, чтобы обойти кэширование блокировки
            async with session.get(f"{URL}?random={random.randint(1,1000)}", timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Сервер сбросил соединение. Код: {resp.status}")
                    return
                
                data = await resp.json()
                matches_found = 0
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'Hockey')
                    for event in stage.get('Events', []):
                        matches_found += 1
                        t1 = event['T1'][0]['Nm']
                        t2 = event['T2'][0]['Nm']
                        score1 = event.get('Tr1', '0')
                        score2 = event.get('Tr2', '0')
                        status = event.get('Eps', '') # Период
                        minute = event.get('Emm', '0') # Минута
                        
                        logger.info(f"ВИЖУ: {t1} - {t2} | {score1}:{score2} | {status} {minute}'")

                        # Логика сигнала для 2-го периода (21-35 мин)
                        if status == '2ND' and 21 <= int(minute or 0) <= 35:
                            # Тут будет твой ИИ и отправка сообщения
                            pass

                logger.info(f"УСПЕХ! В лайве обнаружено {matches_found} матчей.")
                if matches_found == 0:
                    logger.warning("Список пуст, но сервер ответил. Ждем начала игр.")

        except Exception as e:
            logger.error(f"Критическая ошибка доступа: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🛡 Запущен мобильный протокол обхода блокировок...")
    while True:
        await check_matches()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
