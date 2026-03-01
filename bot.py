import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.9")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        # Используем основной мобильный поток данных
        self.url_feed = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/",
            "Connection": "keep-alive"
        }
        self.sent_cache = {}

    async def get_stats_hard(self, session, m_id):
        # Максимальная имитация поведения человека перед кликом
        await asyncio.sleep(random.uniform(4, 7))
        
        # Пробуем достать через мобильный API-эндпоинт (часто менее защищен)
        api_url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1"
        
        try:
            # Используем impersonate="chrome120" для обхода TLS-фингерпринтинга
            r = await session.get(f"{api_url}?t={int(time.time()*1000)}", headers=self.headers, timeout=15)
            
            if r.status_code == 200 and "¬" in r.text:
                d = r.text
                st = {"shots": 0, "pen": 0}
                
                # Парсинг по ключевым меткам (удары/штрафы)
                rows = d.split("¬")
                for i, row in enumerate(rows):
                    if any(x in row for x in ["Удары по воротам", "Броски", "SOG", "SG"]):
                        try:
                            # Значения команд находятся в следующих блоках после названия параметра
                            st["shots"] = int(rows[i+1].split("÷")[1]) + int(rows[i+2].split("÷")[1])
                        except: pass
                    if any(x in row for x in ["ПИМ", "Штраф", "PM"]):
                        try:
                            st["pen"] = int(rows[i+1].split("÷")[1]) + int(rows[i+2].split("÷")[1])
                        except: pass
                
                if st["shots"] > 0 or st["pen"] > 0:
                    return st
        except Exception as e:
            logger.debug(f"Ошибка парсинга {m_id}: {e}")
        return None

    async def run(self):
        logger.info(f"=== v33.9 FINAL BYPASS ЗАПУЩЕН | Прокси: ISP ===")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            # Принудительно ставим базовые куки
            await session.get("https://www.flashscore.ru/", headers=self.headers)
            
            while True:
                try:
                    r = await session.get(f"{self.url_feed}?t={int(time.time())}", headers=self.headers)
                    # Фильтруем матчи в перерыве
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m]
                    logger.info(f"📡 Активно: {len(matches)} игр в перерыве.")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        
                        h = m_block.split('AE÷')[1].split('¬')[0]
                        a = m_block.split('AF÷')[1].split('¬')[0]
                        gh = m_block.split('AG÷')[1].split('¬')[0] if 'AG÷' in m_block else "0"
                        ga = m_block.split('AH÷')[1].split('¬')[0] if 'AH÷' in m_block else "0"
                        
                        if (int(gh) + int(ga)) <= 1:
                            logger.info(f"🧨 Взлом статистики: {h} - {a}")
                            stats = await self.get_stats_hard(session, m_id)
                            
                            if stats:
                                if stats["shots"] >= 11 or stats["pen"] >= 4:
                                    msg = (f"🏒 **{h} {gh}:{ga} {a}**\n\n"
                                           f"🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                           f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                    await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                    self.sent_cache[m_id] = True
                                    logger.info(f"✅ СИГНАЛ: {h}")
                                else:
                                    logger.info(f"📉 Стата получена ({h}), но не подходит: {stats}")
                            else:
                                logger.warning(f"🚧 {h}: Защита не пробита.")
                    
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Ошибка: {e}"); await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
