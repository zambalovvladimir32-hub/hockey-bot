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

def parse_brute(data):
    matches = []
    for section in data.split('~ZA÷')[1:]:
        league = section.split('¬')[0]
        for block in section.split('~AA÷')[1:]:
            try:
                # Берем только Лайв (AB=3)
                if 'AB÷3' not in block: continue
                
                # Вытаскиваем все поля статуса для отладки
                js = block.split('JS÷')[1].split('¬')[0] if 'JS÷' in block else "?"
                tt = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else "?"
                
                # Печатаем в лог всё, что видим по живым играм (чтобы найти П2)
                logger.info(f"DEBUG LIVE: {block[:80]} | JS:{js} | TT:{tt}")

                # Условие: если в статусе есть 2, P2, П2 или код JS=2/6
                is_target = any(x in tt.upper() for x in ['2', 'П2', 'P2']) or js in ['2', '6']
                
                if is_target:
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    matches.append({
                        'id': f"{home}{away}{s_h}{s_a}",
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n⏱ Статус: {tt} (JS:{js})"
                    })
            except:
                continue
    return matches

async def main():
    logger.info("🛠 ЗАПУСК КУВАЛДЫ (БРУТФОРС ПЕРИОДОВ)")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_brute(raw)
            logger.info(f"🔎 Найдено в Лайве: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                    except: pass
        
        if len(last_sent) > 300: last_sent.clear()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
