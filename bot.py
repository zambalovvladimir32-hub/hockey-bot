import asyncio
import os
import logging
import sys
import time
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HockeyBreakScanner")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyScanner:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = set()

    def _get_val(self, block, tag):
        try:
            return block.split(tag)[1].split('¬')[0].strip()
        except IndexError:
            return ""

    def validate_match(self, block, league):
        m_id = block.split('¬')[0]
        
        # 1. ПРОВЕРКА СТАТУСА: СТРОГО ПЕРЕРЫВ
        ac_code = self._get_val(block, 'AC÷')
        timer = self._get_val(block, 'TT÷').upper()
        
        is_break = (ac_code == '45' or "ПЕРЕРЫВ" in timer or "PAUSE" in timer)
        
        if not is_break or ac_code in ['46', '3', '6', '2']:
            return None

        # 2. ПРОВЕРКА СЧЕТА 1-ГО ПЕРИОДА
        ba = self._get_val(block, 'BA÷')
        bb = self._get_val(block, 'BB÷')
        
        if not ba or not bb:
            return None

        try:
            h1 = int(ba)
            a1 = int(bb)
        except ValueError:
            return None

        # 3. ФИЛЬТР НУЖНЫХ СЧЕТОВ: 0:0, 1:0, 0:1
        valid_scores = [(0, 0), (1, 0), (0, 1)]
        if (h1, a1) not in valid_scores:
            return None

        home = self._get_val(block, 'AE÷')
        away = self._get_val(block, 'AF÷')

        return {
            'id': m_id,
            'text': (
                f"🏒 **{home} {h1}:{a1} {away}**\n"
                f"🏆 {league}\n"
                f"☕️ ПЕРЕРЫВ (Перед 2-м периодом)\n\n"
                f"📊 Счет 1-го периода: `{h1}:{a1}`"
            )
        }

    async def run(self):
        logger.info("=== HOCKEY BREAK SCANNER v11.1 (DEBUG) STARTED ===")
        logger.info("Условия: Любая лига | Только Перерыв 1-2 | Счет 0:0, 1:0, 0:1")
        
        loops_count = 0
        
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    
                    if r.status_code != 200:
                        logger.warning(f"⚠️ Ошибка от Flashscore! Код ответа: {r.status_code}. Ждем 15 сек...")
                        await asyncio.sleep(15)
                        continue

                    sections = r.text.split('~ZA÷')
                    live_matches = sum(len(sec.split('~AA÷')) - 1 for sec in sections[1:])
                    
                    loops_count += 1
                    # Пишем пульс каждые 5 минут (каждый 10-й цикл по 30 сек)
                    if loops_count % 10 == 0: 
                        logger.info(f"ℹ️ Бот сканирует... В лайве сейчас матчей: {live_matches}. Ищу нужный перерыв...")

                    for sec in sections[1:]:
                        league = sec.split('¬')[0]
                        matches = sec.split('~AA÷')
                        
                        for m_block in matches[1:]:
                            match = self.validate_match(m_block, league)
                            
                            if match:
                                m_id = match['id']
                                
                                if m_id not in self.sent_cache:
                                    try:
                                        await bot.send_message(CHANNEL_ID, match['text'], parse_mode="Markdown")
                                        self.sent_cache.add(m_id)
                                        logger.info(f"✅ ОТПРАВЛЕН МАТЧ: {m_id}")
                                        await asyncio.sleep(1) 
                                    except TelegramRetryAfter as e:
                                        logger.warning(f"⏳ Флуд-контроль TG, ждем {e.retry_after} сек...")
                                        await asyncio.sleep(e.retry_after)
                                    except Exception as e:
                                        logger.error(f"Ошибка отправки TG: {e}")

                    if len(self.sent_cache) > 500: 
                        self.sent_cache.clear()

                except Exception as e:
                    logger.error(f"❌ Ошибка цикла: {e}")
                
                await asyncio.sleep(30)

if __name__ == "__main__":
    scanner = HockeyScanner()
    asyncio.run(scanner.run())
