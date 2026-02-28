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
                r = await s.get(f"{url}?t={int(asyncio.get_event_loop().time())}", headers=headers, proxies=proxies, timeout=15)
                if r.status_code == 200:
                    all_raw += r.text
            except Exception as e:
                logger.error(f"⚠️ Ошибка запроса: {e}")
    return all_raw

def parse(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        league_name = section.split('¬')[0]
        blocks = section.split('~AA÷')
        for block in blocks[1:]:
            try:
                if 'AG÷' not in block: continue
                
                # Статусы: AB=3 (Live), JS (детальный статус)
                js_status = block.split('JS÷')[1].split('¬')[0] if 'JS÷' in block else ""
                
                # Ищем признаки 2-го периода или перерыва перед ним
                # 2 - идет 2-й период
                # 6 - перерыв
                # Также проверяем наличие счета за 1-й период (XA÷), но отсутствие за 2-й (XB÷)
                is_second = (js_status == '2')
                is_break = (js_status == '6')
                
                # Если перерыв, проверяем, что это именно после 1-го периода
                # Обычно после 1-го периода появляется блок XA÷ (счет 1-го периода)
                has_1st_period_score = 'XA÷' in block
                has_2nd_period_score = 'XB÷' in block
                
                if is_second or (is_break and has_1st_period_score and not has_2nd_period_score):
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0]
                    s_a = block.split('AH÷')[1].split('¬')[0]
                    
                    status_text = "⏱ 2-й ПЕРИОД" if is_second else "☕️ ПЕРЕРЫВ (после 1-го)"
                    
                    matches.append({
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league_name}\n{status_text}",
                        'id': f"{home}{away}{s_h}{s_a}{js_status}"
                    })
                elif js_status:
                    # Лог для отладки, если матч в лайве, но не подошел под условия
                    logger.debug(f"Пропущен матч: {js_status} | 1st Score: {has_1st_period_score}")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 ОБНОВЛЕННЫЙ СКАНЕР ЗАПУЩЕН")
    last_sent = {}

    while True:
        raw_data = await get_combined_data()
        if raw_data:
            found = parse(raw_data)
            logger.info(f"🔎 Найдено подходящих игр (2-й пер/Перерыв): {len(found)}")
            
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
                logger.info(f"📣 Отправлено сообщений: {len(to_send)}")
        
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
