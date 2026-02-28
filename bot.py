import asyncio
import os
import logging
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)

URLS = [
    "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1",
    "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"
]

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
    }
    combined = ""
    async with AsyncSession(impersonate="chrome110") as s:
        proxies = {"http": PROXY, "https": PROXY} if PROXY else None
        for url in URLS:
            try:
                r = await s.get(f"{url}?t={int(asyncio.get_event_loop().time())}", headers=headers, proxies=proxies, timeout=15)
                if r.status_code == 200:
                    combined += r.text
            except Exception as e:
                logger.error(f"Ошибка сети: {e}")
    return combined

def parse_spy(data):
    matches = []
    for block in data.split('~AA÷')[1:]:
        try:
            # Ищем наш "невидимый" матч по названию команд
            if "Tohoku" in block or "Kobe" in block or "Коби" in block:
                # ВЫВОДИМ В ЛОГ ВСЁ "ДНК" МАТЧА
                logger.info(f"🎯 МАТЧ НАЙДЕН! Сырые данные: {block[:150]}")
            
            # Пытаемся поймать его расширенным фильтром
            # Проверяем все возможные коды лайва (3) и периодов
            ab = block.split('AB÷')[1].split('¬')[0] if 'AB÷' in block else ""
            ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else ""
            
            # Если это лайв и хоть какой-то намек на 2-й период или перерыв
            if ab == '3' and ac in ['2', '45', '6', '12', '13', '14']:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                
                matches.append({
                    'id': f"{home}{away}{ac}",
                    'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Код периода (AC): {ac}"
                })
        except: continue
    return matches

async def main():
    logger.info("🕵️‍♂️ ЗАПУЩЕН РЕЖИМ ШПИОНА")
    while True:
        raw = await get_data()
        if raw:
            found = parse_spy(raw)
            for m in found:
                try:
                    await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                    logger.info(f"✅ Улетело в канал: {m['text']}")
                except: pass
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
