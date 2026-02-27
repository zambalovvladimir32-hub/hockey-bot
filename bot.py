import asyncio
import os
import logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Получаем данные без лишних пробелов
PROXY_RAW = os.getenv("PROXY_URL", "").strip()

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    # Собираем строку прокси правильно
    proxy_url = f"socks5://{PROXY_RAW}" if PROXY_RAW else None
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    async with AsyncSession(impersonate="chrome110") as s:
        try:
            # Делаем паузу перед запросом
            await asyncio.sleep(5)
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=30)
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            logger.warning(f"⚠️ Статус: {r.status_code}, Данных: {len(r.text) if r.text else 0}")
        except Exception as e:
            logger.error(f"🔥 Ошибка авторизации: {e}")
    return None

def parse(data):
    matches = []
    for match in data.split('~AA÷')[1:]:
        # Ищем 2-й период через коды Flashscore
        if 'TT÷2' in match or 'NS÷2' in match:
            try:
                home = match.split('AE÷')[1].split('¬')[0]
                away = match.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} vs {away}**\n⏱ Идет 2-й период")
            except: continue
    return matches

async def main():
    logger.info("🚀 БОТ ЗАПУЩЕН. Проверяю прокси...")
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info("✅ ДАННЫЕ ПОЛУЧЕНЫ!")
            found = parse(raw_data)
            if found:
                await bot.send_message(CHANNEL_ID, "\n\n".join(found[:5]), parse_mode="Markdown")
        else:
            logger.info("⏳ Ожидание доступа...")
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
