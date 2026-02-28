import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("Hockey11Plus")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Расширенный список лиг
ALLOWED_LEAGUES = [
    "КХЛ", "ВХЛ", "МХЛ", "НХЛ", "NHL", "АХЛ", "AHL", "ECHL", "OHL", "WHL", "QMJHL",
    "ФИНЛЯНДИЯ", "ШВЕЦИЯ", "ГЕРМАНИЯ", "ЧЕХИЯ", "ШВЕЙЦАРИЯ", "АВСТРИЯ", "НОРВЕГИЯ",
    "ДАНИЯ", "СЛОВАКИЯ", "ПОЛЬША", "БЕЛАРУСЬ", "КАЗАХСТАН", "ФРАНЦИЯ", "ИТАЛИЯ"
]

class HockeyScanner:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = set()

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def run(self):
        logger.info("=== СТАРТ v18.0 | ПОРОГ БРОСКОВ: 11+ ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        await asyncio.sleep(20); continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league_raw = sec.split('¬')[0]
                        if not any(lg.upper() in league_raw.upper() for lg in ALLOWED_LEAGUES):
                            continue
                            
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            
                            # Проверяем перерыв 1-2 (Код 46)
                            if status == '46':
                                h1 = self._get_val(m_block, 'BA÷')
                                a1 = self._get_val(m_block, 'BB÷')
                                
                                if h1 == "" or a1 == "":
                                    h1, a1 = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')

                                if h1 != "" and a1 != "":
                                    score = (int(h1), int(a1))
                                    # Наша база: 0:0, 1:0, 0:1
                                    if score in [(0, 0), (1, 0), (0, 1)]:
                                        
                                        # Броски в створ (AS - хозяева, AT - гости)
                                        s_h = self._get_val(m_block, 'AS÷') 
                                        s_a = self._get_val(m_block, 'AT÷')
                                        
                                        total_shots = (int(s_h) if s_h.isdigit() else 0) + (int(s_a) if s_a.isdigit() else 0)

                                        # ФИЛЬТР: От 11 бросков
                                        if total_shots >= 11:
                                            if m_id not in self.sent_cache:
                                                home = self._get_val(m_block, 'AE÷')
                                                away = self._get_val(m_block, 'AF÷')
                                                link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                                
                                                # Визуальный индикатор
                                                if total_shots >= 18: status_icon = "🔥 ОПАСНО"
                                                elif total_shots >= 14: status_icon = "⚡️ АКТИВНО"
                                                else: status_icon = "🏒 НОРМА"

                                                text = (
                                                    f"🧨 **АЛГОРИТМ 1-Б (11+)**\n\n"
                                                    f"🏒 {home} **{h1}:{a1}** {away}\n"
                                                    f"🏆 {league_raw}\n\n"
                                                    f"📊 Броски в створ: `{total_shots}`\n"
                                                    f"Ранг: {status_icon}\n\n"
                                                    f"⏱ **Ждем гол до 30-й минуты!**\n"
                                                    f"🔗 [АНАЛИЗ МАТЧА]({link})"
                                                )
                                                
                                                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                                self.sent_cache.add(m_id)
                                                logger.info(f"✅ ОТПРАВЛЕНО: {home}-{away} ({total_shots} бр.)")
                                        else:
                                            if m_id not in self.sent_cache:
                                                logger.info(f"⏭ Мало бросков ({total_shots}): {home}-{away}")

                    if len(self.sent_cache) > 1000: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
