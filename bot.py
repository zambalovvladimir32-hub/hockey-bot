import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV32.8")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") # Должен быть в переменных Railway
bot = Bot(token=TOKEN)

LEAGUES = ["НХЛ", "NHL", "АХЛ", "AHL", "КХЛ", "ВХЛ", "МХЛ", "ЧЕХИЯ", "ГЕРМАНИЯ", "ФИНЛЯНДИЯ", "ШВЕЙЦАРИЯ", "ШВЕЦИЯ", "АВСТРИЯ"]

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

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def get_stats(self, session, m_id):
        # Используем прокси для запросов статы
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        for ep in [f"d_st_{m_id}_ru-ru_1", f"d_st_{m_id}_en-gb_1"]:
            try:
                url = f"https://www.flashscore.ru/x/feed/{ep}?t={int(time.time()*1000)}"
                r = await session.get(url, headers=self.headers, proxies=proxies, timeout=15)
                
                if r.status_code == 200 and "¬" in r.text:
                    d = r.text
                    st = {"shots": 0, "pen": 0}
                    # Ищем Броски/Сэйвы
                    for tag in ["Удары по воротам", "Вратарь отбивает мяч", "SG÷", "SOG÷"]:
                        if tag in d:
                            v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                            if len(v) >= 2: st["shots"] = int(v[0]) + int(v[1]); break
                    # Ищем ПИМ
                    for tag in ["ПИМ", "Штрафы", "Штрафное время", "PM÷"]:
                        if tag in d:
                            v = [x.split("÷")[1] for x in d.split(tag)[1].split("~")[0].split("¬") if "÷" in x and x.split("÷")[1].isdigit()]
                            if len(v) >= 2: st["pen"] = int(v[0]) + int(v[1]); break
                    if st["shots"] > 0 or st["pen"] > 0: return st
            except Exception as e:
                logger.debug(f"Ошибка прокси/запроса: {e}")
                continue
        return None

    async def run(self):
        logger.info(f"=== v32.8 PROXY-STRIKE ЗАПУЩЕН | Прокси: {'ДА' if PROXY_URL else 'НЕТ'} ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    # Основную ленту можно тянуть и без прокси (чтобы экономить трафик), 
                    # но если будут ошибки 403, добавим и сюда.
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    matches = r.text.split('~AA÷')[1:]
                    logger.info(f"📡 Мониторинг: {len(matches)} игр.")
                    
                    for sec in r.text.split('~ZA÷')[1:]:
                        league = sec.split('¬')[0]
                        if not any(lg.upper() in league.upper() for lg in LEAGUES): continue
                        
                        for m_block in sec.split('~AA÷')[1:]:
                            m_id = m_block.split('¬')[0]
                            if self._get_val(m_block, 'AC÷') == '46':
                                h, a = self._get_val(m_block, 'AE÷'), self._get_val(m_block, 'AF÷')
                                if m_id not in self.sent_cache:
                                    gh, ga = self._get_val(m_block, 'AG÷'), self._get_val(m_block, 'AH÷')
                                    score = (int(gh) if gh.isdigit() else 0) + (int(ga) if ga.isdigit() else 0)
                                    
                                    if score <= 1:
                                        logger.info(f"🛰 Через прокси проверяю: {h} - {a}")
                                        stats = await self.get_stats(session, m_id)
                                        if stats:
                                            if stats["shots"] >= 11 or stats["pen"] >= 4:
                                                label = "🔥 GOLD СИГНАЛ" if stats["shots"] >= 16 else "💎 СИГНАЛ"
                                                msg = (f"🏒 **{h} {gh}:{ga} {a}**\n🏆 {league}\n\n"
                                                       f"📊 **Статистика (1-й период):**\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                                       f"\n\n🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown", disable_web_page_preview=True)
                                                self.sent_cache[m_id] = f"{h}-{a}"
                                                logger.info(f"🚀 СИГНАЛ ОТПРАВЛЕН: {h}")
                                            else:
                                                logger.info(f"📉 Мало активности ({h}): Б:{stats['shots']} П:{stats['pen']}")
                                        else:
                                            logger.warning(f"📭 Даже через прокси стата скрыта для {h}")
                    
                    await asyncio.sleep(40)
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
