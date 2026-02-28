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
                
                # 1. Проверяем JS статус (2 - период, 6 - перерыв)
                js_status = block.split('JS÷')[1].split('¬')[0] if 'JS÷' in block else ""
                
                # 2. Проверяем поле времени (ТТ). Там часто пишут "2nd period" или "P2"
                time_text = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else ""
                
                # 3. Проверяем наличие счета за 1-й и 2-й периоды
                has_1st = 'XA÷' in block
                has_2nd = 'XB÷' in block

                # УСЛОВИЕ ЛОВУШКИ:
                # - Если JS равен '2' ИЛИ в тексте времени есть '2'
                # - ИЛИ если это перерыв ('6') и уже есть счет 1-го периода, но нет 2-го
                is_second_period = (js_status == '2' or '2' in time_text)
                is_break_after_1st = (js_status == '6' and has_1st and not has_2nd)

                if is_second_period or is_break_after_1st:
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0]
                    s_a = block.split('AH÷')[1].split('¬')[0]
                    
                    # Формируем статус для сообщения
                    status = "⏱ 2-й ПЕРИОД"
                    if is_break_after_1st: status = "☕️ ПЕРЕРЫВ (после 1-го)"
                    if time_text: status += f" ({time_text})"

                    matches.append({
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league_name}\n{status}",
                        'id': f"{home}{away}{s_h}{s_a}" 
                    })
            except:
                continue
    return matches

async def main():
    logger.info("🎯 СУПЕР-СКАНЕР 2-ГО ПЕРИОДА ЗАПУЩЕН")
    last_sent = {}

    while True:
        raw_data = await get_combined_data()
        if raw_data:
            found = parse(raw_data)
            logger.info(f"🔎 Найдено подходящих игр: {len(found)}")
            
            for m in found:
                m_id = m['id']
                if m_id not in last_sent:
                    await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                    last_sent[m_id] = m['text']
                    logger.info(f"✅ Отправлен матч: {m_id}")
        
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(45) # Чуть быстрее опрашиваем

if __name__ == "__main__":
    asyncio.run(main())
