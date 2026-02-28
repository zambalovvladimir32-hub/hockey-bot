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
logger = logging.getLogger("HockeyUltimate")

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
        except:
            return ""

    def validate_match(self, block, league):
        m_id = block.split('¬')[0]
        ac_code = self._get_val(block, 'AC÷')
        timer = self._get_val(block, 'TT÷').upper()
        
        # 1. СТАТУСНЫЙ ФИЛЬТР (Только 2-й период или перерыв 1-2)
        # 45 - Перерыв, 2 - 2-й период. Остальное (3, 4, 6, 1) игнорим.
        if ac_code not in ['2', '45'] and "P2" not in timer and "ПЕРЕРЫВ" not in timer:
            return None

        # 2. СБОР ДАННЫХ
        full_h = self._get_val(block, 'AG÷') or "0"
        full_a = self._get_val(block, 'AH÷') or "0"
        s1 = self._get_val(block, 'XA÷') # Счет 1-го периода
        s2 = self._get_val(block, 'XB÷') # Счет 2-го периода
        s3 = self._get_val(block, 'XC÷') # Счет 3-го периода (если есть - это лаг)

        if s3: return None # Если есть хоть намек на 3-й период в данных - в топку.

        # 3. ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ
        try:
            # Парсим общий счет
            total_h, total_a = int(full_h), int(full_a)
            
            # Парсим 1-й период (он ОБЯЗАН быть, если мы во 2-м)
            if not s1 or ":" not in s1: return None
            h1, a1 = map(int, s1.split(':'))
            
            # Парсим 2-й период (если его еще нет в тегах, считаем 0:0)
            h2, a2 = 0, 0
            if s2 and ":" in s2:
                h2, a2 = map(int, s2.split(':'))

            # ГЛАВНАЯ ПРОВЕРКА: Сумма периодов должна СТРОГО совпадать с общим счетом
            if (h1 + h2 != total_h) or (a1 + a2 != total_a):
                # logger.info(f"СКИП {m_id}: Разрыв данных! Общий {total_h}:{total_a}, Периоды {h1}:{a1} + {h2}:{a2}")
                return None
            
            # Доп. проверка: если общий счет не 0:0, а первый период 0:0 и второго еще нет - это лаг
            if (total_h + total_a > 0) and (h1 + a1 == 0) and (h2 + a2 == 0):
                return None

        except Exception as e:
            return None

        # ОФОРМЛЕНИЕ
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
                f"└ 1-й: `{h1}:{a1}`\n"
                f"└ 2-й: `{h2}:{a2}`"
            )
        }

    async def run(self):
        logger.info("=== HOCKEY SCANNER v9.0 (IRON LOGIC) STARTED ===")
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
                                        logger.info(f"✅ Отправлено: {m_id} ({state})")
                                    except TelegramRetryAfter as e:
                                        await asyncio.sleep(e.retry_after)
                                    except Exception as e:
                                        logger.error(f"Ошибка TG: {e}")

                    if len(self.sent_cache) > 600: self.sent_cache.clear()

                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                
                await asyncio.sleep(30)

if __name__ == "__main__":
    scanner = HockeyScanner()
    asyncio.run(scanner.run())
