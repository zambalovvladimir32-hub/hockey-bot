import asyncio
import aiohttp
import os
import logging
from aiogram import Bot

# Настройка логирования для Amvera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Список возможных адресов API (зеркала)
FONBET_URLS = [
    "https://line01i.bkfon-resources.com/live/eventsList",
    "https://line02i.bkfon-resources.com/live/eventsList",
    "https://line03i.bkfon-resources.com/live/eventsList"
]

async def scan_to_channel():
    logger.info("Начинаю попытку подключения к российскому API...")
    
    # Отключаем проверку SSL для стабильности на облачных серверах
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        for url in FONBET_URLS:
            try:
                logger.info(f"Пробую адрес: {url}")
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        text = "🏒 **АКТУАЛЬНЫЕ ХОККЕЙНЫЕ ЛИГИ (FONBET):**\n\n"
                        found = False
                        
                        # Собираем данные
                        for sport in data.get('sports', []):
                            name = sport.get('name', '').lower()
                            if 'хоккей' in name and 'настольный' not in name:
                                l_id = sport.get('id')
                                l_name = sport.get('name')
                                text += f"🆔 `{l_id}` — {l_name}\n"
                                found = True
                        
                        if not found:
                            text = "❌ В данный момент активных хоккейных лиг не найдено."
                        else:
                            text += "\n\n**Пришли мне ID лиг, которые хочешь отслеживать!**"

                        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                        logger.info("Успех! Список отправлен в канал.")
                        return # Выходим после успешной отправки
                    else:
                        logger.warning(f"Сервер ответил статусом: {resp.status}")
            except Exception as e:
                logger.error(f"Не удалось подключиться к {url}: {e}")
        
        logger.error("Все попытки подключения провалились.")

if __name__ == "__main__":
    # Запускаем один раз для проверки
    asyncio.run(scan_to_channel())
