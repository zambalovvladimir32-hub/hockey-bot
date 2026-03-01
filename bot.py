import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.8")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/",
            "Accept": "*/*"
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        # Имитируем реальную паузу
        await asyncio.sleep(random.uniform(5, 8))
        
        # Пробуем ДВА разных источника данных
        sources = [
            f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1", # Статистика
            f"https://www.flashscore.ru/x/feed/d_su_{m_id}_ru-ru_1"  # Сводка (иногда там есть стата)
        ]
        
        for url in sources:
            try:
                r = await session.get(f"{url}?t={int(time.time()*1000)}", headers=self.headers, timeout=15)
                if r.status_code == 200 and "÷" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    
                    # Ищем любые упоминания бросков или штрафов
                    parts = d.split("¬")
                    for i, p in enumerate(parts):
                        if any(x in p for x in ["Броски", "Удары по воротам", "SOG", "SG"]):
                            try:
                                st["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                            except: pass
                        if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                            try:
                                st["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                            except: pass
                    
                    if st["shots"] > 0 or st["pen"] > 0:
                        return st
            except: continue
        return None

    async def run(self):
        logger.info(f"=== v33.8 THE GHOST ЗАПУЩЕН | Прокси: ISP ===")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="chrome120", proxies=proxies) as session:
            # "Прогрев" через мобильную версию
            await session.get("https://www.flashscore.ru/?m=1", headers=self.headers)
            
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"📡 В перерыве: {len(matches)} игр.")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        
                        h = m_block.split('AE÷')[1].split('¬')[0]
                        a = m_block.split('AF÷')[1].split('¬')[0]
                        
                        logger.info(f"👻 Скрытая проверка: {h} - {a}")
                        stats = await self.get_stats(session, m_id)
                        
                        if stats:
                            if stats["shots"] >= 11 or stats["pen"] >= 4:
                                msg = (f"🏒 **{h} - {a}**\n\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                       f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                self.sent_cache[m_id] = True
                                logger.info(f"✅ УСПЕХ: {h}")
                        else:
                            logger.warning(f"❌ {h}: Статистика недоступна.")
                        
                        await asyncio.sleep(5)
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка: {e}"); await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
