import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ArchiveTest_v56.2")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyArchive:
    def __init__(self):
        self.flash_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo", 
            "X-Referer": "https://www.flashscore.ru/"
        }
        self.sofa_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    async def get_sofa_stats(self, session, h_team, a_team):
        """Проверка связи с архивом SofaScore"""
        try:
            # Очистка названия для поиска
            clean_h = re.sub(r'\(.*?\)', '', h_team).strip()
            logger.info(f"🔎 Поиск архива для: {clean_h}")
            
            q = quote(clean_h)
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={q}"
            r = await session.get(search_url, headers=self.sofa_headers, impersonate="chrome110")
            
            if r.status_code != 200: return None
            
            data = r.json()
            event_id = None
            for res in data.get('results', []):
                if res.get('type') == 'event' and res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey':
                    event_id = res['entity']['id']
                    break
            
            if not event_id: return None

            # Запрос статистики завершенного матча
            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
            r_stat = await session.get(stat_url, headers=self.sofa_headers, impersonate="chrome110")
            
            if r_stat.status_code == 200:
                s_data = r_stat.json()
                res = {"shots": 0, "pen": 0}
                # Парсим JSON статистики
                for period_data in s_data.get('statistics', []):
                    if period_data.get('period') == 'ALL':
                        for group in period_data.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'Shots on goal' in item['name']:
                                    res['shots'] = int(item['homeValue']) + int(item['awayValue'])
                                if 'Penalty minutes' in item['name']:
                                    res['pen'] = int(item['homeValue']) + int(item['awayValue'])
                return res
            return None
        except Exception as e:
            logger.error(f"💥 Ошибка: {e}")
            return None

    async def run(self):
        logger.info("🧪 ТЕСТ ПО АРХИВУ: Flashscore (Список) -> SofaScore (Цифры)")
        async with AsyncSession() as session:
            # Берем список вчерашних/завершенных игр (f_4_-1_3 — это архив за вчера)
            url = "https://www.flashscore.ru/x/feed/f_4_-1_3_ru-ru_1"
            r = await session.get(url, headers=self.flash_headers, impersonate="chrome110")
            
            if r.status_code == 200 and "¬" in r.text:
                # Берем первые 5 завершенных матчей (AC÷3 — статус 'Матч завершен')
                matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷3" in m][:5]
                logger.info(f"📋 Нашел {len(matches)} завершенных игр для проверки.")

                for m_block in matches:
                    h_team = m_block.split('AE÷')[1].split('¬')[0]
                    a_team = m_block.split('AF÷')[1].split('¬')[0]
                    
                    stats = await self.get_sofa_stats(session, h_team, a_team)
                    
                    if stats:
                        logger.info(f"✅ ПОЛУЧЕНО! {h_team} - {a_team}: Броски: {stats['shots']}, Штраф: {stats['pen']}")
                        await bot.send_message(CHANNEL_ID, f"📜 ТЕСТ ПО АРХИВУ:\n🏒 {h_team} - {a_team}\n📊 Броски: {stats['shots']}\n⚖️ Штраф: {stats['pen']}\n🔥 Связка Flash+Sofa ПОДТВЕРЖДЕНА!")
                    else:
                        logger.warning(f"⚠️ Для {h_team} статика в архиве не найдена (возможно, лига без детальной статы)")
            else:
                logger.error(f"❌ Flashscore не отдал архив (Status: {r.status_code})")

if __name__ == "__main__":
    asyncio.run(HockeyArchive().run())
