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

def parse_strict_second(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        league = section.split('¬')[0]
        blocks = section.split('~AA÷')
        
        for block in blocks[1:]:
            try:
                if 'AB÷' not in block: continue
                
                # Системные коды Flashscore
                ab = block.split('AB÷')[1].split('¬')[0]  # Статус (LIVE/Ожидание)
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else "" # Подстатус
                cr = block.split('CR÷')[1].split('¬')[0] if 'CR÷' in block else "" # Текущий период
                tt = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else "" # Текст времени (напр. 25')

                # 1. Берем только те, что в эфире
                if ab not in ['2', '3']: continue

                # 2. ЖЕСТКИЙ ФИЛЬТР ПЕРИОДОВ
                # Если видим коды 1-го или 3-го периода — сразу пропускаем.
                # AC 1=1й пер, 3=3й пер, 46=перерыв перед 3-м.
                # CR 1=1й пер, 3=3й пер.
                if ac in ['1', '3', '46', '4', '5'] or cr in ['1', '3']:
                    continue

                # 3. ПРОВЕРКА НА 2-Й ПЕРИОД
                # AC 45 — это всегда перерыв между 1 и 2 периодом.
                # AC 2 или CR 2 — это всегда 2-й период.
                # AC 15 — специфический код для Азиатских лиг (2-й период).
                is_break = (ac == '45')
                is_second_period = (ac in ['2', '15'] or cr == '2')

                if is_break or is_second_period:
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    status = "☕️ ПЕРЕРЫВ (1-2)" if is_break else "⏱ 2-Й ПЕРИОД"
                    if tt and tt != "?": status += f" [{tt}]"

                    matches.append({
                        'id': f"{home}{away}{s_h}{s_a}{is_break}",
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status}"
                    })
            except:
                continue
    return matches

async def main():
    logger.info("🎯 СКАНЕР 'ТОЛЬКО 2-Й ПЕРИОД' ВКЛЮЧЕН")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_strict_second(raw)
            logger.info(f"🔎 В эфире 2-го периода: {len(found)} матчей")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                    except: pass
        
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
