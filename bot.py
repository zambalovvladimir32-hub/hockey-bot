import asyncio, os, logging, sys, time, random
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyV33.7")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
bot = Bot(token=TOKEN)

class HockeySniper:
    def __init__(self):
        self.url_main = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9"
        }
        self.sent_cache = {}

    async def get_stats(self, session, m_id):
        # Для резидентских прокси важна небольшая пауза, имитирующая чтение страницы
        await asyncio.sleep(random.uniform(3.5, 6.0))
        
        # Основной эндпоинт для статистики
        url = f"https://www.flashscore.ru/x/feed/d_st_{m_id}_ru-ru_1?t={int(time.time()*1000)}"
        try:
            r = await session.get(url, headers=self.headers, timeout=15)
            if r.status_code == 200 and "¬" in r.text:
                d = r.text
                st = {"shots": 0, "pen": 0}
                
                # Поиск Бросков (Shots on Goal)
                for tag in ["Удары по воротам", "Броски", "SG÷", "SOG÷"]:
                    if tag in d:
                        try:
                            # Парсим значения хозяев и гостей
                            parts = d.split(tag)[1].split("¬")
                            v1 = parts[1].split("÷")[1]
                            v2 = parts[2].split("÷")[1]
                            if v1.isdigit() and v2.isdigit():
                                st["shots"] = int(v1) + int(v2)
                                break
                        except: continue

                # Поиск Штрафов (PIM)
                for tag in ["ПИМ", "Штрафное время", "PM÷"]:
                    if tag in d:
                        try:
                            parts = d.split(tag)[1].split("¬")
                            v1 = parts[1].split("÷")[1]
                            v2 = parts[2].split("÷")[1]
                            if v1.isdigit() and v2.isdigit():
                                st["pen"] = int(v1) + int(v2)
                                break
                        except: continue
                
                return st if (st["shots"] > 0 or st["pen"] > 0) else None
        except Exception as e:
            logger.debug(f"Ошибка запроса статы {m_id}: {e}")
        return None

    async def run(self):
        logger.info(f"🚀 v33.7 ЗАПУЩЕН | Прокси: {PROXY_URL[:20]}...")
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        async with AsyncSession(impersonate="chrome110", proxies=proxies) as session:
            # Предварительный заход на главную для получения кук
            try:
                await session.get("https://www.flashscore.ru/", headers=self.headers, timeout=15)
                logger.info("✅ Сессия на новом прокси успешно инициализирована.")
            except:
                logger.warning("⚠️ Не удалось прогреть сессию, работаем напрямую.")

            while True:
                try:
                    # Тянем ленту матчей
                    r = await session.get(f"{self.url_main}?t={int(time.time())}", headers=self.headers, timeout=20)
                    matches = [m for m in r.text.split('~AA÷')[1:] if "AC÷46" in m] # Только перерыв
                    logger.info(f"📡 Мониторинг: {len(matches)} игр в перерыве.")
                    
                    for m_block in matches:
                        m_id = m_block.split('¬')[0]
                        if m_id in self.sent_cache: continue
                        
                        # Извлекаем команды и счет
                        try:
                            h = m_block.split('AE÷')[1].split('¬')[0]
                            a = m_block.split('AF÷')[1].split('¬')[0]
                            gh = m_block.split('AG÷')[1].split('¬')[0] if 'AG÷' in m_block else "0"
                            ga = m_block.split('AH÷')[1].split('¬')[0] if 'AH÷' in m_block else "0"
                            
                            score = int(gh) + int(ga)
                            if score <= 1:
                                logger.info(f"🔎 Проверка через резидентский прокси: {h} - {a}")
                                stats = await self.get_stats(session, m_id)
                                
                                if stats:
                                    # Критерии: броски >= 11 или ПИМ >= 4
                                    if stats["shots"] >= 11 or stats["pen"] >= 4:
                                        label = "🔥 GOLD" if stats["shots"] >= 16 else "💎 SIGNAL"
                                        msg = (f"🏒 **{h} {gh}:{ga} {a}**\n"
                                               f"📊 **1-й период:**\n🎯 Броски: `{stats['shots']}`\n⚖️ ПИМ: `{stats['pen']} мин`"
                                               f"\n\n🏆 Рейтинг: **{label}**\n"
                                               f"🔗 [МАТЧ](https://www.flashscore.ru/match/{m_id}/#/match-summary)")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown", disable_web_page_preview=True)
                                        self.sent_cache[m_id] = True
                                        logger.info(f"✅ СИГНАЛ ОТПРАВЛЕН: {h}")
                                    else:
                                        logger.info(f"📉 Слабо ({h}): Б:{stats['shots']} П:{stats['pen']}")
                                else:
                                    logger.warning(f"📭 Данные не пробиты для {h}")
                        except: continue
                        
                    await asyncio.sleep(45)
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(HockeySniper().run())
