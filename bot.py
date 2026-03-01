import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeySafe_v38.6")

# Все секретные данные тянем из переменных окружения
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
            # Используем скрытый прокси для обхода блокировки 6556 байт
            r = await session.get(url, headers=self.headers, proxy=PROXY_URL, impersonate="chrome120", timeout=20)
            data = r.text
            
            if "¬" not in data:
                logger.warning(f"⚠️ Данные не получены (len={len(data)}). Проверь переменную PROXY_URL.")
                return None

            parts = data.split("¬")
            stats = {"shots": 0, "pen": 0}
            for i, p in enumerate(parts):
                if any(x in p for x in ["Броски", "SOG", "Удары в створ"]):
                    try:
                        stats["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
                if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                    try:
                        stats["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    except: pass
            return stats
        except Exception as e:
            logger.error(f"🌐 Ошибка прокси: {e}")
            return None

    async def run(self):
        logger.info("🛡 Бот запущен в безопасном режиме (прокси скрыт)")
        if not PROXY_URL:
            logger.error("❌ ПЕРЕМЕННАЯ PROXY_URL НЕ НАЙДЕНА В RAILWAY!")
            return

        async with AsyncSession() as session:
            while True:
                try:
                    # Весь трафик идет через прокси
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, proxy=PROXY_URL, impersonate="chrome120")
                    
                    # Ищем перерыв (AC÷46) после 1-го периода (нет BC÷)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m and "BC÷" not in m]
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        try:
                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                        except: continue

                        # Фильтр счета (до 1 гола)
                        if (h_score + a_score) <= 1:
                            res = await self.get_stats(session, m_id)
                            
                            # Фильтр активности (броски 11+ или штраф 4+)
                            if res and (res['shots'] >= 11 or res['pen'] >= 4):
                                msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                       f"🎯 Броски: `{res['shots']}` | ⚖️ Штраф: `{res['pen']} мин`\n\n"
                                       f"🔗 [Матч](https://www.flashscore.ru/match/{m_id})")
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                self.sent_cache[m_id] = asyncio.get_event_loop().time()
                                logger.info(f"✅ Сигнал отправлен: {h_team}")
                            
                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
