import asyncio
import aiohttp
import os
import logging
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Прямые ссылки на API
URLS = [
    "https://line12.bkfon-resources.com/live/eventsList",
    "https://line01i.bkfon-resources.com/live/eventsList",
    "https://193.106.173.131/live/eventsList" # Прямой IP на крайний случай
]

async def scan_to_channel():
    logger.info("Попытка получить список лиг через резервные каналы...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    # Отключаем проверку SSL для пробива через облачные фильтры
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for url in URLS:
            try:
                logger.info(f"Запрос к: {url}")
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        text = "🏒 **АКТУАЛЬНЫЕ ХОККЕЙНЫЕ ЛИГИ:**\n\n"
                        found = False
                        
                        # Собираем все турниры из раздела Хоккей
                        for sport in data.get('sports', []):
                            name = sport.get('name', '').lower()
                            if 'хоккей' in name and 'настольный' not in name:
                                l_id = sport.get('id')
                                l_name = sport.get('name')
                                text += f"🆔 `{l_id}` — {l_name}\n"
                                found = True
                        
                        if not found:
                            text = "❌ В лайве сейчас нет хоккейных лиг."
                        else:
                            text += "\n\n**Пришли мне ID лиг из списка выше!**"

                        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                        logger.info("СПИСОК ОТПРАВЛЕН В КАНАЛ!")
                        return 
                    else:
                        logger.warning(f"Сервер {url} ответил: {resp.status}")
            except Exception as e:
                logger.error(f"Ошибка при обращении к {url}: {e}")
        
        logger.error("Все адреса недоступны.")

if __name__ == "__main__":
    asyncio.run(scan_to_channel())
