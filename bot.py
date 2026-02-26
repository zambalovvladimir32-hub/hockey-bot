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

# Используем стабильный международный агрегатор (белый список для хостингов)
# Этот эндпоинт отдает данные, аналогичные Flashscore
API_URL = "https://api.livescore.com/api/realtime/soccer" # Для теста связи, заменим на хоккей ниже

async def get_live_hockey():
    logger.info("Запуск мониторинга Flashscore Data...")
    
    # Прямой URL к хоккейному лайву (стабильное зеркало)
    hockey_url = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://www.livescore.com",
        "Referer": "https://www.livescore.com/"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(hockey_url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stages = data.get('Stages', [])
                    
                    if not stages:
                        await bot.send_message(CHANNEL_ID, "🏒 **Связь с Flashscore установлена!**\n\nВ лайве сейчас пусто, жду начала матчей.")
                        return

                    text = "🏒 **МАТЧИ В LIVE (FLASHSCORE):**\n\n"
                    for stage in stages[:5]: # Берем первые 5 лиг
                        league = stage.get('Snm', 'Лига')
                        for game in stage.get('Events', []):
                            home = game.get('T1', [{}])[0].get('Nm', 'Хозяева')
                            away = game.get('T2', [{}])[0].get('Nm', 'Гости')
                            score = f"{game.get('Tr1', 0)}:{game.get('Tr2', 0)}"
                            status = game.get('Eps', '1-й период')
                            
                            text += f"🏆 *{league}*\n⚔️ {home} — {away}\n📊 Счет: `{score}` | `{status}`\n\n"
                    
                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                    logger.info("Данные успешно отправлены!")
                else:
                    logger.error(f"Ошибка API: {resp.status}")
                    await bot.send_message(CHANNEL_ID, f"⚠️ Не удалось получить данные. Код ошибки: {resp.status}")
                    
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")
            await bot.send_message(CHANNEL_ID, f"🚫 Ошибка подключения. Amvera блокирует запрос: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(get_live_hockey())
