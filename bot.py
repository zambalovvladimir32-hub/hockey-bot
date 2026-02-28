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

# Используем оба фида для 100% охвата всех лиг мира
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
                # Добавляем временную метку для обхода кэша
                ts = int(asyncio.get_event_loop().time())
                r = await s.get(f"{url}?t={ts}", headers=headers, proxies=proxies, timeout=15)
                if r.status_code == 200:
                    combined += r.text
            except Exception as e:
                logger.error(f"Ошибка сети: {e}")
    return combined

def parse_universal(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        league = section.split('¬')[0]
        blocks = section.split('~AA÷')
        
        for block in blocks[1:]:
            try:
                if 'AB÷' not in block: continue
                
                # 1. Извлекаем все ключевые коды
                ab = block.split('AB÷')[1].split('¬')[0] # Статус Live (2 или 3)
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else "" # Код периода (2-идет, 45-перерыв)
                cr = block.split('CR÷')[1].split('¬')[0] if 'CR÷' in block else "" # НОМЕР периода (1, 2, 3)
                tt = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else "" # Текст времени (П2, 2nd, и т.д.)

                # 2. ПРОВЕРКА: Это лайв? (AB:2 или AB:3)
                if ab not in ['2', '3']: continue

                # 3. ПРОВЕРКА: Это 2-й период или перерыв перед ним?
                # - CR == 2 (самый точный признак 2-го периода)
                # - AC == 45 (железный признак перерыва 1-2)
                # - Или в тексте времени есть "2" или "П2" (резерв)
                is_2nd_period = (cr == '2' or ac == '2' or '2' in tt or 'П2' in tt.upper())
                is_break_1_2 = (ac == '45' or 'ПЕРЕРЫВ' in tt.upper())

                if is_2nd_period or is_break_1_2:
                    home = block.split('AE÷')[1].split('¬')[0]
                    away = block.split('AF÷')[1].split('¬')[0]
                    s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                    s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                    
                    status_text = "⏱ 2-Й ПЕРИОД" if is_2nd_period else "☕️ ПЕРЕРЫВ (1-2)"
                    # Добавляем инфо о времени, если оно есть
                    if tt and tt != "?": status_text += f" [{tt}]"

                    matches.append({
                        # ID включает счет, чтобы ловить изменения счета внутри 2-го периода
                        'id': f"{home}{away}{s_h}{s_a}{is_break_1_2}", 
                        'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status_text}"
                    })
            except:
                continue
    return matches

async def main():
    logger.info("🌍 ГЛОБАЛЬНЫЙ СКАНЕР ВСЕХ ЛИГ ЗАПУЩЕН")
    last_sent = set()

    while True:
        raw = await get_data()
        if raw:
            found = parse_universal(raw)
            logger.info(f"🔎 Найдено подходящих игр: {len(found)}")
            
            for m in found:
                if m['id'] not in last_sent:
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        last_sent.add(m['id'])
                        logger.info(f"✅ Отправлено: {m['text'][:40]}...")
                    except Exception as e:
                        logger.error(f"Ошибка ТГ: {e}")
        
        # Очистка памяти от старых матчей раз в час
        if len(last_sent) > 800: last_sent.clear()
        
        # Пауза 45 секунд — оптимально, чтобы не забанили и не пропустить гол
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
