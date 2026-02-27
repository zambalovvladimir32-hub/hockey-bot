import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

# Настройка логирования для Railway (чтобы всё было видно в консоли)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"

# Чтобы не спамить об одном и том же матче по 100 раз
sent_signals = set()

async def check_matches():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4_1 like Mac OS X)",
        "X-Requested-With": "com.livescore.app"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка доступа к API: {resp.status}")
                    return

                data = await resp.json()
                found_any = 0
                
                # Проходим по всем лигам и матчам
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'Хоккей')
                    for event in stage.get('Events', []):
                        found_any += 1
                        t1 = event['T1'][0]['Nm']
                        t2 = event['T2'][0]['Nm']
                        status = event.get('Eps', 'LIVE') # Текущий период (1ST, 2ND, 3RD)
                        s1 = event.get('Tr1', '0') # Голы хозяев
                        s2 = event.get('Tr2', '0') # Голы гостей
                        
                        # Создаем уникальный ключ для уведомления (команды + период)
                        # Это нужно, чтобы при изменении счета или периода бот мог прислать апдейт
                        match_key = f"{t1}_{t2}_{status}_{s1}_{s2}"
                        
                        if match_key not in sent_signals:
                            # 1. Условие твоей стратегии (2-й период)
                            if status == '2ND':
                                msg = (f"🔥 **СТРАТЕГИЯ: 2-й ПЕРИОД**\n"
                                       f"🏆 {league}\n"
                                       f"🏒 {t1} {s1}:{s2} {t2}\n"
                                       f"📢 Пора делать анализ!")
                            
                            # 2. Просто уведомление о начале или ходе игры
                            else:
                                msg = (f"🏒 **LIVE ОБНОВЛЕНИЕ**\n"
                                       f"🏆 {league}\n"
                                       f"📊 {t1} {s1}:{s2} {t2}\n"
                                       f"⏱ Статус: {status}")

                            await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                            sent_signals.add(match_key)
                            logger.info(f"Отправлен сигнал: {t1}-{t2} ({status})")

                if found_any == 0:
                    logger.info("На линии затишье. Масштабный поиск продолжается...")
                else:
                    logger.info(f"В работе матчей: {found_any}")

        except Exception as e:
            logger.error(f"Ошибка в цикле: {e}")

async def main():
    logger.info("Бот заступил на дежурство.")
    # Опционально: уведомление в телегу, что бот готов
    # await bot.send_message(CHANNEL_ID, "✅ Бот на связи. Жду начала вечерних матчей!")
    
    while True:
        await check_matches()
        # Проверяем раз в минуту, чтобы не забанили за слишком частые запросы
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
