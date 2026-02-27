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
# Пробуем основной домен (иногда d. домен блокируют сильнее)
URL = "https://www.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    # Расширенный набор заголовков, как у реального браузера Chrome
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Origin": "https://www.flashscore.ru",
        "Referer": "https://www.flashscore.ru/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=1, i",
    }
    
    proxies = {"http": PROXY, "https": PROXY} if PROXY else None

    try:
        async with AsyncSession(impersonate="chrome110") as s:
            # Сначала проверяем, какой у нас IP (для самодиагностики)
            try:
                ip_check = await s.get("https://ifconfig.me/ip", proxies=proxies, timeout=10)
                logger.info(f"🌐 Бот выходит в сеть через IP: {ip_check.text.strip()}")
            except:
                logger.warning("⚠️ Не удалось проверить внешний IP, но продолжаем...")

            logger.info("📡 Запрашиваем данные у Flashscore...")
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=30)
            
            if r.status_code == 200:
                content_size = len(r.text)
                if content_size > 500: # Реальный фид весит от 10кб до 500кб
                    return r.text
                logger.warning(f"⚠️ Получен пустой ответ ({content_size} байт). Flashscore нас раскусил.")
            else:
                logger.error(f"❌ Ошибка сайта: {r.status_code}")
    except Exception as e:
        logger.error(f"🔥 Ошибка: {e}")
    return None

def parse(data):
    matches = []
    # Flashscore отдает данные кусками, разделенными ~AA÷
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Ищем матчи, где статус "2-й период" (TT÷2)
        if 'TT÷2' in block or 'NS÷2' in block:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                # Извлекаем счет, если он есть
                score_home = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                score_away = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                matches.append(f"🏒 **{home} {score_home}:{score_away} {away}**\n⏱ Идет 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ ВЫХОДИТ НА ФИНИШНУЮ ПРЯМУЮ")
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info(f"✅ ПОЛУЧЕНО {len(raw_data)} байт данных!")
            found = parse(raw_data)
            if found:
                # Отправляем только первые 10 матчей, чтобы не спамить
                report = "🥅 **LIVE: 2-Й ПЕРИОД (ХОККЕЙ)**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"📡 Сигналы ({len(found)}) успешно отправлены!")
            else:
                logger.info("🔎 Матчей во 2-м периоде сейчас нет.")
        else:
            logger.info("⏳ Повтор через 2 минуты...")
        
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
