import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyLocal_v53.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyLocal:
    def __init__(self):
        self.sent_cache = {}
        # Заголовки, которые делают нас "невидимками"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "X-Referer": "https://www.flashscore.ru/",
            "Origin": "https://www.sofascore.com"
        }

    async def fetch_flashscore(self, session):
        """Прямой запрос к Flashscore через curl_cffi (имитация браузера)"""
        url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        try:
            # impersonate="chrome" — главная фишка curl_cffi для обхода Cloudflare
            r = await session.get(url, headers=self.headers, timeout=25, impersonate="chrome110")
            if r.status_code == 200:
                return r.text
            logger.warning(f"Flashscore Error {r.status_code}")
            return None
        except Exception as e:
            logger.error(f"Flashscore Connect Error: {e}")
            return None

    async def get_sofa_stats(self, session, h_name, a_name):
        """Поиск и статика на SofaScore без лишних прослоек"""
        try:
            # 1. Поиск ID матча
            q = quote(f"{h_name} {a_name}")
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={q}"
            r_search = await session.get(search_url, headers=self.headers, impersonate="chrome110")
            
            if r_search.status_code != 200: return None
            
            data = r_search.json()
            event_id = next((res['entity']['id'] for res in data.get('results', []) 
                            if res.get('type') == 'event' and 
                            res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey'), None)
            
            if not event_id: return None

            # 2. Получение статики
            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
            r_stat = await session.get(stat_url, headers=self.headers, impersonate="chrome110")
            
            if r_stat.status_code == 200:
                s_data = r_stat.json()
                res = {"shots": 0, "pen": 0}
                for period in s_data.get('statistics', []):
                    if period.get('period') == 'ALL':
                        for group in period.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'Shots on goal' in item['name']:
                                    res['shots'] = int(item['homeValue']) + int(item['awayValue'])
                                if 'Penalty minutes' in item['name']:
                                    res['pen'] = int(item['homeValue']) + int(item['awayValue'])
                return res
        except: return None

    async def run(self):
        logger.info("🦾 v53.0 ЗАПУЩЕНА: Используем локальные прокси и прямой гибрид")
        async with AsyncSession() as session:
            while True:
                try:
                    data = await self.fetch_flashscore(session)
                    if data and "¬" in data:
                        # Фильтруем только перерывы
                        matches = [m for m in data.split('~AA÷')[1:] if "AC÷46" in m]
                        logger.info(f"🔎 Матчей в перерыве: {len(matches)}")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])

                            if (h_score + a_score) <= 1:
                                h_team = m_block.split('AE÷')[1].split('¬')[0]
                                a_team = m_block.split('AF÷')[1].split('¬')[0]
                                
                                # Очистка имен для SofaScore
                                clean_h = re.sub(r'\(.*?\)', '', h_team).strip()
                                clean_a = re.sub(r'\(.*?\)', '', a_team).strip()

                                logger.info(f"📊 Тяну статику SofaScore для {clean_h} - {clean_a}")
                                stats = await self.get_sofa_stats(session, clean_h, clean_a)
                                
                                if stats:
                                    logger.info(f"📈 Броски: {stats['shots']}, Штраф: {stats['pen']}")
                                    if stats['shots'] >= 11 or stats['pen'] >= 4:
                                        msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                               f"🎯 Броски: `{stats['shots']}` | ⚖️ Штраф: `{stats['pen']} мин`")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        self.sent_cache[m_id] = True

                    await asyncio.sleep(180) # Раз в 3 минуты
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyLocal().run())
