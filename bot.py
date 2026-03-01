import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Логирование для Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeySniper")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Твой список лиг
STAT_LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "АЗИЯ", "ASIA", "ЧЕХИЯ", "ФИНЛЯНДИЯ", "ГЕРМАНИЯ", "ШВЕЙЦАРИЯ", "АВСТРИЯ"]

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
        logger.info("=== v23.1 ЗАПУЩЕН | ФИЛЬТР: СЧЕТ 0:0, 1:0, 0:1 ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        await asyncio.sleep(20); continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league_raw = sec.split('¬')[0]
                        if not any(lg.upper() in league_raw.upper() for lg in STAT_LEAGUES):
                            continue
                            
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            home = self._get_val(m_block, 'AE÷')
                            away = self._get_val(m_block, 'AF÷')
                            
                            # Текущий счет (для логов ожидания)
                            gh = self._get_val(m_block, 'AG÷')
                            ga = self._get_val(m_block, 'AH÷')
                            
                            # Если идет 1-й период (код 11 или 12)
                            if status in ['11', '12']:
                                # Пишем в логи только если счет подходит под наш фильтр
                                if (gh == "0" or gh == "1") and (ga == "0" or ga == "1") and (int(gh or 0) + int(ga or 0) <= 1):
                                    logger.info(f"⏳ Мониторю: {home} {gh}:{ga} {away} (Жду перерыв)")

                            # Если ПЕРЕРЫВ (код 46)
                            if status == '46':
                                h1 = self._get_val(m_block, 'BA÷') or gh
                                a1 = self._get_val(m_block, 'BB÷') or ga
                                
                                if h1 != "" and a1 != "":
                                    total_goals = int(h1) + int(a1)
                                    
                                    # --- ЖЕСТКИЙ ФИЛЬТР: МАКСИМУМ 1 ГОЛ В 1-М ПЕРИОДЕ ---
                                    if total_goals <= 1:
                                        if m_id not in self.sent_cache:
                                            # Проверяем броски
                                            s_h = self._get_val(m_block, 'AS÷')
                                            s_a = self._get_val(m_block, 'AT÷')
                                            shots_info = f"{s_h}:{s_a}" if s_h.isdigit() else "Нет данных"
                                            
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            text = (
                                                f"🏒 **{home} {h1}:{a1} {away}**\n"
                                                f"🏆 {league_raw}\n\n"
                                                f"📊 Броски (1-й): `{shots_info}`\n"
                                                f"🎯 Анализ: ТБ 0.5 во 2-м периоде\n\n"
                                                f"🔗 [ОТКРЫТЬ MATCH]({link})"
                                            )
                                            
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache.add(m_id)
                                            logger.info(f"✅ СИГНАЛ ОТПРАВЛЕН: {home}-{away} ({h1}:{a1})")

                    if len(self.sent_cache) > 1000: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка парсинга: {e}")
                
                await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
