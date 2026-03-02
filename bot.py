import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyHybrid_v49.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# ZenRows используем только для Flashscore, чтобы не палиться
ZENROWS_TOKEN = os.getenv("ZENROWS_TOKEN") 

bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.sent_cache = {}

    async def fetch_flashscore(self, session):
        """Получаем список матчей с Flashscore через ZenRows (без JS, дешево)"""
        url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        api_url = f"https://api.zenrows.com/v1/?apikey={ZENROWS_TOKEN}&url={quote(url)}&premium_proxy=true"
        try:
            r = await session.get(api_url, timeout=30)
            return r.text if r.status_code == 200 else None
        except: return None

    async def get_sofascore_stats(self, session, home_name, away_name):
        """Ищем матч на SofaScore и тянем статику"""
        try:
            # 1. Поиск матча (SofaScore API обычно не требует прокси, но мы подстрахуемся простым заголовком)
            search_query = quote(f"{home_name} {away_name}")
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={search_query}"
            
            headers = {"User-Agent": "Mozilla/5.0"}
            r_search = await session.get(search_url, headers=headers)
            
            if r_search.status_code != 200: return None
            
            data = r_search.json()
            # Ищем первое событие в категории 'sport':'Ice Hockey'
            event_id = None
            for res in data.get('results', []):
                if res.get('type') == 'event' and res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey':
                    event_id = res['entity']['id']
                    break
            
            if not event_id: return None

            # 2. Получение статистики по ID матча
            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
            r_stat = await session.get(stat_url, headers=headers)
            
            if r_stat.status_code == 200:
                stats_data = r_stat.json()
                res = {"shots": 0, "pen": 0}
                # Ищем период (обычно статистика за весь матч или по периодам)
                # Берем 'ALL' или суммируем. У SofaScore это 'groups'
                for group in stats_data.get('statistics', [{}])[0].get('groups', []):
                    for item in group.get('statisticsItems', []):
                        if item['name'] in ['Shots on goal', 'Total shots on goal']:
                            res['shots'] = int(item['homeValue']) + int(item['awayValue'])
                        if item['name'] in ['Penalty minutes', 'Penalties']:
                            res['pen'] = int(item['homeValue']) + int(item['awayValue'])
                return res
        except Exception as e:
            logger.debug(f"SofaScore error: {e}")
            return None

    async def run(self):
        logger.info("🦾 ГИБРИД v49.0 ЗАПУЩЕН: Flashscore (ID) + SofaScore (Stats)")
        async with AsyncSession() as session:
            while True:
                try:
                    list_data = await self.fetch_flashscore(session)
                    if list_data and "¬" in list_data:
                        matches = [m for m in list_data.split('~AA÷')[1:] if "AC÷46" in m]
                        logger.info(f"🏟 В перерыве: {len(matches)}")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            try:
                                h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                                a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                                
                                if (h_score + a_score) <= 1:
                                    h_name = m_block.split('AE÷')[1].split('¬')[0]
                                    a_name = m_block.split('AF÷')[1].split('¬')[0]
                                    
                                    logger.info(f"🔎 Штурмуем SofaScore для: {h_name} - {a_name}")
                                    # Очищаем названия от лишних символов (типа (Rus))
                                    clean_h = re.sub(r'\(.*?\)', '', h_name).strip()
                                    clean_a = re.sub(r'\(.*?\)', '', a_name).strip()
                                    
                                    res = await self.get_sofascore_stats(session, clean_h, clean_a)
                                    
                                    if res:
                                        logger.info(f"✅ Стата получена: {res['shots']} бросков")
                                        if res['shots'] >= 11 or res['pen'] >= 4:
                                            msg = (f"🏒 **{h_name} {h_score}:{a_score} {a_name}**\n"
                                                   f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`")
                                            await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                            self.sent_cache[m_id] = True
                            except: continue
                    
                    await asyncio.sleep(200)
                except Exception as e:
                    logger.error(f"Цикл: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
