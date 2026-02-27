import asyncio
import aiohttp
import os
import logging
import sys
import re
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

# Прямой фид данных Flashscore (этот узел обычно открыт)
URL = "https://d.flashscore.com/x/feed/l_3_1" 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "X-Referer": "https://www.flashscore.com/",
    "X-Requested-With": "XMLHttpRequest"
}

sent_signals = set()

async def check_logic():
    logger.info("--- ШТУРМ FLASHSCORE (ПРЯМОЙ ФИД) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=20) as resp:
                if resp.status != 200:
                    logger.error(f"Flashscore недоступен: {resp.status}")
                    return
                
                content = await resp.text()
                # Данные Flashscore идут через разделители ~, делим их на матчи
                raw_events = content.split('~')
                total = 0
                
                for event in raw_events:
                    # Ищем признаки хоккейного матча в Live
                    if 'AA÷' in event:
                        total += 1
                        # Извлекаем названия команд
                        t1 = re.search(r'AE÷([^¬]+)', event)
                        t2 = re.search(r'AF÷([^¬]+)', event)
                        # Извлекаем счет
                        s1 = re.search(r'AG÷([^¬]+)', event)
                        s2 = re.search(r'AH÷([^¬]+)', event)
                        # Извлекаем период и время
                        period_raw = re.search(r'EP÷([^¬]+)', event)
                        time_raw = re.search(r'ER÷([^¬]+)', event) # Минута

                        if t1 and t2:
                            team1, team2 = t1.group(1), t2.group(1)
                            score1 = s1.group(1) if s1 else "0"
                            score2 = s2.group(1) if s2 else "0"
                            period = period_raw.group(1) if period_raw else "?"
                            
                            logger.info(f"НАЙДЕНО: {team1} - {team2} | {score1}:{score2} | {period}")

                            # Проверка на Омск для подтверждения связи
                            if "Omskie" in team1 or "Omsk" in team1:
                                key = f"omsk_{score1}_{score2}"
                                if key not in sent_signals:
                                    await bot.send_message(CHANNEL_ID, f"🏒 **МАТЧ НАЙДЕН!**\n{team1} {score1}:{score2} {team2}\nСтатус: {period}")
                                    sent_signals.add(key)

                logger.info(f"ИТОГ: Flashscore отдал {total} активных игр.")
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🚀 Переход на Flashscore завершен. Проверяю Омск...")
    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
