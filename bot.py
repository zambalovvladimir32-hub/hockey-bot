import asyncio
import os
import logging
import sys
import time
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

# 1. Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("HockeyPro_v8")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyScanner:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = {}

    def _get_val(self, block, tag):
        try:
            parts = block.split(tag)
            if len(parts) > 1:
                return parts[1].split('¬')[0]
            return ""
        except:
            return ""

    def validate_match(self, block, league):
        """Проверка матча на вшивость и лаги данных."""
        m_id = block.split('¬')[0]
        
        ac_code = self._get_val(block, 'AC÷')     # Системный статус
        timer = self._get_val(block, 'TT÷').upper() # Таймер/Статус (P2, Pause)
        
        # Общий счет из заголовка (обновляется быстрее всего)
        full_h = self._get_val(block, 'AG÷') or "0"
        full_a = self._get_val(block, 'AH÷') or "0"
        
        # Детальный счет по периодам
        s1 = self._get_val(block, 'XA÷') # 1-й
        s2 = self._get_val(block, 'XB÷') # 2-й
        s3 = self._get_val(block, 'XC÷') # 3-й

        # --- ЖЕСТКИЕ ФИЛЬТРЫ ---
        
        # 1. Если есть счет за 3-й период (XC) или статус 3-го — СКИП
        if s3 or ac_code in ['3', '46', '6'] or "P3" in timer:
            return None

        # 2. Если 1-й период еще идет или нет счета за него — СКИП
        if not s1 or ac_code == '1' or "P1" in timer:
            return None

        # 3. МАТЕМАТИЧЕСКАЯ ПРОВЕРКА (Анти-Тохоку)
        try:
            h1, a1 = map(int, s1.split(':'))
            h2, a2 = map(int, (s2 if s2 else "0:0").split(':'))
            
            # Сумма за 1 и 2 периоды
            sum_h = h1 + h2
            sum_a = a1 + a2
            
            # Если сумма не бьется с общим счетом — значит Flashscore лагает (уже забили в 3-м)
            if sum_h != int(full_h) or sum_a != int(full_a):
                # logger.info(f"DEBUG: Match {m_id} rejected. Sum {sum_h}:{sum_a} != Full {full_h}:{full_a}")
                return None
        except:
            return None

        # Определение статуса (Перерыв или Игра)
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
        logger.info("=== HOCKEY SCANNER v8.0 (TOTAL CONTROL) STARTED ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    # Читинское время (GMT+9) учитывается через метку времени в логах Railway (UTC)
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
