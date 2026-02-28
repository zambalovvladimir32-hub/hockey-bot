import asyncio
import os
import logging
import sys
import time
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

# =================================================================
# 1. НАСТРОЙКА ЛОГИРОВАНИЯ И КОНФИГ
# =================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("hockey_system.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HockeySystem")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)

# =================================================================
# 2. ЯДРО ПАРСЕРА (БЕЗ СОКРАЩЕНИЙ)
# =================================================================
class HockeyScanner:
    def __init__(self):
        self.urls = [
            "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1",
            "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/",
        }
        self.sent_cache = {} # Храним состояние {ID: СЧЕТ_СТАТУС}

    def _get_value(self, block, tag):
        """Безопасное извлечение значения тега из строки Flashscore."""
        try:
            parts = block.split(tag)
            if len(parts) > 1:
                return parts[1].split('¬')[0]
            return ""
        except Exception:
            return ""

    async def fetch_data(self):
        """Загрузка сырых данных с обработкой прокси и таймаутов."""
        combined_raw = ""
        async with AsyncSession(impersonate="chrome110") as session:
            proxies = {"http": PROXY, "https": PROXY} if PROXY else None
            for url in self.urls:
                try:
                    # Добавляем временную метку, чтобы избежать кэширования на сервере
                    timestamp_url = f"{url}?t={int(time.time())}"
                    response = await session.get(timestamp_url, headers=self.headers, proxies=proxies, timeout=20)
                    if response.status_code == 200:
                        combined_raw += response.text
                    else:
                        logger.error(f"Сервер вернул ошибку {response.status_code} для {url}")
                except Exception as e:
                    logger.error(f"Ошибка сети при запросе к {url}: {e}")
        return combined_raw

    def process_raw_to_matches(self, raw_data):
        """Разбор сырой строки в список проверенных матчей."""
        results = []
        if not raw_data:
            return results

        # Делим данные по лигам (тег ZA)
        league_sections = raw_data.split('~ZA÷')
        
        for section in league_sections[1:]:
            try:
                league_name = section.split('¬')[0]
                # Делим лигу на матчи (тег AA)
                match_blocks = section.split('~AA÷')
                
                for block in match_blocks[1:]:
                    if 'AB÷' not in block:
                        continue

                    # --- ИЗВЛЕЧЕНИЕ ДАННЫХ ---
                    match_id = block.split('¬')[0]
                    status_live = self._get_value(block, 'AB÷') # 2/3 - Live/Перерыв
                    ac_code = self._get_value(block, 'AC÷')     # Код периода
                    timer_text = self._get_value(block, 'TT÷').upper() # Текст (P1, 25', Pause)
                    
                    # Счет (Общий и по периодам)
                    full_h = self._get_tag_int(block, 'AG÷')
                    full_a = self._get_tag_int(block, 'AH÷')
                    
                    score_p1 = self._get_value(block, 'XA÷') # Счет 1-го периода
                    score_p2 = self._get_value(block, 'XB÷') # Счет 2-го периода
                    score_p3 = self._get_value(block, 'XC÷') # Счет 3-го периода (Детектор 3-го пер)

                    # --- МНОГОУРОВНЕВАЯ ФИЛЬТРАЦИЯ ---

                    # 1. ЖЕСТКИЙ БЛОК 3-ГО ПЕРИОДА
                    # Если есть XC (счет 3-го), коды 3, 46 (пауза 2-3), или текст P3/3-Й
                    if score_p3 or ac_code in ['3', '46', '6', '4', '5'] or "P3" in timer_text or "3-Й" in timer_text:
                        continue

                    # 2. ЖЕСТКИЙ БЛОК 1-ГО ПЕРИОДА
                    # Если нет счета 1-го периода (XA) или код 1/текст P1 - скипаем
                    if not score_p1 or ac_code == '1' or "P1" in timer_text or "1-Й" in timer_text:
                        continue

                    # 3. МАТЕМАТИЧЕСКАЯ ПРОВЕРКА (Защита от вранья Flashscore)
                    # Считаем сумму голов из подтвержденных периодов 1 и 2
                    try:
                        h1, a1 = map(int, score_p1.split(':'))
                        h2, a2 = map(int, (score_p2 if score_p2 else "0:0").split(':'))
                        
                        # Если (1-й + 2-й) != Общий счет, значит уже забили в 3-м периоде. БАНИМ.
                        if (h1 + h2 != full_h) or (a1 + a2 != full_a):
                            logger.debug(f"Матч {match_id} отклонен: математика счета не сходится ({h1+h2} != {full_h})")
                            continue
                    except Exception:
                        continue

                    # 4. ОПРЕДЕЛЕНИЕ СТАТУСА (Перерыв или Ход игры)
                    is_break = (ac_code == '45' or "ПЕРЕРЫВ" in timer_text or "PAUSE" in timer_text)
                    
                    home_team = self._get_value(block, 'AE÷')
                    away_team = self._get_value(block, 'AF÷')

                    # Формируем финальные данные
                    status_str = "☕️ ПЕРЕРЫВ (1-2)" if is_break else f"⏱ 2-Й ПЕРИОД [{timer_text}]"
                    
                    results.append({
                        'id': match_id,
                        'state_key': f"{full_h}:{full_a}_{is_break}",
                        'text': (
                            f"🏒 **{home_team} {full_h}:{full_a} {away_team}**\n"
                            f"🏆 {league_name}\n"
                            f"{status_str}\n\n"
                            f"📊 **Детализация:**\n"
                            f"└ 1-й период: `{score_p1}`\n"
                            f"└ 2-й период: `{score_p2 if score_p2 else '0:0'}`"
                        )
                    })
            except Exception as e:
                logger.error(f"Ошибка парсинга блока лиги: {e}")
        return results

    def _get_tag_int(self, block, tag):
        val = self._get_value(block, tag)
        return int(val) if val.isdigit() else 0

# =================================================================
# 3. ГЛАВНЫЙ ЦИКЛ УПРАВЛЕНИЯ
# =================================================================
async def main_loop():
    scanner = HockeyScanner()
    logger.info("✅ Глубокий сканер запущен. Ожидание матчей...")

    while True:
        try:
            # Получаем свежие данные
            raw_html = await scanner.fetch_data()
            
            # Анализируем
            found_matches = scanner.process_raw_to_matches(raw_html)
            
            for match in found_matches:
                m_id = match
