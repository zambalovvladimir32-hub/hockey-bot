import asyncio, os, logging, sys, time
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

# Настройка логов, чтобы в Railway всё было красиво
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s', 
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HockeyUltimatum")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyScanner:
    def __init__(self):
        # Основной фид Flashscore (Лайв)
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = set()

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def run(self):
        logger.info("🚀 ЗАПУСК: ХОККЕЙНЫЙ СКАНЕР v11.3 [ULTIMATUM]")
        logger.info("🎯 Цель: Перерыв 1-2 | Счет 0:0, 1:0, 0:1")
        
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    # Добавляем t=время, чтобы обмануть кэш
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    
                    if r.status_code != 200:
                        logger.warning(f"⚠️ Ошибка Flashscore: {r.status_code}. Жду 30 сек...")
                        await asyncio.sleep(30)
                        continue

                    sections = r.text.split('~ZA÷')
                    total_live = 0
                    found_breaks = 0
                    
                    for sec in sections[1:]:
                        league = sec.split('¬')[0]
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            total_live += 1
                            m_id = m_block.split('¬')[0]
                            status_code = self._get_val(m_block, 'AC÷')
                            
                            # AC÷45 — это строго ПЕРЕРЫВ между 1 и 2 периодом
                            if status_code == '45':
                                found_breaks += 1
                                h1 = self._get_val(m_block, 'BA÷') # Голы хозяев в 1-м
                                a1 = self._get_val(m_block, 'BB÷') # Голы гостей в 1-м
                                
                                if h1 != "" and a1 != "":
                                    score = (int(h1), int(a1))
                                    home = self._get_val(m_block, 'AE÷')
                                    away = self._get_val(m_block, 'AF÷')
                                    
                                    # Проверяем наши "золотые" счета
                                    if score in [(0, 0), (1, 0), (0, 1)]:
                                        if m_id not in self.sent_cache:
                                            # Формируем прямую ссылку на матч
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            
                                            text = (
                                                f"🏒 **{home} {h1}:{a1} {away}**\n"
                                                f"🏆 {league}\n\n"
                                                f"☕️ **ПЕРЕРЫВ 1-2**\n"
                                                f"📊 Счет периода: `{h1}:{a1}`\n\n"
                                                f"🔗 [ОТКРЫТЬ МАТЧ]({link})"
                                            )
                                            
                                            try:
                                                await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                                self.sent_cache.add(m_id)
                                                logger.info(f"✅ СИГНАЛ: {home}-{away} ({h1}:{a1})")
                                            except Exception as te:
                                                logger.error(f"Ошибка TG: {te}")
                                    else:
                                        # Если счет другой (например 1:1), просто отмечаем в кэше, чтобы не дергать
                                        self.sent_cache.add(m_id)

                    # Пульс в логи Railway (чтобы ты видел, что всё ок)
                    logger.info(f"📡 Мониторинг: {total_live} игр в лайве, {found_breaks} в перерыве. Жду...")

                    # Очистка кэша раз в 6 часов
                    if len(self.sent_cache) > 1000:
                        self.sent_cache.clear()
                        logger.info("🧹 Кэш очищен")

                except Exception as e:
                    logger.error(f"🚨 Ошибка в цикле: {e}")
                
                # Опрос каждые 40 секунд (оптимально для Railway)
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
