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

def parse_logical_second(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        league = section.split('¬')[0]
        blocks = section.split('~AA÷')
        
        for block in blocks[1:]:
            try:
                if 'AB÷' not in block: continue
                
                # Извлекаем все важные теги
                ab = block.split('AB÷')[1].split('¬')[0] # Статус матча
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else "" # Код периода
                cr = block.split('CR÷')[1].split('¬')[0] if 'CR÷' in block else "" # Текущий период
                tt = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else "" # Текст времени (напр. 25')
                
                # 1. Только LIVE
                if ab not in ['2', '3']: continue

                # 2. ЖЕСТКИЙ БАН (Исключаем всё лишнее)
                # ac:1 - 1-й пер, ac:3 - 3-й пер, ac:46 - перерыв перед 3-м, ac:6 - конец, ac:4/5 - ОТ/Буллиты
                # cr:1 - 1-й пер, cr:3 - 3-й пер.
                if ac in ['1', '3', '46', '6', '4', '5'] or cr in ['1', '3']:
                    continue
                
                # Дополнительный бан по тексту: если видим "3" или "P3" или "1" в статусе времени
                time_label = tt.upper()
                if "3" in time_label or "P3" in time_label or "1-Й" in time_label:
                    continue

                # 3. ПОДТВЕРЖДЕНИЕ (Остается только Перерыв 1-2 или 2-й период)
                is_break = (ac == '45' or "ПЕРЕРЫВ" in time_label or "PAUSE" in time_label)
                
                # Собираем данные
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                
                status_text = "☕️ ПЕРЕРЫВ (1-2)" if is_break else "⏱ 2-Й ПЕРИОД"
                if tt and tt != "?": status_text += f" [{tt}]"

                matches.append({
                    'id': f"{home}{away}{is_break}{s_h}{s_a}", # ID меняется при смене счета или статуса
                    'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status_text}"
                })
            except:
                continue
    return matches

async def main():
    logger.info("🚀 ЗАПУСК ТЕРМИНАТОРА (Только Перерыв 1-2 и 2-й Период)")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_logical_second(raw)
            logger.info(f"🔎 Найдено в фазе 2-го периода: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                    except: pass
        
        if len(last_sent) > 500: last_sent.clear()
        await asyncio.sleep(30) # Ускорим опрос до 30 сек, чтобы не прозевать начало 2-го периода

if __name__ == "__main__":
    asyncio.run(main())
