import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.4")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Accept": "*/*",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        # ОЧЕНЬ ВАЖНО: Пауза перед каждым матчем, имитирующая чтение
        await asyncio.sleep(random.uniform(5.5, 9.2))
        
        # Пробуем 3 разных способа достать данные
        endpoints = [f"d_st_{m_id}_ru-ru_1", f"d_st_{m_id}_en-gb_1", f"d_su_{m_id}_ru-ru_1"]
        
        for ep in endpoints:
            try:
                url = f"https://www.flashscore.ru/x/feed/{ep}?t={int(time.time()*1000)}"
                r = await session.get(url, headers=self.headers, timeout=15)
                
                if r.status_code == 200 and "¬" in r.text and "÷" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    
                    # Ищем данные (универсальный поиск)
                    blocks = d.split("¬")
                    for i, b in enumerate(blocks):
                        if "÷" not in b: continue
                        name = b.split("÷")[0]
                        
                        # Броски
                        if any(x in name for x in ["Удары по воротам", "Броски", "SG", "SOG"]):
                            try:
                                v1 = blocks[i+1].split("÷")[1]
                                v2 = blocks[i+2].split("÷")[1]
                                st["shots"] = int(v1) + int(v2)
                            except: pass
                        
                        # Штрафы
                        if any(x in name for x in ["ПИМ", "Штраф", "PM"]):
                            try:
                                v1 = blocks[i+1].split("÷")[1]
                                v2 = blocks[i+2].split("÷")[1]
                                st["pen"] = int(v1) + int(v2)
                            except: pass
                    
                    if st["shots"] > 0 or st["pen"] > 0:
                        return st
            except: continue
        return None

    async def run(self):
        logger.info(f"=== v33.4 STEALTH-ORBITER | Proxy: {'ON'}")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="safari_15_5", proxies=proxies) as session:
            # Сначала заходим на мобильную версию
            await session.get("https://www.flashscore.ru/?m=1", headers=self.headers)
            
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"📡 Перерыв в {len(matches)} играх. Начинаю медленный обход...")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        
                        h = m_block.split('AE÷')[1].split('¬')[0]
                        a = m_block.split('AF÷')[1].split('¬')[0]
                        gh = m_block.split('AG÷')[1].split('¬')[0] if 'AG÷' in m_block else "0"
                        ga = m_block.split('AH÷')[1].split('¬')[0] if 'AH÷' in m_block else "0"
                        
                        if (int(gh) + int(ga)) <= 1:
                            logger.info(f"🐢 Скрытно проверяю: {h} - {a}")
                            stats = await self.get_stats(session, m_id)
                            
                            if stats:
                                if stats["shots"] >= 11 or stats["pen"] >= 4:
                                    msg = (f"🏒 **{h} {gh}:{ga} {a}**\n\n"
                                           f"📊 **1-й период:**\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                           f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = True
                                    logger.info(f"✅ СИГНАЛ: {h}")
                            else:
                                logger.warning(f"📭 {h}: Данные пока не отдают.")
                        
                        # Пауза между матчами, чтобы не триггерить защиту
                        await asyncio.sleep(random.uniform(2, 4))
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка: {e}"); await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
