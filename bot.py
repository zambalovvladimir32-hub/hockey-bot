import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyForceTest_v37.7")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = {} 

    async def get_stats(self, session, m_id):
        # Пытаемся забрать вкладку статистики
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, impersonate="chrome120", timeout=10)
            if "¬" in r.text:
                parts = r.text.split("¬")
                st = {"shots": 0, "pen": 0}
                for i, p in enumerate(parts):
                    # Ищем ключевые слова (Броски, Удары, SOG)
                    if any(x in p for x in ["Броски", "Удары", "SOG"]):
                        st["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    # Ищем штрафы (ПИМ, Штраф, PM)
                    if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                        st["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                return st
        except: return None

    async def run(self):
        logger.info("🧪 v37.7 ТЕСТОВЫЙ РЕЖИМ: ПРОВЕРКА ВСЕХ МАТЧЕЙ БЕЗ ФИЛЬТРА СЧЕТА")
        async with AsyncSession() as session:
            while True:
                try:
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, impersonate="chrome120")
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    
                    logger.info(f"🔎 Вижу в перерыве: {len(matches)} матчей")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        if "BC÷" in m_block: continue # Оставляем только 1-й перерыв

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        try:
                            h_score = m_block.split('AG÷')[1].split('¬')[0]
                            a_score = m_block.split('AH÷')[1].split('¬')[0]
                        except:
                            h_score, a_score = "0", "0"

                        # ТЕПЕРЬ ЗАХОДИМ В КАЖДУЮ ИГРУ БЕЗ ПРОВЕРКИ СЧЕТА
                        stats = await self.get_stats(session, m_id)
                        
                        if stats:
                            # Логируем абсолютно всё, что нашли
                            logger.info(f"📊 ДАННЫЕ ПОЛУЧЕНЫ -> {h_team} ({h_score}:{a_score}) {a_team} | Броски: {stats['shots']}, ПИМ: {stats['pen']}")
                            
                            # В канал шлем только если всё-таки бросков 11+ или ПИМ 4+
                            if stats["shots"] >= 11 or stats["pen"] >= 4:
                                text = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                       f"🎯 Броски: `{stats['shots']}`\n"
                                       f"⚖️ Штраф: `{stats['pen']} мин`\n"
                                       f"🔗 [Матч](https://www.flashscore.ru/match/{m_id})")
                                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                                self.sent_cache[m_id] = asyncio.get_event_loop().time()
                        else:
                            logger.warning(f"⚪️ У матча {h_team}-{a_team} нет вкладки статистики на Flashscore")

                    await asyncio.sleep(45) 
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
