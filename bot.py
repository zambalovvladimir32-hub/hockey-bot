import asyncio
import os
import logging
import aiohttp
from aiogram import Bot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Мобильный фид (обычно работает без x-fsign)
URL = "https://d.flashscore.com/x/feed/f_4_1_2_ru-ru_1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "X-Referer": "https://www.flashscore.ru/",
    "X-Requested-With": "XMLHttpRequest"
}

async def fetch_hockey():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            # Пытаемся пробиться напрямую
            async with session.get(URL, timeout=15) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return text
                else:
                    logger.error(f"Ошибка доступа: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Сбой сети: {e}")
            return None

def extract_games(raw_data):
    """Парсим игры по упрощенной схеме"""
    if not raw_data: return []
    
    matches = []
    # Каждая игра начинается с идентификатора AA÷
    blocks = raw_data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # AE - Команда 1, AF - Команда 2, AG - Счет 1, AH - Счет 2, ER - Статус
            # Используем поиск подстрок, так как это быстрее и надежнее
            def get_val(key):
                start = block.find(f"{key}÷")
                if start == -1: return ""
                end = block.find("¬", start)
                return block[start + len(key) + 1 : end]

            t1, t2 = get_val("AE"), get_val("AF")
            s1, s2 = get_val("AG") or "0", get_val("AH") or "0"
            status = get_val("ER") # Например: "2-й период"

            # Нам нужен 2-й период или наш Норильск
            if "2" in status or "норильск" in t1.lower():
                matches.append(f"🏒 **{t1} {s1}:{s2} {t2}**\n⏱ {status}")
        except:
            continue
    return matches

async def main():
    logger.info("📡 Бесплатный мониторинг запущен...")
    while True:
        raw = await fetch_hockey()
        if raw:
            games = extract_games(raw)
            if games:
                report = "🥅 **LIVE ХОККЕЙ:**\n\n" + "\n\n".join(games[:15])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"✅ Отправлено {len(games)} матчей")
            else:
                logger.info("Подходящих матчей нет.")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
