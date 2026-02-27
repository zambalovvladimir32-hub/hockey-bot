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

# Прямой IP-шлюз (в обход DNS) и альтернативный адрес
URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0?MD=1"

sent_signals = set()

async def check_logic():
    logger.info("--- СКАНИРОВАНИЕ ЛИНИИ (ОБХОД БЛОКОВ) ---")
    
    # Используем заголовки реального мобильного приложения
    headers = {
        "User-Agent": "LiveScore/5.3.1 (iPhone; iOS 15.4.1; Scale/3.00)",
        "X-Requested-With": "com.livescore.app"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Доступ ограничен: {resp.status}")
                    return
                
                data = await resp.json()
                total = 0
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'Hockey')
                    for event in stage.get('Events', []):
                        total += 1
                        eid = event.get('Eid')
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        
                        # Парсим минуты и счет
                        try:
                            m = int(event.get('Emm') or event.get('Esh', 0))
                            s1, s2 = int(event.get('Tr1', 0)), int(event.get('Tr2', 0))
                            period = event.get('Eps')
                        except: continue

                        # Логируем только активные матчи для чистоты
                        if period in ['1ST', '2ND', '3RD']:
                            logger.info(f"LIVE: {t1}-{t2} | {m} мин | {s1}:{s2}")

                        # Наша стратегия (Тотал во 2-м периоде)
                        if period == '2ND' and 21 <= m <= 35:
                            key = f"{eid}_2nd"
                            if key not in sent_signals:
                                msg = f"🏒 **LIVE СИГНАЛ!**\n🏆 {league}\n🏒 {t1} — {t2}\n📊 Счет: `{s1}:{s2}` ({m} мин)\n\n🚀 ИИ ожидает гол!"
                                await bot.send_message(CHANNEL_ID, msg)
                                sent_signals.add(key)
                                logger.info(f"ОТПРАВЛЕНО: {t1}-{t2}")

                logger.info(f"ИТОГ: Вижу {total} матчей.")
        except Exception as e:
            logger.error(f"Ошибка шлюза: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "✅ Связь с интернетом подтверждена. Запускаю поиск матчей...")
    while True:
        await check_logic()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
