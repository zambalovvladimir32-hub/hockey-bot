import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyAutoCheck")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

STAT_LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "АЗИЯ", "ASIA", "ЧЕХИЯ", "ФИНЛЯНДИЯ", "ГЕРМАНИЯ", "ШВЕЙЦАРИЯ"]

class HockeyScanner:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo"}
        self.sent_cache = {} # Храним ID матча и счет 1-го периода

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def run(self):
        logger.info("=== v26.0 AUTO-CHECK ЗАПУЩЕН | Отчеты ВКЛЮЧЕНЫ ===")
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
                            gh = self._get_val(m_block, 'AG÷')
                            ga = self._get_val(m_block, 'AH÷')

                            # --- ЛОГИКА ОТЧЕТОВ (Проверка зашедших ставок) ---
                            if m_id in self.sent_cache:
                                h1, a1 = self.sent_cache[m_id]
                                # Текущий счет 2-го периода
                                h2 = self._get_val(m_block, 'BC÷')
                                a2 = self._get_val(m_block, 'BD÷')
                                
                                # 1. Проверяем ГОЛ во 2-м периоде
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅✅✅ **ЗАНОС!**\n🏒 {home} — {away}\nГол во 2-м периоде забит! 💸")
                                    del self.sent_cache[m_id] # Удаляем из слежки
                                    continue

                                # 2. Проверяем окончание 2-го периода (статус 13 - 3-й период или 45 - перерыв 2-3)
                                if status in ['13', '45']:
                                    if h2 == "0" and a2 == "0":
                                        await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n🏒 {home} — {away}\nВторой период прошел без голов.")
                                    del self.sent_cache[m_id]
                                    continue

                            # --- ЛОГИКА СИГНАЛОВ (Поиск новых матчей) ---
                            if status == '46' and m_id not in self.sent_cache:
                                # Проверяем, что 2-й период еще не начался
                                if self._get_val(m_block, 'BC÷') == "":
                                    curr_score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if curr_score <= 1:
                                        s_h = self._get_val(m_block, 'AS÷')
                                        s_a = self._get_val(m_block, 'AT÷')
                                        shots = f"{s_h}:{s_a}" if s_h.isdigit() else "Нет данных"
                                        
                                        link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                        text = (
                                            f"🏒 **{home} {gh}:{ga} {away}**\n"
                                            f"🏆 {league_raw}\n\n"
                                            f"📊 Броски (1-й): `{shots}`\n"
                                            f"🎯 Ждем гол во 2-м периоде!\n"
                                            f"🔗 [ОТКРЫТЬ MATCH]({link})"
                                        )
                                        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                        # Запоминаем для отчета
                                        self.sent_cache[m_id] = (gh, ga)
                                        logger.info(f"✅ СИГНАЛ: {home}-{away} (Взят на контроль)")

                    # Очистка старого кэша (если игра висит слишком долго)
                    if len(self.sent_cache) > 100: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
