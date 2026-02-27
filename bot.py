import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/0"

async def check_matches():
    headers = {
        "User-Agent": "LiveScore/5.3.1 (iPhone; iOS 15.4.1)",
        "X-Requested-With": "com.livescore.app"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                data = await resp.json()
                found_any = 0
                
                for stage in data.get('Stages', []):
                    league = stage.get('Snm', 'Хоккей')
                    for event in stage.get('Events', []):
                        found_any += 1
                        t1, t2 = event['T1'][0]['Nm'], event['T2'][0]['Nm']
                        status = event.get('Eps', 'LIVE')
                        s1, s2 = event.get('Tr1', '0'), event.get('Tr2', '0')
                        
                        # В ТЕСТОВОМ РЕЖИМЕ шлем вообще всё, что находим
                        logger.info(f"Нашел: {t1} {s1}:{s2} {t2}")
                        
                        # Уникальный ключ для матча, чтобы не спамить
                        key = f"{t1}_{s1}_{s2}_test"
                        if not hasattr(check_matches, "sent"): check_matches.sent = set()
                        
                        if key not in check_matches.sent:
                            msg = f"🏒 **ТЕСТОВАЯ ПРОВЕРКА СВЯЗИ**\n🏆 {league}\n📊 {t1} {s1}:{s2} {t2}\n⏱ Статус: {status}"
                            await bot.send_message(CHANNEL_ID, msg)
                            check_matches.sent.add(key)

                if found_any == 0:
                    logger.info("В мировом лайве сейчас вообще нет хоккея. Ждем матчи.")
                else:
                    logger.info(f"Успешно обработано матчей: {found_any}")

        except Exception as e:
            logger.error(f"Ошибка: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "🛠 Бот в тестовом режиме: шлю в канал все матчи из лайва!")
    while True:
        await check_matches()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
