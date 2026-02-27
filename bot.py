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
PROXY = os.getenv("PROXY_URL") # Формат: socks5://user:pass@ip:port

bot = Bot(token=TOKEN)
URL = "https://www.flashscore.ru/x/feed/f_4_1_2_ru-ru_1"

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
    }
    
    # Пытаемся сначала с прокси, если он задан
    modes = [("Proxy", PROXY)] if PROXY else []
    modes.append(("Direct", None)) # Прямое подключение как запасной вариант

    for name, p_url in modes:
        try:
            async with AsyncSession(impersonate="chrome110") as s:
                proxies = {"http": p_url, "https": p_url} if p_url else None
                r = await s.get(URL, headers=headers, proxies=proxies, timeout=20)
                if r.status_code == 200 and len(r.text) > 1000:
                    logger.info(f"✅ Успех через {name}! Размер: {len(r.text)} байт")
                    return r.text
        except Exception as e:
            logger.error(f"❌ Ошибка в режиме {name}: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    found_codes = set()
    
    for block in blocks[1:]:
        # Вытаскиваем статусы для отладки
        status_part = block.split('AB÷')[1].split('¬')[0] if 'AB÷' in block else '?'
        period_part = block.split('JS÷')[1].split('¬')[0] if 'JS÷' in block else '?'
        found_codes.add(f"AB:{status_part}|JS:{period_part}")

        # Условие: Live (AB:3) + 2-й период (JS:2 или TT:2)
        is_live = 'AB÷3' in block
        is_2nd = any(x in block for x in ['JS÷2', 'TT÷2', 'NS÷2'])
        
        if is_live and is_2nd:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ 2-й период")
            except: continue
            
    if not matches:
        logger.info(f"🔎 Живых игр во 2-м периоде нет. Коды в сети: {list(found_codes)[:5]}")
    return matches

async def main():
    logger.info("🚀 БОТ ЗАПУЩЕН И ГОТОВ К ОХОТЕ")
    while True:
        raw_data = await get_data()
        if raw_data:
            found = parse(raw_data)
            if found:
                text = "🥅 **LIVE: 2-Й ПЕРИОД**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"📣 Отправлено {len(found)} матчей")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
