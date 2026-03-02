import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Explorer_v56.5")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class DataExplorer:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}

    async def explore_match(self, session, e_id, name):
        url = f"https://www.sofascore.com/api/v1/event/{e_id}/statistics"
        try:
            r = await session.get(url, headers=self.headers, impersonate="chrome110")
            if r.status_code == 200:
                data = r.json()
                for period in data.get('statistics', []):
                    if period.get('period') == 'ALL':
                        logger.info(f"--- 📊 АНАЛИЗ МАТЧА: {name} ---")
                        for group in period.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                # ПЕЧАТАЕМ ВСЕ ИМЕНА ПОКАЗАТЕЛЕЙ
                                logger.info(f"Found Key: '{item['name']}' | Home: {item['homeValue']} | Away: {item['awayValue']}")
            else:
                logger.warning(f"❌ {name}: Ошибка {r.status_code}")
        except Exception as e:
            logger.error(f"💥 Ошибка: {e}")

    async def run(self):
        logger.info("🕵️‍♂️ ЗАПУСК v56.5: ИССЛЕДУЕМ НАЗВАНИЯ ПОЛЕЙ...")
        async with AsyncSession() as session:
            # Берем архивные матчи NHL за 1 марта
            url = "https://www.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/2026-03-01"
            r = await session.get(url, headers=self.headers, impersonate="chrome110")
            
            if r.status_code == 200:
                events = r.json().get('events', [])
                targets = [ev for ev in events if ev.get('tournament', {}).get('name') == 'NHL'][:3]
                
                for ev in targets:
                    await self.explore_match(session, ev['id'], ev['homeTeam']['name'])
                    await asyncio.sleep(2)
            else:
                logger.error(f"API Error: {r.status_code}")

if __name__ == "__main__":
    asyncio.run(DataExplorer().run())
