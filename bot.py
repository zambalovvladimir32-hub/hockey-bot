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

# ОБНОВЛЕННЫЙ URL: Теперь запрашиваем именно LIVE-вкладку (f_4_1_3)
URL = "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
    }
    
    try:
        async with AsyncSession(impersonate="chrome110") as s:
            proxies = {"http": PROXY, "https": PROXY} if PROXY else None
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=20)
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            else:
                logger.error(f"⚠️ Плохой ответ: {r.status_code}, размер: {len(r.text)}")
    except Exception as e:
        logger.error(f"❌ Ошибка сети: {e}")
    return None

def parse(data):
    matches = []
    # Flashscore разделяет матчи через ~AA÷
    blocks = data.split('~AA÷')
    
    for block in blocks[1:]:
        # Ищем статус периода. В хоккее 2-й период часто JS÷2 или просто текст в других полях
        # Проверяем все возможные метки '2-го периода'
        is_2nd = any(x in block for x in ['JS÷2', 'TT÷2', 'LP÷2', 'NS÷2'])
        # Проверяем, что матч идет сейчас (AB÷3) или перерыв после 1-го (в некоторых лигах)
        is_live = 'AB÷3' in block or 'AB÷2' in block 

        if is_2nd:
            try:
                # Извлекаем названия команд
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                
                # Извлекаем счет (AG - дом, AH - гости)
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                # Извлекаем время периода (если есть)
                time_val = ""
                if 'BE÷' in block: # Минута периода
                    time_val = f" ({block.split('BE÷')[1].split('¬')[0]}')"

                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период{time_val}")
            except Exception as e:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ ЗАПУЩЕН (LIVE-РЕЖИМ)")
    # Список ID матчей, о которых уже сообщили, чтобы не спамить каждую минуту
    reported_matches = set()

    while True:
        raw_data = await get_data()
        if raw_data:
            found = parse(raw_data)
            
            # Очищаем список старых матчей раз в час (примерно)
            if len(reported_matches) > 100: reported_matches.clear()

            new_to_send = []
            for m in found:
                if m not in reported_matches:
                    new_to_send.append(m)
                    reported_matches.add(m)

            if new_to_send:
                text = "🥅 **LIVE: 2-Й ПЕРИОД**\n\n" + "\n\n".join(new_to_send)
                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"📣 Отправлено: {len(new_to_send)} игр")
            else:
                logger.info("🔎 Новых игр во 2-м периоде пока нет...")
        
        await asyncio.sleep(60) # Проверка каждую минуту

if __name__ == "__main__":
    asyncio.run(main())
