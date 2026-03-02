import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyBalanced_v63.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyBalancedBot:
    def __init__(self):
        self.sent_cache = {}
        self.flash_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo", "X-Referer": "https://www.flashscore.ru/"
        }
        self.sofa_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    async def get_sofa_data(self, session, h_name):
        try:
            clean_h = re.sub(r'\(.*?\)', '', h_name).strip()
            q = quote(clean_h)
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={q}"
            r_search = await session.get(search_url, headers=self.sofa_headers, impersonate="chrome110")
            if r_search.status_code != 200: return None
            
            data = r_search.json()
            event_id = next((res['entity']['id'] for res in data.get('results', []) 
                            if res.get('type') == 'event' and 
                            res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey'), None)
            
            if not event_id: return None

            r_stat = await session.get(f"https://www.sofascore.com/api/v1/event/{event_id}/statistics", headers=self.sofa_headers, impersonate="chrome110")
            if r_stat.status_code == 200:
                s_data = r_stat.json()
                res = {"shots": 0, "pen": 0}
                for period in s_data.get('statistics', []):
                    if period.get('period') == 'ALL':
                        for group in period.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if item['name'] == 'Shots':
                                    res['shots'] = int(item['homeValue']) + int(item['awayValue'])
                                if item['name'] == 'Penalty minutes':
                                    res['pen'] = int(item['homeValue']) + int(item['awayValue'])
                return res
        except: return None

    async def process_match(self, session, m_block):
        try:
            m_id = m_block.split('¬')[0]
            if m_id in self.sent_cache: return

            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
            
            # 1. Счёт 0:0, 1:0 или 0:1
            if (h_score + a_score) > 1: return 

            h_name = m_block.split('AE÷')[1].split('¬')[0]
            a_name = m_block.split('AF÷')[1].split('¬')[0]

            stats = await self.get_sofa_data(session, h_name)
            if not stats: return

            # 🔥 ОБНОВЛЕННАЯ ЛОГИКА: Броски >= 11 И Штраф >= 2 (Одновременно)
            if stats['shots'] >= 11 and stats['pen'] >= 2:
                msg = (f"🏒 **СИГНАЛ: АКТИВНЫЙ ПЕРЕРЫВ**\n"
                       f"📊 {h_name} {h_score}:{a_score} {a_name}\n"
                       f"⏱ Статус: `ПЕРЕРЫВ` (1-й период)\n"
                       f"🎯 Броски: `{stats['shots']}` (>=11 ✅)\n"
                       f"⚖️ Штраф: `{stats['pen']} мин` (>=2 ✅)")
                
                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                self.sent_cache[m_id] = True
                logger.info(f"✅ СИГНАЛ ОТПРАВЛЕН: {h_name} (Б:{stats['shots']} Ш:{stats['pen']})")
            else:
                logger.info(f"📉 {h_name}: Недобор (Б:{stats['shots']} Ш:{stats['pen']})")
        except: pass

    async def run(self):
        logger.info("🚀 ЗАПУСК v63.0: BALANCED (Счёт + Броски 11+ + Штраф 2+)")
        async with AsyncSession() as session:
            while True:
                try:
                    url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
                    r = await session.get(url, headers=self.flash_headers, impersonate="chrome110")
                    if r.status_code == 200 and "¬" in r.text:
                        matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                        if matches:
                            tasks = [self.process_match(session, m) for m in matches]
                            await asyncio.gather(*tasks)
                    await asyncio.sleep(120)
                except: await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyBalancedBot().run())
