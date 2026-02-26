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

# Мобильный шлюз (то, что использует само приложение Flashscore)
URL = "https://m.flashscore.kz/x/feed/proxy-hockey" 

HEADERS = {
    "User-Agent": "FlashScore/5.10.0 (iPhone; iOS 17.2; Scale/3.00)",
    "X-Referer": "https://www.flashscorekz.com/",
    "X-Requested-With": "com.flashscore.kz",
    "Accept": "*/*"
}

async def run_test():
    logger.info("Пробуем пробиться через мобильный шлюз...")
    
    # Отключаем проверку SSL, чтобы Amvera не ругалась
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        try:
            # Делаем запрос к скрытому фиду
            async with session.get("https://d.flashscore.kz/x/feed/l_3_1", timeout=15) as resp:
                status = resp.status
                raw_data = await resp.text()
                
                if status == 200:
                    # Данные приходят в текстовом формате Flashscore (нужно просто проверить наличие команд)
                    # Если в тексте есть 'Salavat' или 'Traktor', значит мы победили
                    matches_found = []
                    if "Salavat" in raw_data or "Салават" in raw_data: matches_found.append("Салават Юлаев")
                    if "Traktor" in raw_data or "Трактор" in raw_data: matches_found.append("Трактор")
                    if "Gornyak" in raw_data or "Горняк" in raw_data: matches_found.append("Горняк")

                    res_text = "✅ **СВЯЗЬ УСТАНОВЛЕНА!**\n\n"
                    if matches_found:
                        res_text += "Бот видит твои матчи из скриншота:\n" + "\n".join([f"• {m}" for m in matches_found])
                    else:
                        res_text += "Сайт ответил, но матчи в сыром коде не распознаны. Нужно парсить текст."
                    
                    await bot.send_message(CHANNEL_ID, res_text, parse_mode="Markdown")
                else:
                    await bot.send_message(CHANNEL_ID, f"❌ Снова отказ (Код {status}). Пробую запасной шлюз...")
                    # Попытка через глобальное зеркало
                    async with session.get("https://v3ds.ls-api.com/get/hockey/live", timeout=10) as resp2:
                        if resp2.status == 200:
                            await bot.send_message(CHANNEL_ID, "🌐 Запасное зеркало (Global API) работает! Переходим на него.")
                        else:
                            await bot.send_message(CHANNEL_ID, "🚫 Amvera заблокировала все пути. Нужно менять сервер.")

        except Exception as e:
            await bot.send_message(CHANNEL_ID, f"⚠️ Ошибка сети: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(run_test())
