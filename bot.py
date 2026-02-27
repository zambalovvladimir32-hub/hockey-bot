import asyncio
import os
import logging
import re
from aiogram import Bot
# Используем магическую библиотеку для обхода блокировок
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Тот самый фид Flashscore
URL = "https://d.flashscore.com/x/feed/f_4_0_2_ru-ru_1"
FSIGN = "SW9D1eZo"

async def get_flashscore():
    headers = {
        "x-fsign": FSIGN,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.com/"
    }
    
    # impersonate="chrome120" — это та самая кнопка "Сделать заебись".
    # Она полностью копирует поведение браузера Chrome, обходя Cloudflare.
    async with AsyncSession(impersonate="chrome120") as session:
        try:
            resp = await session.get(URL, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.text
            else:
                logger.error(f"🚫 Ошибка сервера: {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"🔥 Ошибка сети: {e}")
            return None

def parse_games(raw_data):
    if not raw_data: return []
    matches = []
    blocks = raw_data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Вытягиваем данные с помощью регулярок
            res = dict(re.findall(r'(\w+)÷([^¬]+)', block))
            
            home = res.get('AE', '???')
            away = res.get('AF', '???')
            s1 = res.get('AG', '0')
            s2 = res.get('AH', '0')
            status = res.get('ER', 'LIVE')
            
            # Фильтр: 2-й период или команда Норильск
            if "2" in status or "норильск" in home.lower():
                matches.append(f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Период: {status}")
        except:
            continue
    return matches

async def main():
    logger.info("🚀 Бот запущен в режиме АНТИ-ДЕТЕКТ (обходим защиты бесплатно)")
    await bot.send_message(CHANNEL_ID, "✅ Система слежения запущена. Обход блокировок активирован.")
    
    while True:
        raw = await get_flashscore()
        if raw:
            games = parse_games(raw)
            if games:
                report = "🎯 **СИГНАЛ ПО СТРАТЕГИИ:**\n\n" + "\n\n".join(games[:15])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"✅ Отправлено {len(games)} матчей")
            else:
                logger.info("Матчи идут, но 2-й период еще не наступил.")
        
        # Ждем 60 секунд
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
