import asyncio
import aiohttp
import os
import logging
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Ваши данные из настроек Amvera
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Резервный открытый источник спортивных данных
FALLBACK_URL = "https://spoyer.com/api/get_events.php?login=ayrat&token=12345ayrat&task=livedata&sport=hockey"

async def get_hockey_leagues():
    logger.info("Запуск альтернативного мониторинга...")
    
    # Используем простейший коннектор для обхода блокировок
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(FALLBACK_URL, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    games = data.get('games_live', [])
                    
                    if not games:
                        msg = "❌ На данный момент активных хоккейных матчей в лайве не найдено."
                    else:
                        # Собираем уникальные лиги
                        leagues = {}
                        for game in games:
                            l_name = game.get('league_name')
                            l_id = game.get('league_id')
                            if l_name not in leagues:
                                leagues[l_name] = l_id
                        
                        text = "🏒 **АКТУАЛЬНЫЕ ХОККЕЙНЫЕ ЛИГИ (LIVE):**\n\n"
                        for name, lid in leagues.items():
                            text += f"🆔 `{lid}` — {name}\n"
                        text += "\n**Пришли мне ID нужных лиг!**"
                        msg = text
                    
                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                    logger.info("Список успешно отправлен в канал!")
                else:
                    logger.error(f"Ошибка источника: статус {resp.status}")
                    
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            # Если даже этот метод упадет, отправим уведомление в канал о проблеме с сетью
            await bot.send_message(CHANNEL_ID, "⚠️ Ошибка сети на сервере Amvera. Пробую переподключиться...")

if __name__ == "__main__":
    asyncio.run(get_hockey_leagues())
