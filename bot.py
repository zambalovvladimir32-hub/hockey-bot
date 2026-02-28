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
                ts = int(asyncio.get_event_loop().time())
                r = await s.get(f"{url}?t={ts}", headers=headers, proxies=proxies, timeout=15)
                if r.status_code == 200:
                    combined += r.text
            except Exception as e:
                logger.error(f"Ошибка сети: {e}")
    return combined

def parse_strict(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        league = section.split('¬')[0]
        blocks = section.split('~AA÷')
        
        for block in blocks[1:]:
            try:
                if 'AB÷' not in block: continue
                
                # 1. Извлекаем данные
                ab = block.split('AB÷')[1].split('¬')[0] # Статус Live
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else "" # Код периода
                tt = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else "" # Время (текст)
                has_1st_period_score = 'XA÷' in block # ЕСТЬ СЧЕТ 1-ГО ПЕРИОДА
                has_2nd_period_score = 'XB÷' in block # ЕСТЬ СЧЕТ 2-ГО ПЕРИОДА (значит он уже кончился)

                # 2. ФИЛЬТР-ОТСЕКАТЕЛЬ:
                # Нам НЕ нужны матчи, где:
                # - Идет 1-й период (в тексте времени есть "1")
                # - 2-й период уже завершен (есть блок XB)
                if '1' in tt or 'P1' in tt.upper() or has_2nd_period_score:
                    continue

                # 3. УСЛОВИЕ ЛОВЛИ (только перерыв 1-2 или сам 2-й период):
                # Должен быть ОБЯЗАТЕЛЬНО счет за 1-й период (XA)
                # И статус должен быть либо Перерыв (AC:45), либо 2-й период (AC:2 или текст "2")
                
                is_break = (ac == '45' or 'ПЕРЕРЫВ' in tt.upper())
                is_second = (ac == '2' or '2' in tt or 'П2' in tt.upper())

                if has_1st_period_score and (is_break or is_second):
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    status_label = "☕️ ПЕРЕРЫВ (1-2)" if is_break else "⏱ 2-Й ПЕРИОД"
                    if tt and tt != "?": status_label += f" [{tt}]"

                    matches.append({
                        'id': f"{home}{away}{s_h}{s_a}{is_break}", 
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status_label}"
                    })
            except:
                continue
    return matches

async def main():
    logger.info("🎯 СТРОГИЙ СКАНЕР ЗАПУЩЕН (Только после 1-го периода)")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_strict(raw)
            logger.info(f"🔎 Найдено подходящих игр: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                    except Exception as e:
                        logger.error(f"Ошибка ТГ: {e}")
        
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
