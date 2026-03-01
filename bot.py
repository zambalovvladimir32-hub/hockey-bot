import asyncio, os, logging, sys, time, datetime
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyUnlocked")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

STAT_LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "АЗИЯ", "ASIA", "ЧЕХИЯ", "ФИНЛЯНДИЯ", "ГЕРМАНИЯ", "ШВЕЙЦАРИЯ", "АВСТРИЯ"]

class HockeyScanner:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = {} 
        self.stats_daily = {"win": 0, "loss": 0}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats_with_retry(self, session, m_id, retries=2):
        for i in range(retries):
            try:
                detail_url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
                res = await session.get(detail_url, headers=self.headers, timeout=10)
                data = res.text
                
                if "SG÷" in data and "SH÷" in data:
                    h, a = self._get_val(data, "SG÷"), self._get_val(data, "SH÷")
                    if h.isdigit(): return "Броски", int(h), int(a)
                
                if "Опасные атаки" in data:
                    parts = data.split("Опасные атаки")[1].split("~")[0]
                    vals = [v.split("÷")[1] for v in parts.split("¬") if "÷" in v and v.split("÷")[1].isdigit()]
                    if len(vals) >= 2: return "Оп. атаки", int(vals[0]), int(vals[1])
            except: pass
            if i < retries - 1: await asyncio.sleep(3)
        return "Нет данных", 0, 0

    async def run(self):
        logger.info(f"=== v29.1 UNLOCKED ЗАПУЩЕН | Все лиги открыты ===")
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
                            home, away = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')
                            gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')

                            # 1. ОТЧЕТЫ О ЗАНОСАХ
                            if m_id in self.sent_cache:
                                h2, a2 = self._get_val(m_block, 'BC÷'), self._get_val(m_block, 'BD÷')
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅ **ЗАНОС!**\n🏒 {home} — {away}\nГол во 2-м периоде!")
                                    del self.sent_cache[m_id]
                                    continue
                                if status in ['13', '45']:
                                    if h2 == "0" and a2 == "0":
                                        await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n🏒 {home} — {away}\n2-й период 0:0.")
                                    del self.sent_cache[m_id]
                                    continue

                            # 2. ФИЛЬТР МАТЧЕЙ (ТЕПЕРЬ ПРОПУСКАЕТ ВСЕ ЛИГИ)
                            if status == '46' and m_id not in self.sent_cache:
                                if self._get_val(m_block, 'BC÷') == "":
                                    score_sum = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if score_sum <= 1:
                                        st_type, hv, av = await self.get_stats_with_retry(session, m_id)
                                        is_mhl = "МХЛ" in league_raw.upper()
                                        
                                        # Базовые настройки
                                        should_send = True
                                        label = "Обычный"
                                        total = hv + av if isinstance(hv, int) else 0

                                        # Оценка статы, если она есть
                                        if st_type == "Броски":
                                            if total < 10 and not is_mhl: should_send = False # Отсекаем только совсем мертвые матчи < 10 бросков
                                            elif total >= 20 or abs(hv - av) >= 8: label = "⭐️ УВЕРЕННЫЙ"
                                        elif st_type == "Оп. атаки":
                                            if total >= 35: label = "⚡️ ПО АТАКАМ"
                                        elif st_type == "Нет данных":
                                            # Если статы нет, шлем всё равно, но с пометкой
                                            label = "⚠️ БЕЗ СТАТЫ"
                                            st_type, hv, av = "Данные", "?", "?"
                                            if is_mhl: label = "🐣 МХЛ (БЕЗ СТАТЫ)"

                                        if should_send:
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            text = (
                                                f"🏒 **{home} {gh}:{ga} {away}**\n"
                                                f"🏆 {league_raw}\n\n"
                                                f"📊 {st_type}: `{hv}:{av}`\n"
                                                f"💎 Сигнал: **{label}**\n"
                                                f"🎯 Ждем гол во 2-м!\n\n"
                                                f"🔗 [ОТКРЫТЬ МАТЧ]({link})"
                                            )
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache[m_id] = True
                                            logger.info(f"Отправлено: {home}-{away}")

                    if len(self.sent_cache) > 250: self.sent_cache.clear()
                except Exception as e: logger.error(f"Ошибка: {e}")
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
