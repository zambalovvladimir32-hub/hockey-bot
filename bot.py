import asyncio
import os
import logging
import sys
import time
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HockeyBot")

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
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try:
            return block.split(tag)[1].split('¬')[0]
        except:
            return ""

    def validate_match(self, block, league):
        """Проверка на вшивость: только 2-й период и только честный счет."""
        m_id = block.split('¬')[0]
        
        # Сбор данных
        ac_code = self._get_val(block, 'AC÷')     # Код статуса
        timer = self._get_val(block, 'TT÷').upper() # Текст (P2, Pause)
        
        full_h = self._get_val(block, 'AG÷') or "0"
        full_a = self._get_val(block, 'AH÷') or "0"
        
        s1 = self._get_val(block, 'XA÷') # Счет 1-го периода
        s2 = self._get_val(block, 'XB÷') # Счет 2-го периода
        s3 = self._get_val(block, 'XC÷') # Счет 3-го периода (Детектор зла)

        # 1. ФИЛЬТР 3-ГО ПЕРИОДА (если есть XC или код 3/46/6)
        if s3 or ac_code in ['3', '46', '6'] or "P3" in timer:
            return None

        # 2. ФИЛЬТР 1-ГО ПЕРИОДА (должен быть завершен - есть счет XA)
        if not s1 or ac_code == '1' or "P1" in timer:
            return None

        # 3. МАТЕМАТИЧЕСКАЯ ПРОВЕРКА (Сумма периодов == Общий счет)
        try:
            h1, a1 = map(int, s1.split(':'))
            h2, a2 = map(int, (s2 if s2 else "0:0").split(':'))
            
            # Если сумма за 1-й и 2-й не равна общему счету — значит данные лагают или уже 3-й период
            if (h1 + h2 != int(full_h)) or (a1 + a2 != int(full_a)):
                return None
        except:
            return None

        # 4. ФИНАЛИЗАЦИЯ
        is_break = (ac_code == '45' or "ПЕРЕРЫВ" in timer or "PAUSE" in timer)
        status_text = "☕️ ПЕРЕРЫВ (1-2)" if is_break else f"⏱ 2-Й ПЕРИОД [{timer}]"
        
        home = self._get_val(block, 'AE÷')
        away = self._get_val(block, 'AF÷')

        return {
            'id': m_id,
            'state': f"{full_h}:{full_a}_{is_break}",
            'text': (
                f"🏒 **{home} {full_h}:{full_a} {away}**\n"
                f"🏆 {league}\n"
                f"{status_text}\n\n"
                f"📊 Счет по периодам:\n"
                f"└ 1-й: `{s1}`\n"
                f"└ 2-й: `{s2 if s2 else '0:0'}`"
            )
        }

    async def run(self):
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        await asyncio.sleep(5)
                        continue

                    sections = r.text.split('~ZA÷')
                    for sec in sections[1:]:
                        league = sec.split('¬')[0]
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            match = self.validate_match(m_block, league)
                            if match:
                                m_id, state = match['id'], match['state']
                                if self.sent_cache.get(m_id) != state:
                                    try:
                                        await bot.send_message(CHANNEL_ID, match['text'], parse_mode="Markdown")
                                        self.sent_cache[m_id] = state
                                        logger.info(f"✅ Отправлено: {m_id}")
                                    except TelegramRetryAfter as e:
                                        await asyncio.sleep(e.retry_after)
                                    except Exception as e:
                                        logger.error(f"Ошибка TG: {e}")

                    if len(self.sent_cache) > 500: self.sent_cache.clear()

                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                
                await asyncio.sleep(30)

if __name__ == "__main__":
    scanner = HockeyScanner()
    asyncio.run(scanner.run())
