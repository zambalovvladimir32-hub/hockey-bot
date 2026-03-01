import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyTurbo")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

STAT_LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "АЗИЯ", "ASIA", "ЧЕХИЯ", "ФИНЛЯНДИЯ", "ГЕРМАНИЯ"]

class HockeyScanner:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo"}
        self.sent_cache = set()

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def run(self):
        logger.info("=== v23.0 TURBO-VISION ЗАПУЩЕН ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200: continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league_raw = sec.split('¬')[0]
                        if not any(lg.upper() in league_raw.upper() for lg in STAT_LEAGUES): continue
                            
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            home = self._get_val(m_block, 'AE÷')
                            away = self._get_val(m_block, 'AF÷')
                            
                            # ЛОГ ДЛЯ ТЕБЯ: Видит ли он игру вообще
                            if status in ['11', '12']: # Идет 1-й период
                                logger.info(f"⏳ Жду перерыва: {home}-{away} ({self._get_val(m_block, 'AG÷')}:{self._get_val(m_block, 'AH÷')})")

                            if status == '46': # ПЕРЕРЫВ
                                h1 = self._get_val(m_block, 'BA÷') or self._get_val(m_block, 'AG÷')
                                a1 = self._get_val(m_block, 'BB÷') or self._get_val(m_block, 'AH÷')
                                
                                if h1 != "" and a1 != "":
                                    total_goals = int(h1) + int(a1)
                                    # Пропускаем только если совсем «решето» (4 и более голов)
                                    if total_goals <= 3:
                                        s_h = self._get_val(m_block, 'AS÷')
                                        s_a = self._get_val(m_block, 'AT÷')
                                        
                                        # Если бросков нет в фиде, пишем "???"
                                        shots_info = f"{s_h}:{s_a}" if s_h.isdigit() else "Нет данных"
                                        
                                        if m_id not in self.sent_cache:
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            text = (
                                                f"🏒 **{home} {h1}:{a1} {away}**\n"
                                                f"🏆 {league_raw}\n"
                                                f"📊 Броски (1-й): `{shots_info}`\n"
                                                f"🔗 [Открыть матч]({link})"
                                            )
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                                            self.sent_cache.add(m_id)
                                            logger.info(f"✅ СИГНАЛ ОТПРАВЛЕН: {home}-{away}")

                    if len(self.sent_cache) > 500: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
