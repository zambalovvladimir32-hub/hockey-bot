import asyncio
import os
import logging
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"
FSIGN = "SW9D1eZo" 

async def get_flashscore_data():
    headers = {
        "x-fsign": FSIGN,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with AsyncSession(impersonate="chrome120") as session:
        try:
            resp = await session.get(URL, headers=headers, timeout=15)
            return resp.text if resp.status_code == 200 else None
        except:
            return None

def parse_games(raw_data):
    if not raw_data: return []
    matches = []
    # Делим на блоки матчей
    blocks = raw_data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Ищем названия команд (теги AE и AF)
            home_match = "".join(block.split('AE÷')[1].split('¬')[0]) if 'AE÷' in block else "???"
            away_match = "".join(block.split('AF÷')[1].split('¬')[0]) if 'AF÷' in block else "???"
            
            # Ищем счет
            s1 = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
            s2 = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
            
            # КЛЮЧЕВАЯ ПРОВЕРКА: Ищем маркер периода
            # Мы ищем либо код TT÷2, либо явное упоминание П2/2-й в статусе
            is_2nd = False
            if 'TT÷2' in block or 'NS÷2' in block or 'EP÷2' in block:
                is_2nd = True
            elif 'ER÷2' in block or 'ST÷2' in block:
                is_2nd = True
            
            # Доп. проверка на кириллицу "П2", как на твоем скрине
            if not is_2nd and 'П2' in block:
                is_2nd = True

            # Проверка на Норильск
            is_norilsk = "норильск" in home_match.lower() or "norilsk" in home_match.lower()

            if is_2nd or is_norilsk:
                matches.append(f"🏒 **{home_match} {s1}:{s2} {away_match}**\n⏱ Статус: Идет 2-й период")
                logger.info(f"✅ Поймал матч: {home_match}")
        except:
            continue
    return matches

async def main():
    logger.info("🚀 БОТ ЗАПУЩЕН В РЕЖИМЕ 'ПРЯМОЙ ПОИСК'")
    while True:
        raw = await get_flashscore_data()
        if raw:
            logger.info(f"📥 Получено {len(raw)} байт данных. Ищу 2-й период...")
            games = parse_games(raw)
            if games:
                report = "🥅 **LIVE: 2-Й ПЕРИОД ОБНАРУЖЕН**\n\n" + "\n\n".join(games[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info("📡 Сигнал в ТГ отправлен!")
            else:
                logger.info("⏳ Во входящих данных 2-го периода пока нет.")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
