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

# ИСПОЛЬЗУЕМ ПРЯМОЙ LIVE-ФИД (обычно вкладка LIVE имеет индекс 3)
URL = "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/hockey/",
    }
    
    try:
        async with AsyncSession(impersonate="chrome110") as s:
            proxies = {"http": PROXY, "https": PROXY} if PROXY else None
            # Добавляем метку времени, чтобы сайт не присылал старые данные из кэша
            ts_url = f"{URL}?t={int(asyncio.get_event_loop().time())}"
            r = await s.get(ts_url, headers=headers, proxies=proxies, timeout=20)
            
            if r.status_code == 200 and len(r.text) > 1000:
                logger.info(f"📡 Данные получены: {len(r.text)} байт")
                return r.text
    except Exception as e:
        logger.error(f"❌ Ошибка сети: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    for block in blocks[1:]:
        # КЛЮЧЕВОЙ ПОИСК: Ищем признаки 2-го периода
        # JS÷2 - стандартный код, P2 - отображение в браузере
        is_2nd = any(x in block for x in ['JS÷2', 'TT÷2', 'LP÷2', 'NS÷2'])
        
        # Если нашли 2-й период
        if is_2nd:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                
                # Счет
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                # Минута периода (если есть)
                minute = ""
                if 'BE÷' in block:
                    minute = f" ({block.split('BE÷')[1].split('¬')[0]}')"

                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период{minute}")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ В РЕЖИМЕ ЖИВОЙ ОХОТЫ")
    reported = set() # Чтобы не спамить об одной и той же игре

    while True:
        raw_data = await get_data()
        if raw_data:
            found = parse(raw_data)
            
            new_to_send = []
            for m in found:
                # Берем только названия команд как уникальный ключ
                match_key = m.split('\n')[0]
                if match_key not in reported:
                    new_to_send.append(m)
                    reported.add(match_key)
            
            if new_to_send:
                text = "🥅 **LIVE: 2-Й ПЕРИОД ОБНАРУЖЕН**\n\n" + "\n\n".join(new_to_send)
                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"📣 Отправлено: {len(new_to_send)} матчей")
            else:
                logger.info("🔎 Новых матчей во 2-м периоде пока нет...")

        # Очистка памяти раз в пару часов
        if len(reported) > 100: reported.clear()
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
