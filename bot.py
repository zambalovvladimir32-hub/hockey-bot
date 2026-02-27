import asyncio
import aiohttp
import os
import logging
import sys
from aiogram import Bot

# Настройка логирования для Amvera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)

# URL API мобильного приложения (стабильный источник для РФ)
URL = "https://stat.sports.ru/hockey/match/list.json?sub_status=live"
HEADERS = {
    "User-Agent": "Sports/7.5.0 (iPhone; iOS 16.0; Scale/3.00)",
    "Accept": "application/json"
}

sent_signals = set()

async def check_logic():
    logger.info("--- СКАНИРОВАНИЕ ЧЕРЕЗ РОССИЙСКИЙ API (SPORTS) ---")
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                if resp.status != 200:
                    logger.error(f"Ошибка доступа к API: {resp.status}")
                    return
                
                data = await resp.json()
                total = 0
                
                # В структуре Sports.ru матчи лежат в списке 'matches'
                matches = data.get('matches', [])
                
                for m in matches:
                    total += 1
                    team1 = m.get('home_team', {}).get('name', 'Команда 1')
                    team2 = m.get('away_team', {}).get('name', 'Команда 2')
                    score1 = m.get('home_score', 0)
                    score2 = m.get('away_score', 0)
                    
                    # Статус матча (минута и период)
                    status = m.get('status_name', '') 
                    
                    logger.info(f"🇷🇺 LIVE: {team1} {score1}:{score2} {team2} | {status}")

                    # Логика сигналов для ВХЛ
                    if "Омские Крылья" in team1 or "Динамо" in team2:
                        key = f"{team1}_{score1}_{score2}"
                        if key not in sent_signals:
                            msg = f"🏒 **МАТЧ НАЙДЕН (РФ ИСТОЧНИК)!**\n{team1} {score1}:{score2} {team2}\nСтатус: {status}"
                            await bot.send_message(CHANNEL_ID, msg)
                            sent_signals.add(key)
                            logger.info(f"СИГНАЛ ОТПРАВЛЕН: {team1}")

                logger.info(f"ИТОГ: Найдено {total} матчей в лайве.")
                
        except Exception as e:
            logger.error(f"Ошибка шлюза Sports: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "✅ Бот переключен на российский источник (Sports.ru).")
    while True:
        await check_logic()
        await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(main())
