import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyMaxLeagues")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# --- МАКСИМАЛЬНО РАСШИРЕННЫЙ СПИСОК ЛИГ ---
ALLOWED_LEAGUES = [
    # Россия и СНГ
    "КХЛ", "ВХЛ", "МХЛ", "НМХЛ", "БЕЛАРУСЬ", "КАЗАХСТАН",
    # Северная Америка
    "НХЛ", "NHL", "АХЛ", "AHL", "ECHL", "OHL", "WHL", "QMJHL", "NCAA",
    # Финляндия
    "ФИНЛЯНДИЯ: ЛИГА", "ФИНЛЯНДИЯ: МЕСТИС", "ФИНЛЯНДИЯ: СУОМИ-СЕРИЯ",
    # Швеция
    "ШВЕЦИЯ: ШВЕЦКАЯ ХОККЕЙНАЯ ЛИГА", "ШВЕЦИЯ: АЛЛСВЕНСКАН", "ШВЕЦИЯ: ДИВИЗИОН 1",
    # Германия
    "ГЕРМАНИЯ: ДЕЛ", "ГЕРМАНИЯ: ДЕЛ2", "ГЕРМАНИЯ: ОБЕРЛИГА",
    # Чехия
    "ЧЕХИЯ: ЭКСТРАЛИГА", "ЧЕХИЯ: ПЕРВАЯ ЛИГА", "ЧЕХИЯ: ВТОРАЯ ЛИГА",
    # Швейцария
    "ШВЕЙЦАРИЯ: НАЦИОНАЛЬНАЯ ЛИГА", "ШВЕЙЦАРИЯ: СВИСС ЛИГА",
    # Остальная Европа
    "АВСТРИЯ: ИСЕХОККЕЙ", "АВСТРИЯ: АЛЬПИЙСКАЯ", "НОРВЕГИЯ", "ДАНИЯ", 
    "СЛОВАКИЯ", "ПОЛЬША", "ФРАНЦИЯ", "ВЕЛИКОБРИТАНИЯ", "ИТАЛИЯ", "ВЕНГРИЯ",
    # Азия и Мир
    "АЗИАТСКАЯ ЛИГА", "АЛЬПИЙСКАЯ ЛИГА", "ЧЕМПИОНОВ", "ЕВРОТУР"
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

    def is_league_allowed(self, league_name):
        ln = league_name.upper()
        # Проверяем, есть ли хоть одно ключевое слово из списка в названии лиги
        return any(allowed.upper() in ln for allowed in ALLOWED_LEAGUES)

    async def run(self):
        logger.info(f"=== v16.0 STARTED | Расширенный фильтр: {len(ALLOWED_LEAGUES)} направлений ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        await asyncio.sleep(20); continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league_raw = sec.split('¬')[0]
                        
                        # Фильтр по лигам
                        if not self.is_league_allowed(league_raw):
                            continue
                            
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            
                            # Наш рабочий код перерыва 1-2
                            if status == '46':
                                h1 = self._get_val(m_block, 'BA÷')
                                a1 = self._get_val(m_block, 'BB÷')
                                
                                # Запасной забор счета, если BA/BB еще пусты
                                if h1 == "" or a1 == "":
                                    h1 = self._get_val(m_block, 'AG÷')
                                    a1 = self._get_val(m_block, 'AH÷')

                                if h1 != "" and a1 != "":
                                    try:
                                        score = (int(h1), int(a1))
                                        # Условие: Гол во 2-м периоде (счет 0:0, 1:0, 0:1)
                                        if score in [(0, 0), (1, 0), (0, 1)]:
                                            if m_id not in self.sent_cache:
                                                home = self._get_val(m_block, 'AE÷')
                                                away = self._get_val(m_block, 'AF÷')
                                                link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                                
                                                text = (
                                                    f"🧨 **ГОЛ ВО 2-М ПЕРИОДЕ? (Лига+)**\n\n"
                                                    f"🏒 {home} **{h1}:{a1}** {away}\n"
                                                    f"🏆 {league_raw}\n\n"
                                                    f"📊 Счет после 1-го: `{h1}:{a1}`\n"
                                                    f"🔗 [АНАЛИЗ МАТЧА]({link})"
                                                )
                                                
                                                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                                self.sent_cache.add(m_id)
                                                logger.info(f"✅ СИГНАЛ: {league_raw} | {home}-{away}")
                                    except ValueError:
                                        continue

                    if len(self.sent_cache) > 1000: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
