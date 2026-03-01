import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV34.0")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        self.url_feed = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.sent_cache = {}

    async def get_stats_clean(self, session, m_id):
        # Имитируем "задумчивость" человека перед открытием статы
        await asyncio.sleep(random.uniform(6, 10))
        
        # Секретный заголовок x-fsign — Flashscore часто меняет его
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": f"https://www.flashscore.ru/match/{m_id}/",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }

        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1?t={int(time.time()*1000)}"
        try:
            # Используем impersonate="chrome120" для обхода TLS-проверок Cloudflare/Akamai
            r = await session.get(url, headers=headers, timeout=20)
            
            if r.status_code == 200 and "¬" in r.text:
                d = r.text
                st = {"shots": 0, "pen": 0}
                parts = d.split("¬")
                for i, p in enumerate(parts):
                    if any(x in p for x in ["Удары по воротам", "Броски", "SOG", "SG"]):
                        try:
                            st["shots"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        except: pass
                    if any(x in p for x in ["ПИМ", "Штраф", "PM"]):
                        try:
                            st["pen"] = int(parts[i+1].split("÷")[1]) + int(parts[i+2].split("÷")[1])
                        except: pass
                
                if st["shots"] > 0 or st["pen"] > 0: return st
        except Exception as e:
            logger.error(f"Ошибка на {m_id}: {e}")
        return None

    async def run(self):
        logger.info(f"=== v34.0 THE UNTOUCHABLE | Proxy: ISP ===")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="chrome120", proxies=proxies) as session:
            # Обязательный первый заход на главную для кук
            await session.get("https://www.flashscore.ru/", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})
            
            while True:
                try:
                    r = await session.get(f"{self.url_feed}?t={int(time.time())}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", "x-fsign": "SW9D1eZo"})
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"📡 Перерыв в {len(matches)} играх.")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        
                        h = m_block.split('AE÷')[1].split('¬')[0]
                        a = m_block.split('AF÷')[1].split('¬')[0]
                        
                        logger.info(f"🔍 Взлом TLS-брони: {h} - {a}")
                        stats = await self.get_stats_clean(session, m_id)
                        
                        if stats:
                            if stats["shots"] >= 11 or stats["pen"] >= 4:
                                msg = (f"🏒 **{h} - {a}**\n\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                       f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                self.sent_cache[m_id] = True
                                logger.info(f"✅ ПРОБИТО: {h}")
                        else:
                            logger.warning(f"🛡️ {h}: Защита слишком сильна.")
                        
                        await asyncio.sleep(random.uniform(5, 10))
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Цикл: {e}"); await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
