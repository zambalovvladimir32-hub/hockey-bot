import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("DeepCheck_v56.3")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyDeepCheck:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}

    async def get_stats_by_id(self, session, event_id, name):
        """Прямой запрос цифр по ID"""
        url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
        r = await session.get(url, headers=self.headers, impersonate="chrome110")
        if r.status_code == 200:
            data = r.json()
            for period in data.get('statistics', []):
                if period.get('period') == 'ALL':
                    shots = 0
                    for group in period.get('groups', []):
                        for item in group.get('statisticsItems', []):
                            if 'Shots on goal' in item['name']:
                                shots = int(item['homeValue']) + int(item['awayValue'])
                                logger.info(f"✅ ВЗЯЛ ЦИФРЫ ДЛЯ {name}: Броски = {shots}")
                                return shots
        return None

    async def run(self):
        logger.info("🧪 ГЛУБОКАЯ ПРОВЕРКА: Ищу матчи КХЛ/ВХЛ в архиве...")
        async with AsyncSession() as session:
            # 1. Запрашиваем вчерашние матчи хоккея напрямую у SofaScore (чтобы не зависеть от перевода Flashscore)
            # Дата 2026-03-01 (вчера)
            url = "https://www.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/2026-03-01"
            r = await session.get(url, headers=self.headers, impersonate="chrome110")
            
            if r.status_code == 200:
                events = r.json().get('events', [])
                found = 0
                for ev in events:
                    # Ищем матчи крупных лиг (КХЛ, НХЛ, Чехия, Германия)
                    league = ev.get('tournament', {}).get('name', '')
                    if any(x in league for x in ['KHL', 'VHL', 'NHL', 'Extraliga', 'DEL', 'SHL']):
                        e_id = ev['id']
                        h_name = ev['homeTeam']['name']
                        a_name = ev['awayTeam']['name']
                        
                        logger.info(f"🔎 Проверяю старый матч: {h_name} - {a_name} ({league})")
                        shots = await self.get_stats_by_id(session, e_id, h_name)
                        
                        if shots:
                            await bot.send_message(CHANNEL_ID, f"📊 ПОДТВЕРЖДЕНО: Бот видит статистику!\n🏒 {h_name} vs {a_name}\n🎯 Броски: {shots}")
                            found += 1
                    if found >= 3: break # Нам хватит 3-х примеров
            else:
                logger.error(f"Sofa API Error: {r.status_code}")

if __name__ == "__main__":
    asyncio.run(HockeyDeepCheck().run())
