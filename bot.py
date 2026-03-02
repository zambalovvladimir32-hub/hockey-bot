import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyHybrid_v52.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyHybrid:
    def __init__(self):
        self.sent_cache = {}
        # Заголовки для обхода простых блокировок
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "X-Referer": "https://www.flashscore.ru/",
            "Origin": "https://www.sofascore.com"
        }

    async def fetch_flashscore_list(self, session):
        """Получаем список матчей с Flashscore напрямую"""
        url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, timeout=20)
            if r.status_code == 200:
                return r.text
            logger.warning(f"Flashscore status: {r.status_code}")
            return None
        except: return None

    async def get_sofa_stats(self, session, h_name, a_name):
        """Ищем матч на SofaScore и берем статистику"""
        try:
            # 1. Поиск матча по именам
            query = quote(f"{h_name} {a_name}")
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={query}"
            r_search = await session.get(search_url, headers=self.headers)
            
            if r_search.status_code != 200: return None
            
            data = r_search.json()
            event_id = None
            for res in data.get('results', []):
                if res.get('type') == 'event' and res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey':
                    event_id = res['entity']['id']
                    break
            
            if not event_id: return None

            # 2. Получение статистики
            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
            r_stat = await session.get(stat_url, headers=self.headers)
            
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
        logger.info("🦾 ГИБРИД v52.0: Flashscore (Live) + SofaScore (Stats)")
        async with AsyncSession() as session:
            while True:
                try:
                    data = await self.fetch_flashscore_list(session)
                    if data and "¬" in data:
                        # Фильтруем матчи в перерыве (AC÷46)
                        matches = [m for m in data.split('~AA÷')[1:] if "AC÷46" in m]
                        logger.info(f"🏟 Перерывы на Flashscore: {len(matches)}")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])

                            if (h_score + a_score) <= 1:
                                h_team = m_block.split('AE÷')[1].split('¬')[0]
                                a_team = m_block.split('AF÷')[1].split('¬')[0]
                                
                                # Очистка имен (убираем (Rus) и т.д.)
                                clean_h = re.sub(r'\(.*?\)', '', h_team).strip()
                                clean_a = re.sub(r'\(.*?\)', '', a_team).strip()

                                logger.info(f"🔎 Запрос статистики Sofa для {clean_h}")
                                stats = await self.get_sofa_stats(session, clean_h, clean_a)
                                
                                if stats:
                                    if stats['shots'] >= 11 or stats['pen'] >= 4:
                                        msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                               f"🎯 Броски: `{stats['shots']}` | ⚖️ Штраф: `{stats['pen']} мин`")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        self.sent_cache[m_id] = True
                                        logger.info(f"✅ Сигнал отправлен: {h_team}")

                    await asyncio.sleep(150) # Проверка каждые 2.5 минуты
                except Exception as e:
                    logger.error(f"Цикл: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyHybrid().run())
