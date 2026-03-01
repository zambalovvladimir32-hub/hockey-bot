import asyncio, os, logging, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("LastStand_v39.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

# Список разных браузеров для маскировки
UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

class HockeyLogic:
    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        # Рандомный заголовок
        headers = {
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/",
            "User-Agent": random.choice(UA_LIST),
            "x-requested-with": "XMLHttpRequest",
        }
        try:
            # Увеличиваем время ожидания и меняем профиль браузера
            r = await session.get(url, headers=headers, proxy=PROXY_URL, impersonate="chrome110", timeout=30)
            if "¬" in r.text:
                parts = r.text.split("¬")
                stats = {"shots": 0, "pen": 0}
                for i, p in enumerate(parts):
                    if any(x in p for x in ["Броски", "SOG", "Удары"]):
                        stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                        stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                return stats
            return f"BLOCK_{len(r.text)}"
        except: return "ERROR"

    async def run(self):
        logger.info("📡 Попытка v39.0 с ротацией заголовков...")
        async with AsyncSession() as session:
            while True:
                try:
                    # Очень долгая пауза между циклами, чтобы не злить фильтры
                    await asyncio.sleep(random.randint(60, 90))
                    
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                         headers={"x-fsign": "SW9D1eZo", "User-Agent": random.choice(UA_LIST)},
                                         proxy=PROXY_URL, impersonate="chrome110")
                    
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m and "BC÷" not in m]
                    logger.info(f"🔎 В перерыве: {len(matches)}")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        # Рандомная задержка ПЕРЕД запросом каждого матча
                        await asyncio.sleep(random.uniform(5, 12))
                        
                        res = await self.get_stats(session, m_id)
                        logger.info(f"📊 Матч {m_id}: {res}")
                        
                        if isinstance(res, dict) and (res['shots'] >= 11 or res['pen'] >= 4):
                            # (Тут код отправки сообщения как в прошлых версиях)
                            pass
                            
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
