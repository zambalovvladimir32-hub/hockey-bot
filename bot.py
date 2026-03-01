import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyUltraStats")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# Оставляем только лиги с хорошей статой
LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "ЧЕХИЯ", "ГЕРМАНИЯ", "ФИНЛЯНДИЯ", "ШВЕЙЦАРИЯ", "ШВЕЦИЯ", "АВСТРИЯ"]

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo", "x-requested-with": "XMLHttpRequest", "Referer": "https://www.flashscore.ru/"}
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id):
        """Парсим именно те параметры, что на видео: Сэйвы, ПИМ, Атаки"""
        st = {"shots": 0, "attacks": 0, "pen": 0}
        has_stats = False
        try:
            url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
            r = await session.get(url, headers=self.headers, timeout=10)
            d = r.text
            
            # 1. Броски (ищем 'Вратарь отбивает' или 'Удары в створ')
            for tag in ["Вратарь отбивает мяч", "Удары в створ", "SG÷"]:
                if tag in d:
                    v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                    if len(v) >= 2:
                        st["shots"] = int(v[0]) + int(v[1])
                        has_stats = True; break

            # 2. Опасные атаки
            if "Опасные атаки" in d:
                v = [x.split("÷")[1] for x in d.split("Опасные атаки")[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                if len(v) >= 2:
                    st["attacks"] = int(v[0]) + int(v[1])
                    has_stats = True

            # 3. Штрафное время (ПИМ как на видео)
            if "ПИМ" in d or "Штрафное время" in d:
                tag = "ПИМ" if "ПИМ" in d else "Штрафное время"
                v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                if len(v) >= 2: st["pen"] = int(v[0]) + int(v[1])

        except: pass
        return st if has_stats else None

    async def run(self):
        logger.info("=== v31.2 ULTRA-STATS ЗАПУЩЕН | Только матчи с цифрами ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200: continue
                    for sec in r.text.split('~ZA÷')[1:]:
                        league = sec.split('¬')[0]
                        if not any(lg.upper() in league.upper() for lg in LEAGUES): continue
                        for m_block in sec.split('~AA÷')[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')

                            # Контроль результата
                            if m_id in self.sent_cache:
                                h2, a2 = self._get_val(m_block, 'BC÷'), self._get_val(m_block, 'BD÷')
                                if (h2.isdigit() and int(h2) > 0) or (a2.isdigit() and int(a2) > 0):
                                    await bot.send_message(CHANNEL_ID, f"✅ **ЗАНОС!**\n{self.sent_cache[m_id]}\nГол во втором!")
                                    del self.sent_cache[m_id]
                                elif status in ['13', '45']:
                                    await bot.send_message(CHANNEL_ID, f"❌ **МИНУС**\n{self.sent_cache[m_id]}\nВторой период 0:0.")
                                    del self.sent_cache[m_id]
                                continue

                            # Фильтр перерыва
                            if status == '46' and m_id not in self.sent_cache:
                                if self._get_val(m_block, 'BC÷') == "":
                                    score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if score <= 1:
                                        st = await self.get_stats(session, m_id)
                                        # КЛЮЧЕВОЕ: Если статы нет вообще - ИГНОРИМ МАТЧ
                                        if st and (st["shots"] >= 11 or st["attacks"] >= 30 or st["pen"] >= 4):
                                            home, away = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')
                                            label = "🔥 GOLD" if (st["shots"] >= 15 and st["pen"] >= 4) else "💎 СИГНАЛ"
                                            text = (
                                                f"🏒 **{home} {gh}:{ga} {away}**\n🏆 {league}\n\n"
                                                f"📊 **Статистика (1-й период):**\n"
                                                f"🎯 Броски/Сэйвы: `{st['shots']}`\n"
                                                f"🚀 Оп. атаки: `{st['attacks'] if st['attacks'] > 0 else '?'}`\n"
                                                f"⚖️ Штрафы (ПИМ): `{st['pen']} мин`"
                                                f"\n\nРейтинг: **{label}**\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)"
                                            )
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache[m_id] = f"{home} — {away}"
                    if len(self.sent_cache) > 200: self.sent_cache.clear()
                except Exception as e: logger.error(f"Error: {e}")
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
