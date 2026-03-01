import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.3")

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
        # Имитируем, что мы перешли из ленты в сам матч
        headers = self.headers.copy()
        headers["Referer"] = f"https://www.flashscore.ru/match/{m_id}/#/match-summary/match-statistics/0"
        
        # Небольшая пауза, как будто человек кликает
        await asyncio.sleep(random.uniform(2, 4))
        
        for ep in [f"d_st_{m_id}_ru-ru_1", f"d_st_{m_id}_en-gb_1"]:
            try:
                url = f"https://www.flashscore.ru/x/feed/{ep}?t={int(time.time()*1000)}"
                r = await session.get(url, headers=headers, timeout=15)
                
                if r.status_code == 200 and "¬" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    # Парсинг по твоим меткам
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
        logger.info(f"=== v33.3 THE HUMANIZER | Proxy: {'ON' if PROXY_URL else 'OFF'} ===")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            # ШАГ 1: "Прогрев" — получаем Cookie с главной страницы
            try:
                await session.get("https://www.flashscore.ru/", headers=self.headers, timeout=20)
                logger.info("🍪 Cookie получены, сессия активна.")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось прогреть сессию: {e}")

            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    matches = r.text.split('~AA÷')[1:]
                    logger.info(f"📡 Мониторинг: {len(matches)} игр.")
                    
                    for m_block in matches:
                        # Ищем только ПЕРЕРЫВ (код 46)
                        if "AC÷46" in m_block:
                            m_id = m_block.split('¬')[0]
                            if m_id not in self.sent_cache:
                                h = m_block.split('AE÷')[1].split('¬')[0]
                                a = m_block.split('AF÷')[1].split('¬')[0]
                                gh = m_block.split('AG÷')[1].split('¬')[0] if 'AG÷' in m_block else "0"
                                ga = m_block.split('AH÷')[1].split('¬')[0] if 'AH÷' in m_block else "0"
                                
                                score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                if score <= 1:
                                    logger.info(f"🧐 Проверяю статику для: {h} - {a}")
                                    stats = await self.get_stats(session, m_id)
                                    if stats:
                                        if stats["shots"] >= 11 or stats["pen"] >= 4:
                                            msg = (f"🏒 **{h} {gh}:{ga} {a}**\n\n"
                                                   f"📊 **1-й период:**\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                                   f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                            await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                            self.sent_cache[m_id] = True
                                            logger.info(f"🚀 СИГНАЛ ОТПРАВЛЕН: {h}")
                                        else:
                                            logger.info(f"📉 Активность низкая ({h}): {stats}")
                                    else:
                                        logger.warning(f"📭 Данные не пробиты для {h}")
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
