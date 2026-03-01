import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.1")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "ЧЕХИЯ", "ГЕРМАНИЯ", "ФИНЛЯНДИЯ", "ШВЕЙЦАРИЯ", "ШВЕЦИЯ", "АВСТРИЯ"]

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9"
        }
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id):
        # Добавляем случайную паузу перед запросом статы, чтобы не «спамить»
        await asyncio.sleep(random.uniform(1.5, 3.0))
        
        # Пробуем разные эндпоинты
        for ep in [f"d_st_{m_id}_ru-ru_1", f"d_st_{m_id}_en-gb_1"]:
            try:
                # ВАЖНО: Добавляем параметры, которые сайт ждет от реального браузера
                url = f"https://www.flashscore.ru/x/feed/{ep}?t={int(time.time()*1000)}"
                r = await session.get(url, headers=self.headers, timeout=15)
                
                if r.status_code == 200 and "¬" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    # Универсальный поиск цифр (броски и ПИМ)
                    for line in d.split("¬"):
                        if "÷" not in line: continue
                        key, val = line.split("÷")[0], line.split("÷")[1]
                        
                        if any(x in key for x in ["Удары по воротам", "Броски", "SG", "SOG"]):
                            try:
                                parts = d.split(key)[1].split("¬")
                                v1 = parts[1].split("÷")[1]
                                v2 = parts[2].split("÷")[1]
                                st["shots"] = int(v1) + int(v2)
                            except: pass
                            
                        if any(x in key for x in ["ПИМ", "Штраф", "PM"]):
                            try:
                                parts = d.split(key)[1].split("¬")
                                v1 = parts[1].split("÷")[1]
                                v2 = parts[2].split("÷")[1]
                                st["pen"] = int(v1) + int(v2)
                            except: pass
                    
                    if st["shots"] > 0 or st["pen"] > 0:
                        return st
            except Exception as e:
                logger.debug(f"Ошибка парсинга {m_id}: {e}")
        return None

    async def run(self):
        logger.info(f"=== v33.1 SILENT HUNTER | Proxy: {'ON' if PROXY_URL else 'OFF'} ===")
        # Создаем одну сессию с прокси на всё время
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            while True:
                try:
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    matches = r.text.split('~AA÷')[1:]
                    logger.info(f"📡 Мониторинг: {len(matches)} игр в ленте.")
                    
                    for m_block in matches:
                        # Проверяем только матчи в ПЕРЕРЫВЕ (код 46)
                        if self._get_val(m_block, 'AC÷') == '46':
                            m_id = m_block.split('¬')[0]
                            if m_id not in self.sent_cache:
                                h, a = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')
                                gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')
                                score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                
                                if score <= 1:
                                    logger.info(f"🔎 Проверяю активность: {h} - {a}")
                                    stats = await self.get_stats(session, m_id)
                                    
                                    if stats:
                                        # Наши критерии: броски 11+ или ПИМ 4+
                                        if stats["shots"] >= 11 or stats["pen"] >= 4:
                                            label = "🔥 GOLD" if stats["shots"] >= 16 else "💎 СИГНАЛ"
                                            msg = (f"🏒 **{h} {gh}:{ga} {a}**\n\n"
                                                   f"📊 **1-й период:**\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                                   f"\n\n🏆 Рейтинг: **{label}**\n"
                                                   f"🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                            await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                            self.sent_cache[m_id] = True
                                            logger.info(f"🚀 СИГНАЛ В КАНАЛЕ: {h}")
                                        else:
                                            logger.info(f"📉 Мало: Б:{stats['shots']} П:{stats['pen']} ({h})")
                                    else:
                                        logger.warning(f"📭 Не удалось вытянуть статку для {h}")
                    
                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
