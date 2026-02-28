import asyncio
import os
import logging
import sys
import time
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

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
            return block.split(tag)[1].split('¬')[0].strip()
        except IndexError:
            return ""

    def validate_match(self, block, league):
        m_id = block.split('¬')[0]
        ac_code = self._get_val(block, 'AC÷')
        timer = self._get_val(block, 'TT÷').upper()
        
        # 1. ФИЛЬТР СТАТУСА: Только 2-й период (2) или Перерыв (45)
        if ac_code not in ['2', '45']:
            return None

        # 2. ЖЕСТКИЙ БЛОК 3-ГО ПЕРИОДА
        # Теги BE÷ и BF÷ появляются ТОЛЬКО когда начинается 3-й период
        if self._get_val(block, 'BE÷') or self._get_val(block, 'BF÷'):
            return None

        # 3. ПАРСИНГ ГОЛОВ (Правильные хоккейные теги Flashscore)
        ag = self._get_val(block, 'AG÷') # Общий счет (хозяева)
        ah = self._get_val(block, 'AH÷') # Общий счет (гости)
        if not ag or not ah: 
            return None
            
        # 1-й период (BA - хозяева, BB - гости)
        ba = self._get_val(block, 'BA÷')
        bb = self._get_val(block, 'BB÷')
        if not ba or not bb:
            return None # Если нет реза 1-го периода - данные не готовы
            
        # 2-й период (BC - хозяева, BD - гости)
        bc = self._get_val(block, 'BC÷')
        bd = self._get_val(block, 'BD÷')

        try:
            total_h, total_a = int(ag), int(ah)
            h1, a1 = int(ba), int(bb)
            h2 = int(bc) if bc else 0
            a2 = int(bd) if bd else 0

            # 4. МАТЕМАТИЧЕСКАЯ ПРОВЕРКА (Железная логика)
            # Сумма по периодам ОБЯЗАНА сходиться с общим счетом
            if (h1 + h2 != total_h) or (a1 + a2 != total_a):
                return None
                
        except ValueError:
            return None

        # ОФОРМЛЕНИЕ
        is_break = (ac_code == '45' or "ПЕРЕРЫВ" in timer or "PAUSE" in timer)
        status_text = "☕️ ПЕРЕРЫВ (1-2)" if is_break else f"⏱ 2-Й ПЕРИОД [{timer}]"
        home = self._get_val(block, 'AE÷')
        away = self._get_val(block, 'AF÷')

        return {
            'id': m_id,
            'state': ac_code, # Кэшируем по статусу (чтобы не спамить при каждом голе)
            'text': (
                f"🏒 **{home} {total_h}:{total_a} {away}**\n"
                f"🏆 {league}\n"
                f"{status_text}\n\n"
                f"📊 Счет по периодам:\n"
                f"└ 1-й: `{h1}:{a1}`\n"
                f"└ 2-й: `{h2}:{a2}`"
            )
        }

    async def run(self):
        logger.info("=== HOCKEY SCANNER v10.0 (REAL HOCKEY TAGS) STARTED ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    r = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers, timeout=20)
                    if r.status_code != 200:
                        await asyncio.sleep(5)
                        continue

                    sections = r.text.split('~ZA÷')
                    matches_found = 0
                    
                    for sec in sections[1:]:
                        league = sec.split('¬')[0]
                        matches = sec.split('~AA÷')
                        for m_block in matches[1:]:
                            match = self.validate_match(m_block, league)
                            if match:
                                matches_found += 1
                                m_id, state = match['id'], match['state']
                                
                                # Отправляем, если в кэше нет этого матча ИЛИ у него сменился статус (например, с перерыва на 2-й период)
                                if self.sent_cache.get(m_id) != state:
                                    try:
                                        await bot.send_message(CHANNEL_ID, match['text'], parse_mode="Markdown")
                                        self.sent_cache[m_id] = state
                                        logger.info(f"✅ Отправлено: {m_id} (Статус: {state})")
                                    except TelegramRetryAfter as e:
                                        await asyncio.sleep(e.retry_after)
                                    except Exception as e:
                                        logger.error(f"Ошибка TG: {e}")

                    logger.info(f"🔎 Найдено чистых матчей 2-го периода/перерыва: {matches_found}")
                    if len(self.sent_cache) > 600: self.sent_cache.clear()

                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                
                await asyncio.sleep(30)

if __name__ == "__main__":
    scanner = HockeyScanner()
    asyncio.run(scanner.run())
