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
            return None
        except Exception as e:
            logger.error(f"🔥 Ошибка сети: {e}")
            return None

def parse_games(raw_data):
    if not raw_data: return []
    matches = []
    blocks = raw_data.split('~AA÷')
    
    # DEBUG: Выведем в лог кусочек данных первого матча, чтобы понять формат
    if len(blocks) > 1:
        logger.info(f"🔎 DEBUG (кусок данных): {blocks[1][:150]}")

    for block in blocks[1:]:
        try:
            # Превращаем блок в словарь для удобства
            res = dict(re.findall(r'(\w+)÷([^¬]+)', block))
            home = res.get('AE', '???')
            away = res.get('AF', '???')
            s1, s2 = res.get('AG', '0'), res.get('AH', '0')
            
            # Собираем ВЕСЬ текст блока в одну кучу для поиска периода
            full_block_text = block.upper()
            
            # Ищем любые намеки на 2-й период (TT=2, П2, P2, 2-Й)
            is_2nd = any(x in full_block_text for x in ["TT÷2", "П2", "P2", "2-Й", "2ND", "ER÷2"])
            is_target = "НОРИЛЬСК" in full_block_text or "NORILSK" in full_block_text

            if is_2nd or is_target:
                status = res.get('ER', res.get('ST', '2-й период'))
                msg = f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Статус: {status}"
                matches.append(msg)
                logger.info(f"✅ НАШЕЛ: {home} - {away} (Статус: {status})")
        except:
            continue
    return matches

async def main():
    logger.info("🚀 СКАНИРОВАНИЕ ЗАПУЩЕНО")
    while True:
        raw = await get_flashscore_data()
        if raw:
            games = parse_games(raw)
            if games:
                report = "🥅 **LIVE: ХОККЕЙ, 2-й ПЕРИОД**\n\n" + "\n\n".join(games[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info("📡 Отправил сигнал в ТГ!")
            else:
                logger.info("⏳ Матчи есть, но 2-й период не распознан. Ждем...")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
