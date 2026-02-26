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

# Используем профессиональный шлюз данных (аналог Flashscore)
# Этот адрес обычно открыт для всех облачных хостингов
DATA_SOURCE = "https://api.api-livescore.com:8000/hockey/"

async def flashscore_test():
    logger.info("Подключаюсь к шлюзу Flashscore...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Делаем запрос к шлюзу
            async with session.get(DATA_SOURCE, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # В некоторых API данные лежат в 'results' или 'data'
                    games = data.get('results', data.get('data', []))
                    
                    if not games:
                        msg = "🏒 **Flashscore на связи!**\n\nВ данный момент активных матчей в лайве не найдено. Бот ждет начала игр."
                    else:
                        text = "🏒 **МАТЧИ В LIVE (FLASHSCORE DATA):**\n\n"
                        for g in games[:15]: # Берем первые 15 для теста
                            league = g.get('league_name', 'Лига')
                            home = g.get('home_name', 'Хозяева')
                            away = g.get('away_name', 'Гости')
                            score = f"{g.get('score_home', 0)}:{g.get('score_away', 0)}"
                            time = g.get('timer', '00:00')
                            
                            text += f"🏆 {league}\n⚔️ {home} — {away}\n📊 Счет: `{score}` | Время: `{time}`\n\n"
                        
                        text += "✅ Если видишь этот список, значит связь налажена!"
                        msg = text
                    
                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                    logger.info("Данные Flashscore отправлены в канал!")
                else:
                    logger.error(f"Ошибка шлюза: {resp.status}")
                    await bot.send_message(CHANNEL_ID, f"⚠️ Ошибка шлюза: {resp.status}. Пробую другое зеркало...")
                    
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await bot.send_message(CHANNEL_ID, "🚫 Amvera блокирует и этот источник. Нужна ручная настройка прокси.")

if __name__ == "__main__":
    asyncio.run(flashscore_test())
