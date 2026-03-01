import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.6")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty"
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        # 1. Имитируем "заход" в матч перед запросом статы
        try:
            await session.get(f"https://www.flashscore.ru/match/{m_id}/", headers=self.headers, timeout=10)
            await asyncio.sleep(random.uniform(3, 5))
        except: pass

        # 2. Пробуем получить статику
        headers = self.headers.copy()
        headers["Referer"] = f"https://www.flashscore.ru/match/{m_id}/#/match-summary/match-statistics/0"
        
        # Проверяем 2 эндпоинта (основной и резервный)
        for ep in [f"d_st_{m_id}_ru-ru_1", f"d_su_{m_id}_ru-ru_1"]:
            try:
                url = f"https://www.flashscore.ru/x/feed/{ep}?t={int(time.time()*1000)}"
                r = await session.get(url, headers=headers, timeout=12)
                
                if r.status_code == 200 and "¬" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    # Парсинг (улучшенный поиск)
                    for block in d.split("¬"):
                        if "÷" not in block: continue
                        k, v_all = block.split("÷")[0], block.split("÷")[1:]
                        if any(x in k for x in ["Удары", "Броски", "SG", "SOG"]):
                            try:
                                idx = d.find(block)
                                sub = d[idx:].split("¬")
                                st["shots"] = int(sub[1].split("÷")[1]) + int(sub[2].split("÷")[1])
                            except: pass
                        if any(x in k for x in ["ПИМ", "Штраф", "PM"]):
                            try:
                                idx = d.find(block)
                                sub = d[idx:].split("¬")
                                st["pen"] = int(sub[1].split("÷")[1]) + int(sub[2].split("÷")[1])
                            except: pass
                    if st["shots"] > 0 or st["pen"] > 0: return st
            except: continue
        return None

    async def run(self):
        logger.info(f"=== v33.6 CYBER-SURF ЗАПУЩЕН ===")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="chrome120", proxies=proxies) as session:
            # Начальный "прогрев"
            await session.get("https://www.flashscore.ru/", headers=self.headers)
            
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"📡 Перерыв в {len(matches)} играх. Проверяю по очереди...")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        
                        h, a = m_block.split('AE÷')[1].split('¬')[0], m_block.split('AF÷')[1].split('¬')[0]
                        gh = m_block.split('AG÷')[1].split('¬')[0] if 'AG÷' in m_block else "0"
                        ga = m_block.split('AH÷')[1].split('¬')[0] if 'AH÷' in m_block else "0"
                        
                        if (int(gh) + int(ga)) <= 1:
                            logger.info(f"🛰 Глубокий анализ: {h} - {a}")
                            stats = await self.get_stats(session, m_id)
                            
                            if stats:
                                if stats["shots"] >= 11 or stats["pen"] >= 4:
                                    msg = (f"🏒 **{h} {gh}:{ga} {a}**\n\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                           f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = True
                                    logger.info(f"✅ СИГНАЛ: {h}")
                                else:
                                    logger.info(f"📉 Мало ({h}): {stats}")
                            else:
                                logger.warning(f"📭 {h}: Данные скрыты.")
                        
                        await asyncio.sleep(random.uniform(4, 7)) # Пауза между матчами
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка: {e}"); await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
