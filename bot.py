import asyncio, os, logging, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyHybrid_v39.1")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    async def run(self):
        logger.info("🧪 ЗАПУСК ГИБРИДНОЙ ПРОВЕРКИ (v39.1)")
        
        async with AsyncSession() as session:
            while True:
                try:
                    # ШАГ 1: Заходим на главную (имитируем обычного юзера)
                    logger.info("🏠 Захожу на главную для получения Cookies...")
                    await session.get("https://www.flashscore.com/", headers={"User-Agent": self.ua}, proxy=PROXY_URL, impersonate="chrome110")
                    await asyncio.sleep(3)

                    # ШАГ 2: Список матчей
                    r_list = await session.get(
                        "https://www.flashscore.com/x/feed/f_4_0_3_en-gz_1", 
                        headers={
                            "User-Agent": self.ua,
                            "x-fsign": "SW9D1eZo", # Проверь это значение в браузере!
                            "x-requested-with": "XMLHttpRequest",
                            "Referer": "https://www.flashscore.com/"
                        },
                        proxy=PROXY_URL,
                        impersonate="chrome110"
                    )
                    
                    matches = [m for m in r_list.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"🏟 Найдено в перерыве: {len(matches)}")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        await asyncio.sleep(random.uniform(2, 5))
                        
                        # ШАГ 3: Запрос статы через .com домен
                        url_stat = f"https://www.flashscore.com/x/feed/d_st_{m_id}_en-gz_1"
                        r_stat = await session.get(
                            url_stat, 
                            headers={
                                "User-Agent": self.ua,
                                "x-fsign": "SW9D1eZo",
                                "x-requested-with": "XMLHttpRequest",
                                "Referer": f"https://www.flashscore.com/match/{m_id}/"
                            },
                            proxy=PROXY_URL,
                            impersonate="chrome110"
                        )

                        if "¬" in r_stat.text:
                            logger.info(f"✅ УСПЕХ! Матч {m_id} отдал данные!")
                            # Здесь можно парсить данные ( shots = ... )
                        else:
                            logger.warning(f"❌ Блок {m_id}. Размер ответа: {len(r_stat.text)}")

                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
