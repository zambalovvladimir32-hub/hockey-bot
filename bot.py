import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("DataHungry_v56.4")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class DataHungry:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}

    async def check_stats(self, session, e_id, name):
        """Проверяем наличие ЛЮБОЙ статистики"""
        url = f"https://www.sofascore.com/api/v1/event/{e_id}/statistics"
        try:
            r = await session.get(url, headers=self.headers, impersonate="chrome110")
            if r.status_code != 200:
                logger.warning(f"❌ {name}: Статус {r.status_code}")
                return
            
            data = r.json()
            # Выводим в лог все доступные категории для этого матча
            stats_found = []
            for period in data.get('statistics', []):
                if period.get('period') == 'ALL':
                    for group in period.get('groups', []):
                        for item in group.get('statisticsItems', []):
                            stats_found.append(item['name'])
            
            if stats_found:
                logger.info(f"✅ {name}: Найдено {len(stats_found)} показателей. Есть ли броски? {'Shots on goal' in stats_found}")
                if 'Shots on goal' in stats_found:
                    # Если нашли броски, сразу шлем в ТГ
                    await bot.send_message(CHANNEL_ID, f"🎯 ЕСТЬ КОНТАКТ!\n🏒 {name}\n📊 Статистика бросков доступна!")
            else:
                logger.info(f"⚪️ {name}: Статистика пуста")
        except Exception as e:
            logger.error(f"💥 {name}: Ошибка запроса: {e}")

    async def run(self):
        logger.info("🧨 ЗАПУСК v56.4: ПРЯМАЯ ПРОВЕРКА ЦИФР ПО NHL/KHL")
        async with AsyncSession() as session:
            # Берем свежие матчи прямо у SofaScore
            url = "https://www.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/2026-03-01"
            r = await session.get(url, headers=self.headers, impersonate="chrome110")
            
            if r.status_code == 200:
                events = r.json().get('events', [])
                # Проверяем только матчи NHL и KHL (там стата 100% должна быть)
                targets = [ev for ev in events if ev.get('tournament', {}).get('name') in ['NHL', 'KHL']]
                logger.info(f"📋 Нашел {len(targets)} целевых матчей. Начинаю прозвон...")

                for ev in targets[:10]: # Проверим первые 10 для скорости
                    await self.check_stats(session, ev['id'], ev['homeTeam']['name'])
                    await asyncio.sleep(1) # Небольшая пауза
            else:
                logger.error(f"Sofa API Error: {r.status_code}")

if __name__ == "__main__":
    asyncio.run(DataHungry().run())
