import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.5")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "com.flashscore.ru.mobile", # Маскировка под приложение
            "Referer": "https://www.flashscore.ru/",
            "Accept": "*/*"
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        # ОЧЕНЬ ВАЖНО: Длинная пауза перед каждым запросом статы
        delay = random.uniform(7.0, 12.0)
        logger.info(f"⏳ Жду {delay:.1f} сек перед проверкой {m_id}...")
        await asyncio.sleep(delay)
        
        for ep in [f"d_st_{m_id}_ru-ru_1", f"d_st_{m_id}_en-gb_1"]:
            try:
                url = f"https://www.flashscore.ru/x/feed/{ep}?t={int(time.time()*1000)}"
                r = await session.get(url, headers=self.headers, timeout=15)
                
                if r.status_code == 200 and "¬" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    # Универсальный парсинг
                    for tag in ["Удары по воротам", "Броски", "SG÷", "SOG÷"]:
                        if tag in d:
                            v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                            if len(v) >= 2: st["shots"] = int(v[0]) + int(v[1]); break
                    for tag in ["ПИМ", "Штрафы", "Штрафное время", "PM÷"]:
                        if tag in d:
                            v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                            if len(v) >= 2: st["pen"] = int(v[0]) + int(v[1]); break
                    
                    if st["shots"] > 0 or st["pen"] > 0: return st
            except: continue
        return None

    async def run(self):
        logger.info(f"=== v33.5 THE GENTLEMAN ЗАПУЩЕН | Прокси: ДА ===")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            # Прогрев Cookie
            await session.get("https://www.flashscore.ru/", headers=self.headers)
            
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers)
                    # Фильтруем только матчи в ПЕРЕРЫВЕ (код 46)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"📡 Вижу {len(matches)} игр в перерыве.")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        
                        h = m_block.split('AE÷')[1].split('¬')[0]
                        a = m_block.split('AF÷')[1].split('¬')[0]
                        gh = m_block.split('AG÷')[1].split('¬')[0] if 'AG÷' in m_block else "0"
                        ga = m_block.split('AH÷')[1].split('¬')[0] if 'AH÷' in m_block else "0"
                        
                        if (int(gh) + int(ga)) <= 1:
                            logger.info(f"🔦 Медленный анализ: {h} - {a}")
                            stats = await self.get_stats(session, m_id)
                            
                            if stats:
                                if stats["shots"] >= 11 or stats["pen"] >= 4:
                                    msg = (f"🏒 **{h} {gh}:{ga} {a}**\n\n📊 **1-й период:**\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                           f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = True
                                    logger.info(f"🚀 СИГНАЛ: {h}")
                                else:
                                    logger.info(f"📉 Слабо ({h}): {stats}")
                            else:
                                logger.warning(f"📭 {h}: Данные скрыты.")
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка: {e}"); await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
