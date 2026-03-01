import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV32.9")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL")
bot = Bot(token=TOKEN)

LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "ЧЕХИЯ", "ГЕРМАНИЯ", "ФИНЛЯНДИЯ", "ШВЕЙЦАРИЯ", "ШВЕЦИЯ", "АВСТРИЯ"]

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/",
            "Accept": "*/*"
        }
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id):
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        # Пробуем 3 эндпоинта: Стандарт, Английский и Событийный
        eps = [f"d_st_{m_id}_ru-ru_1", f"d_st_{m_id}_en-gb_1", f"d_su_{m_id}_ru-ru_1"]
        
        for ep in eps:
            try:
                url = f"https://www.flashscore.ru/x/feed/{ep}?t={int(time.time()*1000)}"
                r = await session.get(url, headers=self.headers, proxies=proxies, timeout=12)
                
                if r.status_code == 200 and "¬" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    # Ищем данные по ключевым словам из видео
                    blocks = d.split("¬")
                    for b in blocks:
                        if "÷" not in b: continue
                        name, val = b.split("÷")[0], b.split("÷")[1]
                        # Броски
                        if any(x in name for x in ["Удары по воротам", "Броски", "SG", "SOG"]):
                            # Пытаемся вытащить сумму из соседних полей
                            try:
                                # В структуре Flashscore значения часто идут после названия тега
                                idx = blocks.index(b)
                                v1 = blocks[idx+1].split("÷")[1]
                                v2 = blocks[idx+2].split("÷")[1]
                                if v1.isdigit() and v2.isdigit():
                                    st["shots"] = int(v1) + int(v2)
                            except: pass
                        # ПИМ
                        if any(x in name for x in ["ПИМ", "Штрафное время", "PM"]):
                            try:
                                idx = blocks.index(b)
                                v1 = blocks[idx+1].split("÷")[1]
                                v2 = blocks[idx+2].split("÷")[1]
                                if v1.isdigit() and v2.isdigit():
                                    st["pen"] = int(v1) + int(v2)
                            except: pass
                    
                    if st["shots"] > 0 or st["pen"] > 0: return st
            except: continue
        return None

    async def run(self):
        logger.info(f"=== v32.9 FORCE-SCAN | Proxy: {'ON' if PROXY_URL else 'OFF'} ===")
        async with AsyncSession(impersonate="safari_15_5") as session:
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    matches = r.text.split('~AA÷')[1:]
                    logger.info(f"📡 Мониторинг: {len(matches)} игр.")
                    
                    for m_block in matches:
                        if self._get_val(m_block, 'AC÷') == '46': # ПЕРЕРЫВ
                            h, a = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')
                            if m_id := self._get_val(m_block, 'AA÷'):
                                if m_id not in self.sent_cache:
                                    gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')
                                    score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    
                                    if score <= 1:
                                        logger.info(f"⚡️ Принудительный скан: {h} - {a}")
                                        stats = await self.get_stats(session, m_id)
                                        if stats and (stats["shots"] >= 11 or stats["pen"] >= 4):
                                            msg = (f"🏒 **{h} {gh}:{ga} {a}**\n\n"
                                                   f"📊 **1-й период:**\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                                   f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                            await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                            self.sent_cache[m_id] = True
                                            logger.info(f"🚀 СИГНАЛ: {h}")
                                        elif stats:
                                            logger.info(f"📉 Слабая активность {h}: {stats}")
                                        else:
                                            logger.warning(f"📭 Данные не пробиты для {h}")
                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Error: {e}"); await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
