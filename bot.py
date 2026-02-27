import asyncio
import os
import logging
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Получаем чистые данные из Railway
PROXY_RAW = os.getenv("PROXY_URL", "").strip()

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    # Сами собираем правильную ссылку для прокси
    # Пробуем через SOCKS5, так как в CyberYozh это основной тип
    proxy_final = f"socks5://{PROXY_RAW}" if PROXY_RAW else None
    proxies = {"http": proxy_final, "https": proxy_final}

    async with AsyncSession(impersonate="chrome110") as s:
        try:
            # Задержка 5 секунд, чтобы не спамить
            await asyncio.sleep(5)
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=30)
            
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            
            logger.warning(f"⚠️ Статус: {r.status_code}, Размер данных: {len(r.text) if r.text else 0}")
        except Exception as e:
            logger.error(f"🔥 Ошибка подключения: {e}")
    return None

def parse(data):
    matches = []
    # Делим данные на отдельные матчи
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Ищем коды 2-го периода (TT=2 или NS=2)
        if 'TT÷2' in block or 'NS÷2' in block:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ Идет 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info(f"🚀 БОТ ЗАПУЩЕН. Прокси в работе: {PROXY_RAW[:10]}...")
    
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info("✅ УСПЕХ! Данные Flashscore получены.")
            found = parse(raw_data)
            if found:
                report = "🥅 **LIVE: 2-Й ПЕРИОД**\n\n" + "\n\n".join(found[:10])
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                logger.info(f"📡 Отправлено в канал: {len(found)} матчей")
            else:
                logger.info("🔎 2-й период пока не найден в матчах.")
        else:
            logger.info("⏳ Не удалось получить данные. Проверь прокси на сайте CyberYozh!")
        
        # Ждем 2 минуты до следующей проверки
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
