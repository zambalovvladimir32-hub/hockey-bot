import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyDataCheck_v38.8")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/",
            "x-requested-with": "XMLHttpRequest",
        }

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, proxy=PROXY_URL, impersonate="chrome120", timeout=20)
            data = r.text
            
            if "¬" not in data:
                return f"Данные отсутствуют (размер: {len(data)})"

            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            found_any = False
            
            for i, p in enumerate(parts):
                # Проверяем все варианты названий бросков
                if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                    try:
                        stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        found_any = True
                    except: pass
                # Проверяем все варианты названий штрафа
                if any(x in p for x in ["ПИМ", "Штраф", "PM", "Штрафное время"]):
                    try:
                        stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        found_any = True
                    except: pass
            
            if found_any:
                return stats
            return "Вкладка статистики пуста (технический перерыв или лига без статы)"
        except Exception as e:
            return f"Ошибка запроса: {e}"

    async def run(self):
        logger.info("🧪 v38.8: ТЕСТОВЫЙ ЗАПУСК. ПРОВЕРЯЕМ ВСЕ МАТЧИ В ПЕРЕРЫВЕ.")
        async with AsyncSession() as session:
            while True:
                try:
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, proxy=PROXY_URL, impersonate="chrome120")
                    # Берем ВСЕ матчи в перерыве (AC÷46) без фильтра по счету
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    
                    logger.info(f"🏟 Найдено {len(matches)} игр в перерыве. Начинаю опрос статы...")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        logger.info(f"📡 Запрашиваю данные: {h_team} vs {a_team}")
                        res = await self.get_stats(session, m_id)
                        
                        if isinstance(res, dict):
                            logger.info(f"✅ СТАТИСТИКА: Броски: {res['shots']}, Штраф: {res['pen']}")
                            # Для теста отправим в канал вообще всё, что нашли
                            await bot.send_message(CHANNEL_ID, f"🧪 Тест статы: {h_team} - {a_team}\n🎯 Броски: {res['shots']}\n⚖️ Штраф: {res['pen']}")
                        else:
                            logger.info(f"⚪️ Результат: {res}")
                            
                        await asyncio.sleep(2) # Пауза между запросами матчей

                    logger.info("⌛️ Цикл окончен. Сплю 60 сек...")
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
