import asyncio
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

# ТВОИ ДАННЫЕ
TOKEN = "7543254245:AAH6K2T-7R0n_V-G0W_7mI19o_UshXN_yvI"
CHANNEL_ID = "-1002344716773"

# ДАННЫЕ ПРОКСИ (Вшиты напрямую для надежности)
P_USER = "wiJL0vZ3GEUAcm7"
P_PASS = "lumESo9XGkKWZ4X"
P_HOST = "74.122.59.102"
P_PORT = "58679"

# Собираем строку для библиотеки
PROXY_URL = f"socks5://{P_USER}:{P_PASS}@{P_HOST}:{P_PORT}"

bot = Bot(token=TOKEN)
URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"

async def get_data():
    headers = {
        "x-fsign": "SW9D1eZo",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    proxies = {"http": PROXY_URL, "https": PROXY_URL}

    async with AsyncSession(impersonate="chrome110") as s:
        try:
            logger.info("📡 Пытаюсь подключиться через прокси...")
            r = await s.get(URL, headers=headers, proxies=proxies, timeout=30)
            
            if r.status_code == 200 and len(r.text) > 500:
                return r.text
            
            logger.warning(f"⚠️ Статус: {r.status_code}, Данных: {len(r.text) if r.text else 0}")
        except Exception as e:
            logger.error(f"🔥 Ошибка: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    for block in blocks[1:]:
        # Ищем маркеры 2-го периода
        if 'TT÷2' in block or 'NS÷2' in block or 'П2' in block:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                matches.append(f"🏒 **{home} — {away}**\n⏱ 2-й период")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ ЗАПУЩЕН С ПРЯМЫМ ПОДКЛЮЧЕНИЕМ")
    while True:
        raw_data = await get_data()
        if raw_data:
            logger.info("✅ УСПЕХ! Данные получены.")
            found = parse(raw_data)
            if found:
                await bot.send_message(CHANNEL_ID, "\n\n".join(found[:10]), parse_mode="Markdown")
                logger.info(f"📡 Отправлено: {len(found)}")
            else:
                logger.info("🔎 2-й период пока не найден.")
        else:
            logger.info("⏳ Не удалось пробиться. Жду 2 минуты...")
        
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
