import asyncio, os, logging, sys, time, datetime
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логов, чтобы ты видел всё в Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyGodEye")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Лиги для мониторинга
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
        self.sent_cache = {} # m_id: (home, away)
        self.stats = {"win": 0, "loss": 0}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_deep_shots(self, session, m_id):
        """Продвинутый парсинг бросков по скрытым тегам"""
        try:
            detail_url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
            res = await session.get(detail_url, headers=self.headers, timeout=12)
            data = res.text
            
            # 1. Попытка найти по тегам SG (Home) и SH (Away) - самые стабильные
            if "SG÷" in data and "SH÷" in data:
                h_s = self._get_val(data, "SG÷")
                a_s = self._get_val(data, "SH÷")
                if h_s.isdigit() and a_s.isdigit():
                    return int(h_s), int(a_s)
            
            # 2. Попытка найти в текстовых блоках (если первый способ не сработал)
            for term in ["Броски в створ", "Shots on Goal"]:
                if term in data:
                    block = data.split(term)[1].split("~")[0]
                    vals = [v.split("÷")[1] for v in block.split("¬") if "÷" in v]
                    if len(vals) >= 2:
                        return int(vals[0]), int(vals[1])
        except Exception as e:
            logger.error(f"Ошибка парсинга бросков для {m_id}: {e}")
        return 0, 0

    async def run(self):
        logger.info("=== v28.2 GOD-EYE ЗАПУЩЕН | Чита 17:20 | Броски починены ===")
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

                            # 1. ПРОВЕРКА ЗАНОСОВ
                            if m_id in self.sent_cache:
                                h2, a2 = self._get_val(m_block, 'BC÷'), self._get_val(m_block, 'BD÷')
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅ **ЗАНОС!**\n🏒 {home} — {away}\nГол во 2-м периоде!")
                                    self.stats["win"] += 1
                                    del self.sent_cache[m_id]
                                    continue
                                if status in ['13', '45']: # Конец 2-го периода
                                    if h2 == "0" and a2 == "0":
                                        await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n🏒 {home} — {away}\n2-й период без голов.")
                                        self.stats["loss"] += 1
                                    del self.sent_cache[m_id]
                                    continue

                            # 2. ПОИСК СИГНАЛОВ (АЛГОРИТМ APEX)
                            if status == '46' and m_id not in self.sent_cache:
                                if self._get_val(m_block, 'BC÷') == "":
                                    score_sum = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if score_sum <= 1:
                                        # Глубокий парсинг бросков
                                        h_s, a_s = await self.get_deep_shots(session, m_id)
                                        total_s = h_s + a_s
                                        
                                        if total_s >= 12: # Наш порог активности
                                            conf = "⭐️ УВЕРЕННЫЙ" if total_s >= 20 or abs(h_s - a_s) >= 8 else "Обычный"
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            text = (
                                                f"🏒 **{home} {gh}:{ga} {away}**\n"
                                                f"🏆 {league_raw}\n\n"
                                                f"📊 Броски (1-й): `{h_s}:{a_s}`\n"
                                                f"💎 Алгоритм: **{conf}**\n\n"
                                                f"🔗 [ОТКРЫТЬ МАТЧ]({link})"
                                            )
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache[m_id] = True
                                            logger.info(f"✅ Сигнал отправлен: {home}-{away} ({h_s}:{a_s})")
                                        else:
                                            logger.info(f"⏳ Пропуск {home}: мало бросков ({total_s})")

                    if len(self.sent_cache) > 200: self.sent_cache.clear()
                except Exception as e: logger.error(f"Критическая ошибка: {e}")
                await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
