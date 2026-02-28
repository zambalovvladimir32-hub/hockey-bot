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

def parse_terminator(data):
    matches = []
    # Сначала разбиваем на лиги, чтобы знать названия турниров
    sections = data.split('~ZA÷')
    for section in sections[1:]:
        try:
            league = section.split('¬')[0]
            # Внутри лиги бьем на матчи
            blocks = section.split('~AA÷')
            for block in blocks[1:]:
                if 'AB÷' not in block: continue
                
                # AB: 3 - это Лайв
                # AC: 45 - Перерыв после 1-го, 2 - Второй период
                ab = block.split('AB÷')[1].split('¬')[0]
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else ""
                
                is_break = (ac == '45')
                is_2nd_period = (ac == '2')

                if (ab == '3' and (is_break or is_2nd_period)):
                    # Извлекаем названия команд
                    home = block.split('AE÷')[1].split('¬')[0] if 'AE÷' in block else "Home"
                    away = block.split('AF÷')[1].split('¬')[0] if 'AF÷' in block else "Away"
                    
                    # Счет
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    status_label = "⏱ 2-Й ПЕРИОД" if is_2nd_period else "☕️ ПЕРЕРЫВ (1-2)"
                    
                    matches.append({
                        'id': f"{home}{away}{s_h}{s_a}{ac}",
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status_label}"
                    })
        except:
            continue
    return matches

async def main():
    logger.info("🤖 ТЕРМИНАТОР ЗАПУЩЕН (Фильтр по AC:45/2)")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_terminator(raw)
            logger.info(f"🔎 Найдено подходящих: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                        logger.info(f"✅ Отправлено: {m['id']}")
                    except Exception as e:
                        logger.error(f"Ошибка ТГ: {e}")
        
        # Очистка памяти раз в час
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
