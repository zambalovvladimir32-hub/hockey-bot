import asyncio, os, logging, sys, time, datetime
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyMhlStrike")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

STAT_LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "АЗИЯ", "ASIA", "ЧЕХИЯ", "ФИНЛЯНДИЯ", "ГЕРМАНИЯ", "ШВЕЙЦАРИЯ"]

class HockeyScanner:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo", "x-requested-with": "XMLHttpRequest"}
        self.sent_cache = {} 
        self.stats = {"win": 0, "loss": 0}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id):
        """Пытаемся достать хоть какую-то статистику (Броски или Опасные атаки)"""
        try:
            detail_url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
            res = await session.get(detail_url, headers=self.headers, timeout=10)
            data = res.text
            
            # 1. Ищем броски в створ (SG/SH)
            if "SG÷" in data:
                h = self._get_val(data, "SG÷")
                a = self._get_val(data, "SH÷")
                if h.isdigit(): return "Броски", int(h), int(a)
            
            # 2. Если бросков нет, ищем Опасные атаки (DA/DB или аналоги)
            if "Опасные атаки" in data or "Dangerous Attacks" in data:
                # В API Flashscore они часто идут после заголовка Опасные атаки
                parts = data.split("Опасные атаки")[1].split("~")[0]
                vals = [v.split("÷")[1] for v in parts.split("¬") if "÷" in v and v.split("÷")[1].isdigit()]
                if len(vals) >= 2:
                    return "Оп. атаки", int(vals[0]), int(vals[1])
        except: pass
        return "Нет данных", 0, 0

    async def run(self):
        logger.info("=== v28.4 MHL-STRIKE ЗАПУЩЕН | Чита 17:25 ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200: continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league_raw = sec.split('¬')[0]
                        is_mhl = "МХЛ" in league_raw.upper()
                        if not any(lg.upper() in league_raw.upper() for lg in STAT_LEAGUES): continue
                            
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            home, away = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')
                            gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')

                            # КОНТРОЛЬ ЗАНОСОВ
                            if m_id in self.sent_cache:
                                h2, a2 = self._get_val(m_block, 'BC÷'), self._get_val(m_block, 'BD÷')
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅ **ЗАНОС!**\n🏒 {home} — {away}\nГол во втором!")
                                    self.stats["win"] += 1
                                    del self.sent_cache[m_id]
                                    continue
                                if status in ['13', '45']:
                                    if h2 == "0" and a2 == "0":
                                        await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n🏒 {home} — {away}\n2-й период без голов.")
                                        self.stats["loss"] += 1
                                    del self.sent_cache[m_id]
                                    continue

                            # НОВЫЙ АЛГОРИТМ С ПОДДЕРЖКОЙ МХЛ
                            if status == '46' and m_id not in self.sent_cache:
                                if self._get_val(m_block, 'BC÷') == "":
                                    score_sum = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if score_sum <= 1:
                                        st_type, h_v, a_v = await self.get_stats(session, m_id)
                                        total_v = h_v + a_v
                                        
                                        # ЛОГИКА ОТПРАВКИ:
                                        # 1. Если есть стата и она ок
                                        # 2. ИЛИ если это МХЛ (шлем даже без статы, т.к. там ее часто нет)
                                        should_send = False
                                        conf = "Обычный"
                                        
                                        if st_type == "Броски" and total_v >= 12:
                                            should_send = True
                                            if total_v >= 19: conf = "⭐️ УВЕРЕННЫЙ"
                                        elif st_type == "Оп. атаки" and total_v >= 35:
                                            should_send = True
                                            conf = "⚡️ ПО АТАКАМ"
                                        elif is_mhl: # Для МХЛ делаем исключение
                                            should_send = True
                                            conf = "🐣 МХЛ (БЕЗ СТАТЫ)"
                                            st_type, h_v, a_v = "Данные", "?", "?"

                                        if should_send:
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            text = (
                                                f"🏒 **{home} {gh}:{ga} {away}**\n"
                                                f"🏆 {league_raw}\n\n"
                                                f"📊 {st_type}: `{h_v}:{a_v}`\n"
                                                f"💎 Алгоритм: **{conf}**\n"
                                                f"🎯 Ждем гол во 2-м!\n\n"
                                                f"🔗 [ОТКРЫТЬ МАТЧ]({link})"
                                            )
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache[m_id] = True

                    if len(self.sent_cache) > 200: self.sent_cache.clear()
                except Exception as e: logger.error(f"Error: {e}")
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
