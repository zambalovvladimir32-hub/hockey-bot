import asyncio, os, logging
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyDiagnostic_v37.6")

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
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        try:
            r = await session.get(url, headers=self.headers, impersonate="chrome120", timeout=10)
            if "¬" in r.text:
                parts = r.text.split("¬")
                st = {"shots": 0, "pen": 0}
                for i, p in enumerate(parts):
                    if any(x in p for x in ["Броски", "Удары", "SOG"]):
                        st["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                    if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                        st["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                return st
        except Exception as e:
            logger.error(f"Ошибка при парсинге статы {m_id}: {e}")
        return None

    async def run(self):
        logger.info("🛠 v37.6 РЕЖИМ ДИАГНОСТИКИ ЗАПУЩЕН")
        async with AsyncSession() as session:
            while True:
                try:
                    r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", headers=self.headers, impersonate="chrome120")
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    
                    if matches:
                        logger.info(f"🔎 Найдено {len(matches)} игр в статусе 'Перерыв'")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue

                        if "BC÷" in m_block: 
                            continue # Пропускаем 2-й перерыв

                        h_team = m_block.split('AE÷')[1].split('¬')[0]
                        a_team = m_block.split('AF÷')[1].split('¬')[0]
                        
                        try:
                            h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                            a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                            total_goals = h_score + a_score
                        except: continue

                        # Идем за статистикой, ТОЛЬКО если счет 0:0, 1:0 или 0:1
                        if total_goals <= 1:
                            stats = await self.get_stats(session, m_id)
                            
                            # === ВОТ ОНА, ДИАГНОСТИКА ===
                            if stats:
                                logger.info(f"📊 СТАТА ИЗ ФЛЕШСКОРА -> {h_team} vs {a_team} | Счет: {h_score}:{a_score} | Броски: {stats['shots']} | ПИМ: {stats['pen']}")
                                
                                # А теперь уже проверяем твои лимиты для отправки в канал
                                if stats["shots"] >= 11 or stats["pen"] >= 4:
                                    text = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                           f"⏱ *Перерыв после 1-го периода*\n\n"
                                           f"🎯 Броски: `{stats['shots']}`\n"
                                           f"⚖️ Штраф: `{stats['pen']} мин`\n\n"
                                           f"🔗 [Открыть матч](https://www.flashscore.ru/match/{m_id})")
                                    
                                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                                    logger.info(f"✅ СИГНАЛ УЛЕТЕЛ В КАНАЛ!")
                                    self.sent_cache[m_id] = asyncio.get_event_loop().time()
                            else:
                                logger.warning(f"⚠️ Флешскор не отдал стату для {h_team} vs {a_team}")

                    now = asyncio.get_event_loop().time()
                    self.sent_cache = {k: v for k, v in self.sent_cache.items() if now - v < 7200}
                    await asyncio.sleep(45) 
                except Exception as e:
                    logger.error(f"Критическая ошибка: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeyLogic().run())
