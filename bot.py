import asyncio, os, logging, sys, time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("HockeyPro")

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
        logger.info("=== HOCKEY SCANNER v12.0 (FINAL) STARTED ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        await asyncio.sleep(20); continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league = sec.split('¬')[0]
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            m_id = m_block.split('¬')[0]
                            status = self._get_val(m_block, 'AC÷')
                            
                            # ЛОГИКА: Теперь ловим и 45, и 46 (как на твоем скрине)
                            if status in ['45', '46']:
                                h1 = self._get_val(m_block, 'BA÷')
                                a1 = self._get_val(m_block, 'BB÷')
                                
                                # Запасной вариант забора счета
                                if h1 == "" or a1 == "":
                                    h1 = self._get_val(m_block, 'AG÷')
                                    a1 = self._get_val(m_block, 'AH÷')

                                if h1 != "" and a1 != "":
                                    score = (int(h1), int(a1))
                                    if score in [(0, 0), (1, 0), (0, 1)]:
                                        if m_id not in self.sent_cache:
                                            home = self._get_val(m_block, 'AE÷')
                                            away = self._get_val(m_block, 'AF÷')
                                            link = f"https://www.flashscore.ru/match/{m_id}/#/match-summary"
                                            
                                            text = f"🏒 **{home} {h1}:{a1} {away}**\n🏆 {league}\n\n☕️ **ПЕРЕРЫВ 1-2**\n📊 Счет: `{h1}:{a1}`\n🔗 [ОТКРЫТЬ МАТЧ]({link})"
                                            
                                            await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
                                            self.sent_cache.add(m_id)
                                            logger.info(f"✅ СИГНАЛ: {home}-{away}")

                    if len(self.sent_cache) > 1000: self.sent_cache.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                await asyncio.sleep(35)

if __name__ == "__main__":
    asyncio.run(HockeyScanner().run())
