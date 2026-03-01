import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyDeepStat")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

STAT_LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "АЗИЯ", "ASIA", "ЧЕХИЯ", "ФИНЛЯНДИЯ", "ГЕРМАНИЯ", "ШВЕЙЦАРИЯ"]

class HockeyScanner:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest"
        }
        self.sent_cache = {} # m_id: (home, away)

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_deep_shots(self, session, m_id):
        """Запрашивает детальную статистику матча, если в общем списке пусто"""
        try:
            # Ссылка на детальную статистику (v_4_1 - это блок статы)
            detail_url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
            res = await session.get(detail_url, headers=self.headers, timeout=10)
            if "Броски в створ" in res.text:
                # Парсим броски из детальной таблицы
                parts = res.text.split("Броски в створ")[1].split("~")
                val = parts[0].split("¬")
                # Значения бросков обычно в тегах SG (Home) и SH (Away)
                h_shots = val[1].split("÷")[1]
                a_shots = val[2].split("÷")[1]
                return f"{h_shots}:{a_shots}"
        except:
            pass
        return "Нет данных"

    async def run(self):
        logger.info("=== v26.3 DEEP-STAT ЗАПУЩЕН | Броски через Detail-API ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
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
                            gh = self._get_val(m_block, 'AG÷')
                            ga = self._get_val(m_block, 'AH÷')

                            # 1. ОТЧЕТЫ О ЗАНОСАХ
                            if m_id in self.sent_cache:
                                h2 = self._get_val(m_block, 'BC÷')
                                a2 = self._get_val(m_block, 'BD÷')
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅ **ЗАНОС!**\n🏒 {home} — {away}\nГол во 2-м периоде! 🚨")
                                    del self.sent_cache[m_id]
                                    continue
                                if status in ['13', '45']:
                                    if h2 == "0" and a2 == "0":
                                        await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n🏒 {home} — {away}\n2-й период без голов.")
                                    del self.sent_cache[m_id]
                                    continue

                            # 2. НОВЫЕ СИГНАЛЫ (Только 0 или 1 гол)
                            if status == '46' and m_id not in self.sent_cache:
                                if self._get_val(m_block, 'BC÷') == "":
                                    score_sum = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if score_sum <= 1:
                                        # Сначала смотрим в общем списке
                                        sh = self._get_val(m_block, 'AS÷')
                                        sa = self._get_val(m_block, 'AT÷')
                                        
                                        if sh.isdigit():
                                            shots_final = f"{sh}:{sa}"
                                        else:
                                            # Если в общем списке пусто — идем вглубь
                                            logger.info(f"🔍 Запрашиваю глубокую стату для {home}")
                                            shots_final = await self.get_deep_shots(session, m_id)

                                        link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                        text = (
                                            f"🏒 **{home} {gh}:{ga} {away}**\n"
                                            f"🏆 {league_raw}\n\n"
                                            f"📊 Броски (1-й): `{shots_final}`\n"
                                            f"🎯 Ждем гол во 2-м периоде!\n\n"
                                            f"🔗 [ОТКРЫТЬ МАТЧ]({link})"
                                        )
                                        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                        self.sent_cache[m_id] = (home, away)

                    if len(self.sent_cache) > 200: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
