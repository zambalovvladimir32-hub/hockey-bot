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

# Прямой поток данных Flashscore
HOCKEY_SOURCE = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Origin": "https://www.flashscorekz.com",
    "Referer": "https://www.flashscorekz.com/"
}

async def run_test():
    logger.info("Запуск теста видимости линии...")
    
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(HOCKEY_SOURCE, timeout=15) as resp:
                if resp.status != 200:
                    await bot.send_message(CHANNEL_ID, f"❌ Ошибка связи с API: {resp.status}")
                    return
                
                data = await resp.json()
                stages = data.get('Stages', [])
                
                if not stages:
                    await bot.send_message(CHANNEL_ID, "⚠️ Связь есть, но в лайве сейчас 0 матчей.")
                    return

                text = "📊 **ТЕСТ ВИДИМОСТИ ЛИНИИ (LIVE):**\n\n"
                count = 0
                
                for stage in stages:
                    league = stage.get('Snm', 'Неизвестная лига')
                    for event in stage.get('Events', []):
                        home = event.get('T1', [{}])[0].get('Nm', '???')
                        away = event.get('T2', [{}])[0].get('Nm', '???')
                        score = f"{event.get('Tr1', 0)}:{event.get('Tr2', 0)}"
                        status = event.get('Eps', 'Ожидание')
                        
                        text += f"🏆 {league}\n⚔️ {home} — {away}\n📊 Счет: `{score}` | `{status}`\n\n"
                        count += 1
                        
                        # Чтобы сообщение не было слишком длинным (лимит Телеграм)
                        if count >= 15: break
                    if count >= 15: break

                text += f"\n✅ **Тест завершен. Бот видит {count} матчей.**"
                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info("Тестовый список отправлен!")

        except Exception as e:
            logger.error(f"Ошибка теста: {e}")
            await bot.send_message(CHANNEL_ID, f"🚫 Ошибка при сканировании: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(run_test())
