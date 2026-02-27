import asyncio
import os
import logging
import re
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
            if resp.status_code == 200:
                return resp.text
            else:
                logger.error(f"🚫 Ошибка доступа: {resp.status_code}")
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
            res = dict(re.findall(r'(\w+)÷([^¬]+)', block))
            home = res.get('AE', '???')
            away = res.get('AF', '???')
            s1, s2 = res.get('AG', '0'), res.get('AH', '0')
            
            # ВНИМАНИЕ: Flashscore в сырых данных использует TT для номера периода
            # Если TT=2 — это 100% второй период
            period_code = res.get('TT', '') 
            status_text = (res.get('ER', '') + res.get('ST', '')).upper()
            
            # ПРОВЕРКА: Либо код периода = 2, либо в тексте есть маркеры
            is_2nd = (period_code == "2") or any(x in status_text for x in ["2", "P2", "П2", "2ND", "ВТОР"])
            is_target = "норильск" in home.lower() or "norilsk" in home.lower()

            if is_2nd or is_target:
                msg = f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Статус: 2-й период (код {period_code})"
                matches.append(msg)
                logger.info(f"✅ НАЙДЕН МАТЧ: {home} - {away} (TT={period_code}, ST={status_text})")
        except:
            continue
    return matches

async def main():
    logger.info("🚀 СИСТЕМА ОБНАРУЖЕНИЯ АКТИВИРОВАНА")
    while True:
        raw = await get_flashscore_data()
        if raw:
            logger.info("📥 Данные получены, анализирую...")
            games = parse_games(raw)
            if games:
                report = "🥅 **LIVE: ХОККЕЙ, 2-й ПЕРИОД**\n\n" + "\n\n".join(games[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info("📡 Сигнал отправлен в Telegram!")
            else:
                logger.info("⏸ Матчи идут, но 2-й период в кодах (TT=2) пока не найден.")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
