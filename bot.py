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

# Прямая ссылка на LIVE-фид хоккея
URL = "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/hockey/", # Важно: реферер на хоккей
    }
    
    try:
        async with AsyncSession(impersonate="chrome110") as s:
            proxies = {"http": PROXY, "https": PROXY} if PROXY else None
            # Добавляем случайный параметр для обхода кэша
            r = await s.get(f"{URL}?cache_bust={asyncio.get_event_loop().time()}", 
                             headers=headers, proxies=proxies, timeout=20)
            
            if r.status_code == 200 and len(r.text) > 500:
                logger.info(f"📡 Данные получены: {len(r.text)} байт")
                return r.text
            else:
                logger.error(f"⚠️ Ошибка: Статус {r.status_code}, Данных мало: {len(r.text)}")
    except Exception as e:
        logger.error(f"❌ Сетевой сбой: {e}")
    return None

def parse(data):
    matches = []
    # Flashscore отделяет матчи по AA÷
    blocks = data.split('~AA÷')
    
    for block in blocks[1:]:
        # КЛЮЧЕВОЙ МОМЕНТ: На твоем скрине P2 — это статус периода.
        # В коде это метки JS÷2, TT÷2 или в блоке 'P2' (информация о периодах)
        
        # Проверяем статус лайва (AB:3 - идет, AB:2 - перерыв)
        is_live = 'AB÷3' in block or 'AB÷2' in block
        # Ищем 2-й период (обычно JS÷2)
        is_2nd_period = 'JS÷2' in block or 'TT÷2' in block or 'LP÷2' in block
        
        if is_2nd_period: # Если нашли статус 2-го периода
            try:
                # Парсим команды
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                
                # Парсим счет (если еще нет голов, ставим 0)
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                # Пытаемся вытащить время (минуту)
                time_m = ""
                if 'BE÷' in block:
                    time_m = f" ({block.split('BE÷')[1].split('¬')[0]}')"

                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период{time_m}")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ В РЕЖИМЕ LIVE-ОХОТЫ")
    reported = set()

    while True:
        raw_data = await get_data()
        if raw_data:
            found_matches = parse(raw_data)
            
            # Чтобы не спамить об одном и том же матче
            new_matches = []
            for m in found_matches:
                match_id = m.split('\n')[0] # Берем только название и счет как ID
                if match_id not in reported:
                    new_matches.append(m)
                    reported.add(match_id)
            
            if new_matches:
                message = "🥅 **НАЙДЕНЫ МАТЧИ (2-Й ПЕРИОД):**\n\n" + "\n\n".join(new_matches)
                await bot.send_message(CHANNEL_ID, message, parse_mode="Markdown")
                logger.info(f"📣 Опубликовано: {len(new_matches)} матчей")
            else:
                logger.info("🔎 Мониторю... Новых игр во 2-м периоде нет.")

        # Очистка памяти раз в час
        if len(reported) > 200: reported.clear()
        
        await asyncio.sleep(45) # Проверяем чаще

if __name__ == "__main__":
    asyncio.run(main())
