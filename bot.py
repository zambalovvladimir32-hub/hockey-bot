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
# Меняем 0 на 1 в URL, чтобы получать ТОЛЬКО Live-матчи (ускоряет работу)
URL = "https://www.flashscore.ru/x/feed/f_4_1_2_ru-ru_1"

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
    }
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None

    try:
        async with AsyncSession(impersonate="chrome110") as s:
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=30)
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            logger.warning(f"⚠️ Ответ сайта подозрительный: {len(r.text)} байт.")
    except Exception as e:
        logger.error(f"🔥 Ошибка запроса: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    for block in blocks[1:]:
        # Ищем признаки 2-го периода: TT=2 (период), JS=2 (статус), либо текст "2-й период"
        is_2nd = any(tag in block for tag in ['TT÷2', 'JS÷2', 'NS÷2', 'AS÷2'])
        
        if is_2nd:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                # Извлекаем счет
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период")
            except:
                continue
    
    # Если ничего не нашли, выведем в лог кусок первого матча для анализа
    if not matches and len(blocks) > 1:
        logger.info(f"🧪 Анализ структуры матча: {blocks[1][:150]}")
        
    return matches

async def main():
    logger.info("🚀 БОТ В РЕЖИМЕ ПОИСКА 2-ГО ПЕРИОДА")
    while True:
        raw_data = await get_data()
        if raw_data:
            found = parse(raw_data)
            if found:
                text = "🥅 **LIVE: ХОККЕЙ (2-Й ПЕРИОД)**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"✅ Отправлено сигналов: {len(found)}")
            else:
                logger.info("🔎 Во 2-м периоде пока пусто. Ждем...")
        await asyncio.sleep(60) # Проверяем каждую минуту

if __name__ == "__main__":
    asyncio.run(main())
