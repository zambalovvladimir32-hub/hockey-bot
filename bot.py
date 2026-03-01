import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyDeepScan_v37.9")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyLogic:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "Referer": "https://www.flashscore.ru/",
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, impersonate="chrome120", timeout=10)
            data = r.text
            
            if not data or "¬" not in data:
                return f"Действительно пусто (len={len(data)})"

            # ПАРСИНГ
            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            
            for i, p in enumerate(parts):
                # Ищем броски: Броски, Удары, SOG, S_O_G
                if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                    try:
                        # Берем значения для обеих команд
                        stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
                
                # Ищем штрафы: ПИМ, Штраф, PM, Penalt
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    try:
                        stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
            
            return stats
        except Exception as e:
            return f"Ошибка: {e}"

    async def run(self):
        logger.info("🔍 v37.9: ГЛУБОКОЕ СКАНИРОВАНИЕ ЗАПУЩЕНО")
        async with AsyncSession() as session:
            while True:
                try:
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, impersonate="chrome120")
                    # Берем игры только в ПЕРЕРЫВЕ (возвращаем твою логику)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache or "BC÷" in m_block: continue

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        try:
                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                        except: h_score, a_score = 0, 0

                        # ПРОВЕРКА СЧЕТА (0:0, 1:0, 0:1)
                        if (h_score + a_score) <= 1:
                            res = await self.get_stats(session, m_id)
                            
                            if isinstance(res, dict):
                                logger.info(f"📊 СТАТИСТИКА ЕСТЬ! {h_team} vs {a_team} | Броски: {res['shots']}, ПИМ: {res['pen']}")
                                
                                # ПРОВЕРКА ТВОИХ ЛИМИТОВ
                                if res['shots'] >= 11 or res['pen'] >= 4:
                                    msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                           f"🎯 Броски за 1-й период: `{res['shots']}`\n"
                                           f"⚖️ Штраф: `{res['pen']} мин`\n"
                                           f"🔗 [Матч](https://www.flashscore.ru/match/{m_id})")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = asyncio.get_event_loop().time()
                            else:
                                logger.info(f"⚪️ {h_team}: {res}")

                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
