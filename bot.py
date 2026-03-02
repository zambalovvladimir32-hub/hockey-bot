import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyZen_v45.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ZENROWS_TOKEN = os.getenv("ZENROWS_TOKEN") 

bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.sent_cache = {}

    async def fetch_zenrows(self, session, target_url):
        if not ZENROWS_TOKEN:
            logger.error("🚨 ZENROWS_TOKEN не найден в Railway!")
            return None

        # Параметры для пробития защиты Flashscore
        # js_render=true — запускает браузер, premium_proxy=true — дает элитные IP
        api_url = (
            f"https://api.zenrows.com/v1/?"
            f"apikey={ZENROWS_TOKEN.strip()}&"
            f"url={quote(target_url)}&"
            f"js_render=true&"
            f"premium_proxy=true&"
            f"wait_for=.event__match" # Ждем появления элементов матча
        )
        
        try:
            r = await session.get(api_url, timeout=60)
            if r.status_code == 200 and "¬" in r.text:
                return r.text
            
            logger.warning(f"⚠️ Статус {r.status_code}. Данных нет. Ответ: {r.text[:100]}")
            return None
        except Exception as e:
            logger.error(f"💥 Ошибка ZenRows: {e}")
            return None

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        return await self.fetch_zenrows(session, url)

    async def run(self):
        logger.info("🚀 ЗАПУСК v45.0 ЧЕРЕЗ ZENROWS")
        async with AsyncSession() as session:
            while True:
                try:
                    # Запрашиваем список матчей
                    list_data = await self.fetch_zenrows(session, "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1")
                    
                    if list_data:
                        matches = [m for m in list_data.split('~AA÷')[1:] if "AC÷46" in m]
                        logger.info(f"🏟 Найдено в перерыве: {len(matches)}")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            try:
                                h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                                a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                                
                                # Экономим: проверяем статику только при счете <= 1 гола
                                if (h_score + a_score) <= 1:
                                    h_team = m_block.split('AE÷')[1].split('¬')[0]
                                    a_team = m_block.split('AF÷')[1].split('¬')[0]
                                    
                                    logger.info(f"📊 Запрос статистики для {h_team}")
                                    stat_data = await self.get_stats(session, m_id)
                                    
                                    if stat_data:
                                        # (Здесь остается твоя логика парсинга shots/pen из прошлых версий)
                                        logger.info(f"✅ Данные получены для {m_id}")
                                        self.sent_cache[m_id] = True 

                            except Exception as ex:
                                logger.error(f"Ошибка парсинга матча: {ex}")
                    
                    # ZenRows стоит дорого, проверяем раз в 5 минут
                    await asyncio.sleep(300) 
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
