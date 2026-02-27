import asyncio
import aiohttp
import os
import logging
import sys
from google import genai
from aiogram import Bot

# Логи для Amvera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
client = genai.Client(api_key=GEMINI_KEY)

# НОВЫЙ URL (более стабильный для хоккея)
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0.00"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

sent_signals = set()

async def check_logic():
    logger.info("--- ЗАПУСК ПАРСИНГА (14:03 ЧИТА) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                data = await resp.json()
                events = data.get('Stages', [])
                
                total_games = 0
                for stage in events:
                    for event in stage.get('Events', []):
                        total_games += 1
                        t1 = event['T1'][0]['Nm']
                        t2 = event['T2'][0]['Nm']
                        
                        # ДЛЯ ТЕБЯ: Печатаем в логи все матчи, которые видим
                        logger.info(f"Вижу матч: {t1} - {t2} | Статус: {event.get('Eps')}")

                        # Логика фильтрации
                        period = event.get('Eps')
                        try:
                            m = int(event.get('Emm', 0))
                            s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))
                        except: continue

                        algo = None
                        if period == '1ST' and 12 <= m <= 18 and (s1+s2 <= 1):
                            algo = "ЗАСУХА 1-Й ПЕР"
                        elif period == '2ND' and 21 <= m <= 32:
                            algo = "ГОЛ ВО 2-М ПЕРИОДЕ"

                        if algo:
                            key = f"{event['Eid']}_{algo}"
                            if key not in sent_signals:
                                # Отправка в ТГ
                                msg = f"🚨 {algo}\n🏒 {t1} - {t2}\n📊 Счет: {s1}:{s2} ({m} мин)"
                                await bot.send_message(CHANNEL_ID, msg)
                                sent_signals.add(key)
                                logger.info(f"ОТПРАВЛЕНО: {t1}-{t2}")

                logger.info(f"ОБРАБОТАНО МАТЧЕЙ: {total_games}")
        except Exception as e:
            logger.error(f"ОШИБКА: {e}")

async def main():
    # Проверка связи при старте
    await bot.send_message(CHANNEL_ID, "✅ Бот обновлен. Время в Чите: 14:03. Начинаю поиск матчей...")
    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
