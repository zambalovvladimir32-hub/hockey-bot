import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeySenior_v42.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Если токена нет, бот сразу об этом скажет
API_TOKEN = os.getenv("SCRAPER_TOKEN") 

bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.sent_cache = {}

    async def fetch_via_api(self, session, target_url, use_render=False):
        if not API_TOKEN:
            logger.error("❌ ПЕРЕМЕННАЯ SCRAPER_TOKEN НЕ НАЙДЕНА В RAILWAY!")
            return None

        render_param = "&render=true" if use_render else ""
        api_url = f"https://api.scrape.do?token={API_TOKEN}&url={quote(target_url)}{render_param}"
        
        try:
            logger.info(f"🌐 Отправляю запрос в API (render={use_render})...")
            # Используем обычный запрос, так как API сам маскируется под браузер
            r = await session.get(api_url, timeout=60)
            
            if r.status_code != 200:
                logger.error(f"⚠️ Ошибка API! Статус: {r.status_code}. Ответ: {r.text[:200]}")
                return None
                
            if "¬" in r.text:
                return r.text
            else:
                logger.warning(f"🤔 Данные пришли, но они странные (без '¬'). Ответ: {r.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"💥 Ошибка сети/таймаут: {e}")
            return None

    async def run(self):
        logger.info("🛠 ЗАПУСК v42.0: РЕЖИМ ДИАГНОСТИКИ")
        async with AsyncSession() as session:
            while True:
                try:
                    list_url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
                    
                    # Попытка 1: Обычный запрос API
                    list_data = await self.fetch_via_api(session, list_url, use_render=False)
                    
                    # Попытка 2: Если не вышло, пробуем render
                    if not list_data:
                        logger.info("🔄 Обычный запрос не дал данных, пробуем render=true...")
                        list_data = await self.fetch_via_api(session, list_url, use_render=True)

                    if list_data:
                        logger.info("✅ ДАННЫЕ УСПЕШНО ПОЛУЧЕНЫ! Начинаю парсинг...")
                        matches = [m for m in list_data.split('~AA÷')[1:] if "AC÷46" in m and "BC÷" not in m]
                        logger.info(f"🔎 Найдено в перерыве: {len(matches)}")
                        
                        # (Дальнейшая логика проверки статы скрыта для чистоты тестов, 
                        # нам сейчас главное пробить блок списка матчей)
                    else:
                        logger.error("🛑 Оба запроса провалились. Жду 30 сек и пробую снова.")
                    
                    await asyncio.sleep(30)
                except Exception as e:
                    logger.error(f"Критическая ошибка цикла: {e}")
                    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
