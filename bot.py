import asyncio
import os
import logging
import sys
import time
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

# Настройка подробного логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("hockey_scanner.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HockeyBot")

bot = Bot(token=TOKEN)

# --- КЛАСС ПАРСЕРА (ЯДРО) ---
class HockeyParser:
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

    async def get_raw_data(self):
        """Получение данных с защитой от сбоев и кэширования."""
        combined = ""
        async with AsyncSession(impersonate="chrome110") as session:
            proxies = {"http": PROXY, "https": PROXY} if PROXY else None
            for url in self.urls:
                try:
                    # Cache-buster: t=текущая секунда
                    ts_url = f"{url}?t={int(time.time())}"
                    response = await session.get(ts_url, headers=self.headers, proxies=proxies, timeout=25)
                    if response.status_code == 200:
                        combined += response.text
                    else:
                        logger.error(f"Ошибка HTTP {response.status_code} на {url}")
                except Exception as e:
                    logger.error(f"Сетевой сбой: {e}")
        return combined

    def parse_matches(self, data):
        """Основная логика фильтрации 2-го периода."""
        valid_matches = []
        if not data: return valid_matches

        # Делим на лиги
        leagues = data.split('~ZA÷')
        for league_block in leagues[1:]:
            try:
                league_name = league_block.split('¬')[0]
                # Делим лигу на отдельные матчи
                games = league_block.split('~AA÷')
                
                for game in games[1:]:
                    if 'AB÷' not in game: continue
                    
                    # 1. СТАТУСЫ (Системные коды)
                    ab = self._get_tag(game, 'AB÷') # 2/3 - Live
                    ac = self._get_tag(game, 'AC÷') # Код периода (45-пер1, 2-идет2, 46-пер2)
                    cr = self._get_tag(game, 'CR÷') # Номер периода (1, 2, 3)
                    tt = self._get_tag(game, 'TT÷').upper() # Текст (10', П2, P3)

                    # 2. ЖЕСТКИЕ БАНЫ (Чтобы не было 3-го периода как на скринах)
                    # Если есть счет 3-го периода (XC) или коды 3-го периода - В МУСОР
                    if 'XC÷' in game or ac in ['3', '46', '6', '4', '5'] or cr == '3':
                        continue
                    if any(x in tt for x in ["P3", "3-Й", "3RD", "FIN", "ЗАВЕРШЕН"]):
                        continue

                    # 3. ПРОВЕРКА: ЭТО 1-Й ПЕРИОД? (Тоже баним)
                    # Если XA (счет 1-го пер) еще нет - значит 1-й период еще идет
                    if 'XA÷' not in game or ac == '1' or cr == '1' or "1-Й" in tt:
                        continue

                    # 4. ИДЕНТИФИКАЦИЯ НУЖНОЙ ФАЗЫ
                    # Мы здесь, значит 1-й период кончился, а 3-й еще не начался.
                    is_break = (ac == '45' or "ПЕРЕРЫВ" in tt or "PAUSE" in tt)
                    
                    # 5. СБОР ДАННЫХ
                    home = self._get_tag(game, 'AE÷')
                    away = self._get_tag(game, 'AF÷')
                    total_h = self._get_tag(game, 'AG÷') or "0"
                    total_a = self._get_tag(game, 'AH÷') or "0"
                    
                    # Счет периодов
                    s1 = self._get_tag(game, 'XA÷') or "0:0"
                    s2 = self._get_tag(game, 'XB÷') or "0:0"

                    # 6. ВАЛИДАЦИЯ СЧЕТА (Защита от "счет за 2-й период в первом")
                    # Проверяем, что общий счет не меньше счета 1-го периода
                    try:
                        h1, a1 = map(int, s1.split(':'))
                        if int(total_h) < h1 or int(total_a) < a1:
                            continue # Ошибка данных, пропускаем
                    except: pass

                    status_label = "☕️ ПЕРЕРЫВ (1-2)" if is_break else f"⏱ 2-Й ПЕРИОД [{tt}]"

                    valid_matches.append({
                        'id': game.split('¬')[0],
                        'state_key': f"{total_h}:{total_a}_{is_break}",
                        'text': (
                            f"🏒 **{home} {total_h}:{total_a} {away}**\n"
                            f"🏆 {league_name}\n"
                            f"{status_label}\n\n"
                            f"📊 **Счет по периодам:**\n"
                            f"└ 1-й: `{s1.replace(':', ' : ')}`\n"
                            f"└ 2-й: `{s2.replace(':', ' : ')}`"
                        )
                    })
            except Exception as e:
                logger.debug(f"Ошибка парсинга блока: {e}")
                continue
        return valid_matches

    def _get_tag(self, block, tag):
        """Вспомогательная функция для безопасного извлечения тегов."""
        try:
            return block.split(tag)[1].split('¬')[0]
        except:
            return ""

# --- УПРАВЛЕНИЕ ОТПРАВКОЙ ---
class DeliveryManager:
    def __init__(self):
        self.history = {} # {id: last_state}

    def can_send(self, match):
        m_id = match['id']
        state = match['state_key']
        if m_id not in self.history or self.history[m_id] != state:
            self.history[m_id] = state
            return True
        return False

    def clean_history(self):
        if len(self.history) > 500:
            self.history.clear()

# --- ОСНОВНОЙ ЦИКЛ ---
async def run_bot():
    parser = HockeyParser()
    delivery = DeliveryManager()
    
    logger.info("=== HOCKEY SCANNER PRO v4.0 STARTED ===")
    
    while True:
        try:
            # 1. Получаем данные
            raw_data = await parser.get_raw_data()
            
            # 2. Парсим
            matches = parser.parse_matches(raw_data)
            logger.info(f"Найдено матчей во 2-м периоде/перерыве: {len(matches)}")

            # 3. Рассылаем
            for m in matches:
                if delivery.can_send(m):
                    try:
                        await bot.send_message(CHANNEL_ID, m['text'], parse_mode="Markdown")
                        logger.info(f"✅ Отправлено: {m['id']}")
                        await asyncio.sleep(1.5) # Защита от Flood Limit
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)
                    except Exception as e:
                        logger.error(f"Ошибка TG: {e}")

            delivery.clean_history()
            
        except Exception as e:
            logger.critical(f"Критическая ошибка в основном цикле: {e}")
            await asyncio.sleep(10)

        # Интервал сканирования (35 секунд оптимально для Live)
        await asyncio.sleep(35)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
