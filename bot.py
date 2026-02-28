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
logger = logging.getLogger("HockeyProfessional")

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
        except Exception:
            return ""

    def validate_match(self, block, league):
        """Проверка на реальный 2-й период через математику голов."""
        m_id = block.split('¬')[0]
        
        ac_code = self._get_val(block, 'AC÷')     # Системный статус
        timer = self._get_val(block, 'TT÷').upper() # Таймер (P2, Pause и т.д.)
        
        # Общий счет
        full_h = self._get_val(block, 'AG÷') or "0"
        full_a = self._get_val(block, 'AH÷') or "0"
        
        # Счет по периодам
        s1 = self._get_val(block, 'XA÷') # 1-й период
        s2 = self._get_val(block, 'XB÷') # 2-й период
        s3 = self._get_val(block, 'XC÷') # 3-й период

        # --- ЖЕСТКИЙ ФИЛЬТР (Защита от вранья Flashscore) ---
        
        # 1. Если есть счет за 3-й период (XC) или статус 3-го периода — сразу в бан.
        if s3 or ac_code in ['3', '46', '6'] or "P3" in timer:
            return None

        # 2. Если 1-й период еще не завершен (нет XA) — в бан.
        if not s1 or ac_code == '1' or "P1" in timer:
            return None

        # 3. МАТЕМАТИЧЕСКАЯ ПРОВЕРКА (Ключевое решение)
        try:
            # Парсим голы 1-го и 2-го периодов
            h1, a1 = map(int, s1.split(':'))
            h2, a2 = map(int, (s2 if s2 else "0:0").split(':'))
            
            # Считаем сумму голов, которые ДОЛЖНЫ быть при 2-м периоде
            calc_h = h1 + h2
            calc_a = a1 + a2
            
            # Сравниваем с общим счетом (full_h : full_a). 
            # Если общий счет больше, чем сумма за 1+2 периоды — значит уже идет 3-й период!
            if calc_h != int(full_h) or calc_a != int(full_a):
                logger.info(f"🚫 Матч {m_id} отклонен: лаг статуса (Счет {full_h}:{full_a}, а 1+2 пер. = {calc_h}:{calc_a})")
                return None
        except Exception:
            return None

        # Определение типа уведомления (Перерыв или Игра)
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
                f"└ 1-й период: `{s1}`\n"
                f"└ 2-й период: `{s2 if s2 else '0:0'}`"
            )
        }

    async def run(self):
        logger.info("=== HOCKEY SCANNER v7.5 (ANTI-LAG) STARTED ===")
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    # Запрос с t=time.time() для обхода кэша Railway/Proxy
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

                    # Очистка старья
                    if len(self.sent_cache) > 600: self.sent_cache.clear()

                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                
                await asyncio.sleep(30)

if __name__ == "__main__":
    scanner = HockeyScanner()
    asyncio.run(scanner.run())
