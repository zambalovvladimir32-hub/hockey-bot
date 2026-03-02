import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyUltra_v41.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
API_TOKEN = os.getenv("SCRAPER_TOKEN") 

bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.sent_cache = {}

    async def fetch_via_api(self, session, target_url, use_render=False):
        """
        render=true заставляет API запускать реальный браузер (нужно для обхода блока 6556)
        """
        render_param = "&render=true" if use_render else ""
        api_url = f"https://api.scrape.do?token={API_TOKEN}&url={quote(target_url)}{render_param}"
        
        try:
            # Для списка матчей используем быстрый режим, для статы - render
            r = await session.get(api_url, timeout=60)
            if "¬" in r.text:
                return r.text
            return None
        except Exception as e:
            logger.error(f"🌐 Ошибка API: {e}")
            return None

    async def get_stats(self, session, m_id):
        # Важно: для статистики ВСЕГДА используем render=true
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        data = await self.fetch_via_api(session, url, use_render=True)
        
        if data:
            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            for i, p in enumerate(parts):
                if any(x in p for x in ["Броски", "SOG", "Удары"]):
                    try: stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    try: stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
            return stats
        return None

    async def run(self):
        logger.info("🚀 ЗАПУСК v41.0: РЕЖИМ ПОЛНОЙ ЭМУЛЯЦИИ БРАУЗЕРА")
        async with AsyncSession() as session:
            while True:
                try:
                    list_url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
                    list_data = await self.fetch_via_api(session, list_url, use_render=False)
                    
                    if not list_data:
                        logger.warning("📭 Список матчей пуст, пробую render режим...")
                        list_data = await self.fetch_via_api(session, list_url, use_render=True)

                    if list_data:
                        matches = [m for m in list_data.split('~AA÷')[1:] if "AC÷46" in m and "BC÷" not in m]
                        logger.info(f"🔎 Найдено в перерыве: {len(matches)}")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            h_team = m_block.split('AE÷')[1].split('¬')[0]
                            a_team = m_block.split('AF÷')[1].split('¬')[0]
                            
                            try:
                                h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                                a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                            except: continue

                            if (h_score + a_score) <= 1:
                                logger.info(f"🎭 Эмуляция браузера для: {h_team}")
                                res = await self.get_stats(session, m_id)
                                
                                if res:
                                    logger.info(f"📈 Данные получены! Броски: {res['shots']}")
                                    if res['shots'] >= 11 or res['pen'] >= 4:
                                        msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                               f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        self.sent_cache[m_id] = asyncio.get_event_loop().time()
                    
                    await asyncio.sleep(180) # Режим render дорогой, проверяем реже
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
