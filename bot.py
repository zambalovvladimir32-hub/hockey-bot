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

def parse_perfect_second(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        league = section.split('¬')[0]
        blocks = section.split('~AA÷')
        
        for block in blocks[1:]:
            try:
                if 'AB÷' not in block: continue
                
                # Коды состояния
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else ""
                cr = block.split('CR÷')[1].split('¬')[0] if 'CR÷' in block else ""
                tt = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else ""
                
                # --- ГЛАВНЫЙ ФИЛЬТР: ПРОВЕРКА СЧЕТА ---
                # XA - счет 1-го периода. Если его нет, это 100% первый период.
                # XB - счет 2-го периода. Если он уже есть, значит 2-й период кончился.
                has_1st_period = 'XA÷' in block
                has_2nd_period_ended = 'XB÷' in block

                if not has_1st_period or has_2nd_period_ended:
                    continue

                # Дополнительная проверка: если в тексте времени есть "1", "P1" или "1-й" - в топку
                time_text = tt.upper()
                if any(x in time_text for x in ["1", "P1", "1-Й"]):
                    continue

                # Условие прохода: Перерыв (45) или Код 2-го периода (2 или 15)
                is_break = (ac == '45')
                is_live_2nd = (ac in ['2', '15'] or cr == '2')

                if is_break or is_live_2nd:
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    
                    # Берем ОБЩИЙ счет
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    # Берем счет ТОЛЬКО 1-го периода для информативности
                    score_1p = block.split('XA÷')[1].split('¬')[0]
                    
                    status_label = "☕️ ПЕРЕРЫВ (1-2)" if is_break else "⏱ 2-Й ПЕРИОД"
                    if tt and tt != "?": status_label += f" [{tt}]"

                    matches.append({
                        # Уникальный ID, чтобы не спамить один и тот же матч при каждом обновлении времени
                        'id': f"{home}{away}{is_break}{ac}", 
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status_label}\n(1-й период: {score_1p})"
                    })
            except:
                continue
    return matches

async def main():
    logger.info("🚀 ЗАПУСК БЕЗОШИБОЧНОГО СКАНЕРА (Контроль по периодам)")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_perfect_second(raw)
            logger.info(f"🔎 Найдено чистых матчей 2-го периода: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                    except Exception as e:
                        logger.error(f"Ошибка ТГ: {e}")
        
        # Очистка старых ID раз в час (примерно)
        if len(last_sent) > 1000: last_sent.clear()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
