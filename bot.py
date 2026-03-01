import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyDebug_v38.7")

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
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, proxy=PROXY_URL, impersonate="chrome120", timeout=20)
            data = r.text
            if "¬" not in data:
                logger.warning(f"🛑 МАТЧ {m_id}: Прокси выдал пустоту (байт: {len(data)})")
                return None

            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            for i, p in enumerate(parts):
                if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                    stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
            return stats
        except Exception as e:
            logger.error(f"🌐 Ошибка сети: {e}")
            return None

    async def run(self):
        logger.info("🕵️ ПРОВЕРКА ЗАПУЩЕНА...")
        async with AsyncSession() as session:
            while True:
                try:
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, proxy=PROXY_URL, impersonate="chrome120")
                    
                    # Фильтр: Перерыв (46)
                    all_items = r.text.split('~AA÷')[1:]
                    matches = [m for m in all_items if "AC÷46" in m]
                    
                    logger.info(f"🏟 Всего матчей в перерыве: {len(matches)}")

                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]

                        # Проверка на 2-й период
                        if "BC÷" in m_block:
                            continue 

                        try:
                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                        except: h_score, a_score = 0, 0

                        # ОТЧЕТ В ЛОГИ ПО КАЖДОМУ МАТЧУ
                        if (h_score + a_score) <= 1:
                            logger.info(f"🔎 Проверяю: {h_team} ({h_score}:{a_score}) {a_team}")
                            res = await self.get_stats(session, m_id)
                            
                            if res:
                                logger.info(f"📊 ИТОГ: Броски: {res['shots']}, Штраф: {res['pen']}")
                                if (res['shots'] >= 11 or res['pen'] >= 4) and m_id not in self.sent_cache:
                                    msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                           f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`\n\n"
                                           f"🔗 [Матч](https://www.flashscore.ru/match/{m_id})")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = asyncio.get_event_loop().time()
                                    logger.info(f"💰 СИГНАЛ ОТПРАВЛЕН!")
                            else:
                                logger.info(f"⚠️ У матча {h_team} нет вкладки статистики.")
                        else:
                            logger.info(f"⏭ {h_team} мимо (много голов: {h_score+a_score})")
                            
                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
