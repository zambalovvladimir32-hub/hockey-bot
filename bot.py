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

def parse_ultra(data):
    matches = []
    sections = data.split('~ZA÷')
    for section in sections[1:]:
        league = section.split('¬')[0]
        blocks = section.split('~AA÷')
        for block in blocks[1:]:
            try:
                # AB: 2 или 3 — это живой матч (теперь ловим и Азию)
                ab = block.split('AB÷')[1].split('¬')[0] if 'AB÷' in block else ""
                if ab not in ['2', '3']: continue

                # CR: 2 — это железно Второй период
                # AC: 45 — это Перерыв после 1-го
                cr = block.split('CR÷')[1].split('¬')[0] if 'CR÷' in block else ""
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else ""
                
                if cr == '2' or ac == '45':
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    status = "☕️ ПЕРЕРЫВ (1-2)" if ac == '45' else "⏱ 2-Й ПЕРИОД"
                    
                    matches.append({
                        'id': f"{home}{away}{ac}{cr}",
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status}"
                    })
            except: continue
    return matches

async def main():
    logger.info("🚀 ULTRA-DETECTOR ЗАПУЩЕН. Охота на CR:2 и AB:2/3")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_ultra(raw)
            logger.info(f"🔎 Найдено в эфире: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                        logger.info(f"✅ Отправлено: {m['text'][:30]}...")
                    except: pass
        
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
