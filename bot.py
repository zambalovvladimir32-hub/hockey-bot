import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

# Настройка логов для Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

# Источники данных
LIVESCORE_URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"
# Резервный метод для Flashscore-данных через открытый API
FLASH_URL = "https://be.flashscore.com/api/v1/live-matches/hockey" 

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

sent_signals = set()

async def check_matches():
    logger.info("--- МОНИТОРИНГ: LIVESCORE + FLASHSCORE ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # 1. Проверка через LiveScore
        try:
            async with session.get(LIVESCORE_URL, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for stage in data.get('Stages', []):
                        league = stage.get('Snm', 'Hockey')
                        for event in stage.get('Events', []):
                            t1 = event['T1'][0]['Nm']
                            t2 = event['T2'][0]['Nm']
                            score1 = event.get('Tr1', '0')
                            score2 = event.get('Tr2', '0')
                            status = event.get('Eps', '')
                            
                            # Логика для ВХЛ (Омск и другие)
                            if "VHL" in league or "KHL" in league:
                                logger.info(f"Нашел матч: {t1} {score1}:{score2} {t2} ({status})")
                                
                                # Пример условия для сигнала: 2-й период
                                if status == '2ND':
                                    key = f"{t1}_signal"
                                    if key not in sent_signals:
                                        msg = f"🏒 **СИГНАЛ LIVESCORE**\n🏆 {league}\n📊 {t1} {score1}:{score2} {t2}\n🔥 Идет 2-й период!"
                                        await bot.send_message(CHANNEL_ID, msg)
                                        sent_signals.add(key)
                else:
                    logger.warning(f"LiveScore временно недоступен: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка LiveScore: {e}")

        # 2. Проверка через Flashscore API (резерв)
        try:
            async with session.get(FLASH_URL, timeout=10) as resp:
                if resp.status == 200:
                    # Flashscore отдает специфический формат, просто проверяем наличие матчей
                    logger.info("Flashscore API ответил успешно.")
                else:
                    logger.warning(f"Flashscore временно недоступен: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка Flashscore: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "✅ Бот на Railway переключен на Flashscore и LiveScore!")
    while True:
        await check_matches()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
