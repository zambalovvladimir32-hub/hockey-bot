import asyncio
import os
import logging
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)
# Прямая ссылка на фид хоккея
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/",
    }
    
    # Настройка прокси для curl_cffi
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None

    try:
        async with AsyncSession(impersonate="chrome110") as s:
            logger.info(f"🛰 Запрос через прокси: {PROXY[:20]}..." if PROXY else "🛰 Запрос напрямую")
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=30)
            
            if r.status_code == 200:
                if len(r.text) > 1000: # Реальные данные обычно весят много
                    return r.text
                logger.warning(f"⚠️ Мало данных: {len(r.text)} байт. Прокси заблокирован?")
            elif r.status_code == 401:
                logger.error("🔥 Ошибка 401: Прокси отклонил логин/пароль!")
            else:
                logger.error(f"❌ Ошибка сайта: {r.status_code}")
    except Exception as e:
        logger.error(f"💥 Ошибка подключения: {e}")
    return None

def parse(data):
    matches = []
    # Flashscore делит матчи через ~AA÷
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Ищем 2-й период (TT÷2 или NS÷2)
        if 'TT÷2' in block or 'NS÷2' in block:
            try:
                # AE - команда 1, AF - команда 2
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ Идет 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 СИСТЕМА ЗАПУЩЕНА")
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info(f"✅ УСПЕХ! Данные получены ({len(raw_data)} байт)")
            found = parse(raw_data)
            if found:
                report = "🏒 **LIVE: ХОККЕЙ (2-Й ПЕРИОД)**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"📡 Отправлено: {len(found)} матчей")
            else:
                logger.info("🔎 Матчи во 2-м периоде не найдены.")
        else:
            logger.info("⏳ Повтор через 2 минуты...")
        
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
