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

def parse_smart(data):
    matches = []
    # Делим на лиги, потом на матчи
    for section in data.split('~ZA÷')[1:]:
        league = section.split('¬')[0]
        for block in section.split('~AA÷')[1:]:
            try:
                # Базовые данные
                if 'AE÷' not in block or 'AF÷' not in block: continue
                
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                
                # Статус матча (AB) и Детальный статус (JS/TT)
                status_main = block.split('AB÷')[1].split('¬')[0] if 'AB÷' in block else ""
                js_status = block.split('JS÷')[1].split('¬')[0] if 'JS÷' in block else ""
                time_info = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else ""
                
                # ГЛАВНАЯ ЛОГИКА: ОПРЕДЕЛЕНИЕ ПЕРИОДА ПО БЛОКАМ СЧЕТА
                # XA - счет 1-го периода, XB - счет 2-го, XC - 3-го
                has_1st_score = 'XA÷' in block
                has_2nd_score = 'XB÷' in block
                has_3rd_score = 'XC÷' in block
                
                # Нам нужен матч, если:
                # 1. 1-й период уже точно БЫЛ (есть счет XA)
                # 2. 2-й период либо идет, либо только закончился (НЕТ счета XB или он только появился)
                # 3. Матч находится в LIVE статусе (AB=3)
                
                is_2nd_period = False
                label = ""

                # Если есть счет 1-го, но нет счета 2-го -> это либо перерыв 1-2, либо сам 2-й период
                if has_1st_score and not has_2nd_score and status_main == '3':
                    is_2nd_period = True
                    label = "⏱ 2-й ПЕРИОД / ПЕРЕРЫВ"
                
                # Резервный поиск по тексту (для Азиатской лиги)
                if not is_2nd_period:
                    if "2" in time_info or js_status == "2" or "П2" in time_info:
                        is_2nd_period = True
                        label = f"⏱ 2-й ПЕРИОД ({time_info})"

                if is_2nd_period:
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    matches.append({
                        'id': f"{home}{away}{s_h}{s_a}{js_status}",
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{label}"
                    })
            except:
                continue
    return matches

async def main():
    logger.info("🚀 ЗАПУСК УМНОГО СКАНЕРА (Детектор периодов по счетам)")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_smart(raw)
            logger.info(f"🔎 В эфире найдено подходящих: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                        logger.info(f"✅ Отправлено: {m['text'][:30]}...")
                    except Exception as e:
                        logger.error(f"Ошибка отправки: {e}")
        
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
