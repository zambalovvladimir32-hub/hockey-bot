import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyXRay")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyScanner:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = set()

    def _get_val(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0].strip()
        except: return ""

    async def run(self):
        logger.info("📡 ЗАПУСК ДИАГНОСТИКИ v11.4 [X-RAY]")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        logger.error(f"❌ Ошибка доступа: {r.status_code}")
                        await asyncio.sleep(20); continue

                    sections = r.text.split('~ZA÷')
                    found_matches = 0
                    
                    for sec in sections[1:]:
                        league = sec.split('¬')[0]
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            found_matches += 1
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷') # Код статуса
                            timer = self._get_val(m_block, 'TT÷').upper() # Текст (ПЕРЕРЫВ)
                            home = self._get_val(m_block, 'AE÷')
                            away = self._get_val(m_block, 'AF÷')

                            # 🛠 ЛОГИРУЕМ ВСЕ ПЕРЕРЫВЫ ДЛЯ ПРОВЕРКИ
                            # Если это не 1, 2 или 3 период - значит какой-то спец-статус
                            if status not in ['1', '2', '3', '6', '37']: 
                                logger.info(f"🔎 Найден матч: {home}-{away} | Статус Код: {status} | Таймер: {timer}")

                            # Пытаемся поймать перерыв (Код 45 или текст "ПЕРЕРЫВ")
                            is_break = (status == '45' or "ПЕРЕРЫВ" in timer or "1-Й ПЕРЕРЫВ" in timer)
                            
                            if is_break:
                                # Пробуем достать счет 1-го периода
                                h1 = self._get_val(m_block, 'BA÷')
                                a1 = self._get_val(m_block, 'BB÷')
                                
                                # Если BA/BB пусты, берем общий счет AG/AH (в перерыве он совпадает с 1-м периодом)
                                if h1 == "" or a1 == "":
                                    h1 = self._get_val(m_block, 'AG÷')
                                    a1 = self._get_val(m_block, 'AH÷')

                                if h1 != "" and a1 != "":
                                    score = (int(h1), int(a1))
                                    if score in [(0, 0), (1, 0), (0, 1)]:
                                        if m_id not in self.sent_cache:
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            text = f"🏒 **{home} {h1}:{a1} {away}**\n🏆 {league}\n\n☕️ **ПЕРЕРЫВ 1-2**\n📊 Счет: `{h1}:{a1}`\n🔗 [МАТЧ]({link})"
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache.add(m_id)
                                            logger.info(f"✅ ОТПРАВЛЕНО: {home}-{away}")
                                    else:
                                        if m_id not in self.sent_cache:
                                            logger.info(f"⏭ Пропуск по счету: {home}-{away} ({h1}:{a1})")
                                            self.sent_cache.add(m_id)

                    logger.info(f"📡 Цикл окончен. Всего игр в лайве: {found_matches}")
                    if len(self.sent_cache) > 1000: self.sent_cache.clear()

                except Exception as e:
                    logger.error(f"🚨 Ошибка: {e}")
                await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
