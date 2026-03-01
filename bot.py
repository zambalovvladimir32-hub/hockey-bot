import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyTotalTest_v37.8")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/",
            "X-Requested-With": "XMLHttpRequest"
        }

    async def get_stats(self, session, m_id):
        # Пробуем получить вкладку общей статистики матча
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, impersonate="chrome120", timeout=10)
            data = r.text
            
            # Для отладки: если данных совсем нет, пишем длину ответа
            if not data or "¬" not in data:
                return f"Пустой ответ (len={len(data)})"

            parts = data.split("¬")
            st = {"shots": 0, "pen": 0}
            found_any = False
            
            for i, p in enumerate(parts):
                # Ищем Броски (могут называться по-разному в разных лигах)
                if any(x in p for x in ["Броски", "Удары", "SOG", "Shots on Goal"]):
                    try:
                        st["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        found_any = True
                    except: pass
                
                # Ищем Штрафы
                if any(x in p for x in ["ПИМ", "Штраф", "PM", "Penalties"]):
                    try:
                        st["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        found_any = True
                    except: pass
            
            return st if found_any else "Статистика отсутствует в фиде"
        except Exception as e:
            return f"Ошибка запроса: {e}"

    async def run(self):
        logger.info("🔓 v37.8: ФИЛЬТРЫ ОТКЛЮЧЕНЫ. ПРОВЕРЯЕМ ВСЁ ПОДРЯД.")
        async with AsyncSession() as session:
            while True:
                try:
                    # Запрашиваем весь список хоккея
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, impersonate="chrome120")
                    # Берем вообще все матчи, которые начались или идут (статусы Live, Break, Finished)
                    all_matches = r.text.split('~AA÷')[1:]
                    
                    logger.info(f"📊 Всего матчей в списке: {len(all_matches)}")
                    
                    for m_block in all_matches:
                        try:
                            m_id = m_block.split('¬')[0]
                            h_team = m_block.split('AE÷')[1].split('¬')[0]
                            a_team = m_block.split('AF÷')[1].split('¬')[0]
                            
                            # Тянем статус для лога (чтобы понимать, идет игра или перерыв)
                            m_status = "Status unknown"
                            if "AC÷" in m_block:
                                m_status = m_block.split("AC÷")[1].split("¬")[0]

                            # ЗАХОДИМ В КАЖДЫЙ МАТЧ
                            res = await self.get_stats(session, m_id)
                            
                            if isinstance(res, dict):
                                logger.info(f"✅ ДАННЫЕ ЕСТЬ -> {h_team} vs {a_team} | Статус: {m_status} | Броски: {res['shots']}, ПИМ: {res['pen']}")
                                # Отправим в канал сообщение вообще про любой матч, где есть хоть 1 бросок
                                if res['shots'] > 0:
                                    await bot.send_message(CHANNEL_ID, f"🧪 Тест: {h_team} - {a_team}\nБроски: {res['shots']}\nПИМ: {res['pen']}")
                            else:
                                logger.info(f"⚪️ {h_team} vs {a_team} | {res}")
                            
                            await asyncio.sleep(1) # Минимальная пауза, чтобы не забанили
                        except: continue

                    logger.info("⌛️ Цикл завершен. Спим 60 сек...")
                    await asyncio.sleep(60) 
                except Exception as e:
                    logger.error(f"Ошибка главного цикла: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
