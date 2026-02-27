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

# Мы будем опрашивать сразу два фида для максимального охвата
URLS = [
    "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", # Общий фид
    "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"  # Топ-лиги
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
                logger.error(f"⚠️ Ошибка запроса к {url}: {e}")
    return all_raw

def parse(data):
    matches = []
    # Сначала найдем лиги (они начинаются с ~ZA÷)
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        try:
            league_name = section.split('¬')[0]
            # Внутри секции лиги ищем матчи (~AA÷)
            blocks = section.split('~AA÷')
            for block in blocks[1:]:
                if 'AG÷' not in block: continue # Пропускаем неначатые
                
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                s_h = block.split('AG÷')[1].split('¬')[0]
                s_a = block.split('AH÷')[1].split('¬')[0]
                
                status = "LIVE"
                if 'JS÷' in block:
                    val = block.split('JS÷')[1].split('¬')[0]
                    status_map = {'1':'1-й','2':'2-й','3':'3-й','6':'Пауза','10':'ОТ','11':'Бул.'}
                    status = status_map.get(val, "LIVE")

                matches.append({
                    'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league_name} | ⏱ {status}",
                    'id': f"{home}{away}{s_h}{s_a}" # Ключ для отслеживания изменений
                })
        except:
            continue
    return matches

async def main():
    logger.info("📡 ЗАПУСК МАКСИМАЛЬНОГО СКАНЕРА")
    last_sent = {} # Храним ID матча и его последнее состояние

    while True:
        raw_data = await get_combined_data()
        if raw_data:
            found = parse(raw_data)
            logger.info(f"🔎 Всего в системе: {len(found)} активных игр")
            
            to_send = []
            for m in found:
                m_id = m['id']
                # Если матч новый или счет изменился
                if m_id not in last_sent:
                    to_send.append(m['text'])
                    last_sent[m_id] = m['text']
            
            if to_send:
                for i in range(0, len(to_send), 8):
                    chunk = to_send[i:i+8]
                    msg = "🥅 **LIVE ОБНОВЛЕНИЯ:**\n\n" + "\n\n".join(chunk)
                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                logger.info(f"📣 Дослано {len(to_send)} новых событий")
        
        # Чистим память (оставляем только последние 200 игр)
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
