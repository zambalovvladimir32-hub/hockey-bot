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

# Используем оба фида для максимального охвата
URLS = [
    "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1",
    "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"
]

async def get_combined_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
    }
    all_raw = ""
    async with AsyncSession(impersonate="chrome110") as s:
        proxies = {"http": PROXY, "https": PROXY} if PROXY else None
        for url in URLS:
            try:
                ts_url = f"{url}?t={int(asyncio.get_event_loop().time())}"
                r = await s.get(ts_url, headers=headers, proxies=proxies, timeout=15)
                if r.status_code == 200:
                    all_raw += r.text
            except Exception as e:
                logger.error(f"⚠️ Ошибка запроса: {e}")
    return all_raw

def parse(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        try:
            league_name = section.split('¬')[0]
            blocks = section.split('~AA÷')
            for block in blocks[1:]:
                if 'AG÷' not in block: continue
                
                # Читаем код статуса JS
                status_code = block.split('JS÷')[1].split('¬')[0] if 'JS÷' in block else '0'
                
                # УСЛОВИЕ: 
                # Код '6' = Перерыв (обычно после 1-го или 2-го)
                # Код '2' = Идет 2-й период
                is_break = status_code == '6'
                is_second_period = status_code == '2'
                
                # Дополнительная проверка: если перерыв, то после какого периода?
                # Flashscore иногда пишет номер периода в поле 'LP' или 'TT'
                period_num = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else ""
                
                # Нам нужны только те, где:
                # 1. Либо явно 2-й период (JS:2)
                # 2. Либо перерыв (JS:6), но мы видим, что 1-й период уже закончен
                if is_second_period or (is_break and ("1" in period_num or "2" not in period_num)):
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0]
                    s_a = block.split('AH÷')[1].split('¬')[0]
                    
                    status_text = "⏱ 2-й ПЕРИОД" if is_second_period else "☕️ ПЕРЕРЫВ (после 1-го)"
                    
                    matches.append({
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league_name}\n{status_text}",
                        'id': f"{home}{away}{status_code}{s_h}{s_a}" 
                    })
        except:
            continue
    return matches

async def main():
    logger.info("📡 СКАНЕР (ПЕРЕРЫВ + 2-Й ПЕРИОД) ЗАПУЩЕН")
    last_sent = {}

    while True:
        raw_data = await get_combined_data()
        if raw_data:
            found = parse(raw_data)
            logger.info(f"🔎 Найдено подходящих игр: {len(found)}")
            
            to_send = []
            for m in found:
                m_id = m['id']
                if m_id not in last_sent:
                    to_send.append(m['text'])
                    last_sent[m_id] = m['text']
            
            if to_send:
                for i in range(0, len(to_send), 5):
                    chunk = to_send[i:i+5]
                    msg = "🥅 **LIVE: ПЕРЕРЫВ / 2-Й ПЕРИОД**\n\n" + "\n\n".join(chunk)
                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
            
        # Чистим память раз в 3 часа
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
