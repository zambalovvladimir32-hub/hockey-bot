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

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"

async def diagnostic_check():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X)",
        "X-Requested-With": "com.livescore.app"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            logger.info("--- ЗАПУСК ДИАГНОСТИКИ ЛИНИИ ---")
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Ошибка доступа! Статус: {resp.status}")
                    return

                data = await resp.json()
                stages = data.get('Stages', [])
                
                if not stages:
                    logger.warning("⚠️ API прислал пустой список лиг. Матчей в лайве сейчас нет?")
                    return

                found_count = 0
                for stage in stages:
                    league_name = stage.get('Snm', 'Неизвестная лига')
                    for event in stage.get('Events', []):
                        found_count += 1
                        t1 = event['T1'][0]['Nm']
                        t2 = event['T2'][0]['Nm']
                        status = event.get('Eps', '???')
                        score = f"{event.get('Tr1', '0')}:{event.get('Tr2', '0')}"
                        
                        # Печатаем КАЖДЫЙ найденный матч в логи Railway
                        logger.info(f"✅ ВИЖУ: [{league_name}] {t1} {score} {t2} (Статус: {status})")

                logger.info(f"--- ДИАГНОСТИКА ЗАВЕРШЕНА. ВСЕГО МАТЧЕЙ: {found_count} ---")
                
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")

async def main():
    # Отправим в канал сообщение, чтобы знать, что бот обновился
    await bot.send_message(CHANNEL_ID, "🔍 Запущена полная диагностика линии. Проверяю логи...")
    while True:
        await diagnostic_check()
        await asyncio.sleep(30) # Проверка каждые 30 секунд для теста

if __name__ == "__main__":
    asyncio.run(main())
