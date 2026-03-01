import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeySniperV31.5")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "ЧЕХИЯ", "ГЕРМАНИЯ", "ФИНЛЯНДИЯ", "ШВЕЙЦАРИЯ", "ШВЕЦИЯ", "АВСТРИЯ"]

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id, h_name, a_name):
        """Пробиваем 404 ошибку через перебор вариантов"""
        st = {"shots": 0, "pen": 0}
        variants = ["_ru-ru_1", "_ru-ru_3", "_en-gb_1", "_ru-ru_0", "_ru-ru_2"]
        
        for v_suffix in variants:
            url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}{v_suffix}"
            try:
                r = await session.get(url, headers=self.headers, timeout=8)
                if r.status_code == 200 and "¬" in r.text:
                    d = r.text
                    # Ищем данные как на видео
                    for tag in ["Удары по воротам", "Вратарь отбивает мяч", "Удары в створ", "SG÷"]:
                        if tag in d:
                            vals = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                            if len(vals) >= 2:
                                st["shots"] = int(vals[0]) + int(vals[1])
                                break
                    for tag in ["ПИМ", "Штрафное время", "Штрафы"]:
                        if tag in d:
                            vals = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                            if len(vals) >= 2:
                                st["pen"] = int(vals[0]) + int(vals[1])
                                break
                    
                    if st["shots"] > 0:
                        logger.info(f"✅ УСПЕХ ({v_suffix}) для {h_name}: Броски={st['shots']}, ПИМ={st['pen']}")
                        return st
            except: continue
        return None

    async def run(self):
        logger.info("=== v31.5 ULTRA-REPAIR ЗАПУЩЕН | Пробиваем 404 ===")
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
                            h_name, a_name = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')

                            if status == '46' and m_id not in self.sent_cache:
                                if self._get_val(m_block, 'BC÷') == "":
                                    score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    if score <= 1:
                                        stats = await self.get_stats(session, m_id, h_name, a_name)
                                        if stats:
                                            if stats["shots"] >= 11 or stats["pen"] >= 4:
                                                label = "🔥 GOLD" if stats["shots"] >= 16 else "💎 СИГНАЛ"
                                                text = (
                                                    f"🏒 **{h_name} {gh}:{ga} {a_name}**\n🏆 {league}\n\n"
                                                    f"📊 **1-й период:**\n🎯 Броски/Сэйвы: `{stats['shots']}`\n⚖️ ПИМ (Штрафы): `{stats['pen']} мин`"
                                                    f"\n\nРейтинг: **{label}**\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)"
                                                )
                                                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                                self.sent_cache[m_id] = f"{h_name} — {a_name}"
                    await asyncio.sleep(40)
                except Exception as e: logger.error(f"Ошибка цикла: {e}"); await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
