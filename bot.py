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
        # Опрашиваем все доступные лайв-матчи по хоккею
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_cache = set() # Теперь храним просто ID матчей, так как шлем только 1 раз в перерыв

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
        
        # Код 45 - перерыв между 1 и 2 периодом. 
        # Если статус 2 (идет 2-й период) или любой другой - сразу пропускаем!
        is_break = (ac_code == '45' or "ПЕРЕРЫВ" in timer or "PAUSE" in timer)
        
        # Исключаем перерыв перед 3-м периодом (код 46) или конец матча
        if not is_break or ac_code in ['46', '3', '6', '2']:
            return None

        # 2. ПРОВЕРКА СЧЕТА 1-ГО ПЕРИОДА
        ba = self._get_val(block, 'BA÷') # Голы хозяев в 1-м
        bb = self._get_val(block, 'BB÷') # Голы гостей в 1-м
        
        if not ba or not bb:
            return None # 1-й период еще не завершен, данных нет

        try:
            h1 = int(ba)
            a1 = int(bb)
        except ValueError:
            return None

        # 3. ФИЛЬТР НУЖНЫХ СЧЕТОВ: 0:0, 1:0, 0:1
        valid_scores = [(0, 0), (1, 0), (0, 1)]
        if (h1, a1) not in valid_scores:
            return None # Счет другой (например 1:1 или 2:0) - пропускаем

        # ОФОРМЛЕНИЕ УВЕДОМЛЕНИЯ
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
        logger.info("=== HOCKEY BREAK SCANNER v11.0 STARTED ===")
        logger.info("Условия: Любая лига | Только Перерыв 1-2 | Счет 0:0, 1:0, 0:1")
        
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
                                m_id = match['id']
                                
                                # Отправляем только если еще не присылали этот матч
                                if m_id not in self.sent_cache:
                                    try:
                                        await bot.send_message(CHANNEL_ID, match['text'], parse_mode="Markdown")
                                        self.sent_cache.add(m_id)
                                        logger.info(f"✅ Отправлено: {m_id} (Счет 1-го периода подходит)")
                                        await asyncio.sleep(1) # Защита от спам-блока Telegram
                                    except TelegramRetryAfter as e:
                                        await asyncio.sleep(e.retry_after)
                                    except Exception as e:
                                        logger.error(f"Ошибка отправки TG: {e}")

                    # Очистка памяти каждые 12-24 часа (500 матчей хватит за глаза)
                    if len(self.sent_cache) > 500: 
                        self.sent_cache.clear()
                        logger.info("🧹 Кэш отправленных матчей очищен")

                except Exception as e:
                    logger.error(f"Ошибка цикла парсинга: {e}")
                
                # Интервал опроса - 30 секунд
                await asyncio.sleep(30)

if __name__ == "__main__":
    scanner = HockeyScanner()
    asyncio.run(scanner.run())
