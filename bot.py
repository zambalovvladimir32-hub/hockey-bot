import asyncio
import os
import logging
import sys
import time
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from curl_cffi.requests import AsyncSession

# =================================================================
# 1. НАСТРОЙКА ЛОГИРОВАНИЯ (БЕЗ СОКРАЩЕНИЙ)
# =================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HockeyProfessional")

# --- ДАННЫЕ АВТОРИЗАЦИИ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# =================================================================
# 2. ЯДРО ПАРСЕРА (ПОЛНАЯ ЛОГИКА БЕЗ СКРЫТЫХ БЛОКОВ)
# =================================================================
class HockeyScanner:
    def __init__(self):
        # Используем основной фид Flashscore
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
            "Referer": "https://www.flashscore.ru/"
        }
        self.sent_matches = {} # Словарь для отслеживания состояний {id: state}

    def get_tag_value(self, block, tag):
        """Извлекает значение тега из сырой строки Flashscore."""
        try:
            parts = block.split(tag)
            if len(parts) > 1:
                return parts[1].split('¬')[0]
            return ""
        except Exception:
            return ""

    def validate_and_parse(self, block, league_name):
        """Глубокая проверка матча на соответствие 2-му периоду."""
        try:
            match_id = block.split('¬')[0]
            
            # 1. ИЗВЛЕЧЕНИЕ ТЕХНИЧЕСКИХ СТАТУСОВ
            ac_code = self.get_tag_value(block, 'AC÷')     # Системный код периода
            timer_text = self.get_tag_value(block, 'TT÷').upper() # Текст (P1, 20', Pause)
            cr_num = self.get_tag_value(block, 'CR÷')      # Номер текущего периода
            
            # 2. ИЗВЛЕЧЕНИЕ СЧЕТА
            full_score_home = self.get_tag_value(block, 'AG÷') or "0"
            full_score_away = self.get_tag_value(block, 'AH÷') or "0"
            
            score_p1 = self.get_tag_value(block, 'XA÷') # Счет 1-го периода (напр. 1:1)
            score_p2 = self.get_tag_value(block, 'XB÷') # Счет 2-го периода
            score_p3 = self.get_tag_value(block, 'XC÷') # Счет 3-го периода (Детектор 3-го пер)

            # --- ЖЕСТКИЕ ФИЛЬТРЫ ИСКЛЮЧЕНИЯ ---

            # А. БАН 3-ГО ПЕРИОДА (если есть XC, коды 3, 46 или текст P3)
            # 46 - это перерыв перед 3-м периодом. Нам он не нужен.
            if score_p3 or ac_code in ['3', '46', '6', '4', '5'] or cr_num == '3' or "P3" in timer_text:
                return None

            # Б. БАН 1-ГО ПЕРИОДА (он должен быть завершен - тег XA должен существовать)
            if not score_p1 or ac_code == '1' or cr_num == '1' or "P1" in timer_text:
                return None

            # В. МАТЕМАТИЧЕСКАЯ ПРОВЕРКА (Защита от вранья сервера в Азиатской лиге)
            # Мы складываем голы первого и второго периода. Если сумма не равна общему счету,
            # значит забивали уже в 3-м, и матч нам не подходит.
            try:
                h1, a1 = map(int, score_p1.split(':'))
                h2, a2 = map(int, (score_p2 if score_p2 else "0:0").split(':'))
                
                total_h = int(full_score_home)
                total_a = int(full_score_away)
                
                if (h1 + h2 != total_h) or (a1 + a2 != total_a):
                    #logger.debug(f"Матч {match_id} отклонен: математика голов не сходится ({h1+h2} != {total_h})")
                    return None
            except Exception:
                return None

            # --- ЕСЛИ ПРОШЛИ ПРОВЕРКИ — ЭТО НАШ МАТЧ ---
            
            # Определяем, перерыв сейчас или идет игра
            # Код 45 - это гарантированный перерыв между 1 и 2 периодом
            is_break = (ac_code == '45' or "ПЕРЕРЫВ" in timer_text or "PAUSE" in timer_text)
            
            home_team = self.get_tag_value(block, 'AE÷')
            away_team = self.get_tag_value(block, 'AF÷')

            status_label = "☕️ ПЕРЕРЫВ (1-2)" if is_break else f"⏱ 2-Й ПЕРИОД [{timer_text}]"
            
            return {
                'id': match_id,
                'state_key': f"{full_score_home}:{full_score_away}_{is_break}",
                'text': (
                    f"🏒 **{home_team} {full_score_home}:{full_score_away} {away_team}**\n"
                    f"🏆 {league_name}\n"
                    f"{status_label}\n\n"
                    f"📊 **Счет по периодам:**\n"
                    f"└ 1-й: `{score_p1}`\n"
                    f"└ 2-й: `{score_p2 if score_p2 else '0:0'}`"
                )
            }
        except Exception as e:
            return None

    async def start_scanning(self):
        """Главный цикл работы бота."""
        logger.info("🚀 СКАНЕР ЗАПУЩЕН В ПОЛНОМ РЕЖИМЕ (v7.0)")
        
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    # Запрос к Flashscore с защитой от кэширования
                    current_ts = int(time.time())
                    response = await session.get(f"{self.url}?t={current_ts}", headers=self.headers, timeout=20)
                    
                    if response.status_code != 200:
                        logger.warning(f"Ошибка сервера: {response.status_code}. Ждем 5 сек...")
                        await asyncio.sleep(5)
                        continue

                    # Парсинг данных
                    sections = response.text.split('~ZA÷')
                    for section in sections[1:]:
                        league = section.split('¬')[0]
                        games = section.split('~AA÷')
                        
                        for game_block in games[1:]:
                            match_data = self.validate_and_parse(game_block, league)
                            
                            if match_data:
                                m_id = match_data['id']
                                current_state = match_data['state_key']
                                
                                # Отправляем, если матч новый или изменился счет/статус
                                if self.sent_matches.get(m_id) != current_state:
                                    try:
                                        await bot.send_message(CHANNEL_ID, match_data['text'], parse_mode="Markdown")
                                        self.sent_matches[m_id] = current_state
                                        logger.info(f"✅ СООБЩЕНИЕ ОТПРАВЛЕНО: {m_id}")
                                        await asyncio.sleep(1) # Защита от Flood
                                    except TelegramRetryAfter as e:
                                        await asyncio.sleep(e.retry_after)
                                    except Exception as e:
                                        logger.error(f"Ошибка Telegram: {e}")

                    # Очистка памяти раз в 2 часа
                    if len(self.sent_matches) > 1000:
                        self.sent_matches.clear()

                except Exception as e:
                    logger.error(f"Ошибка в основном цикле: {e}")
                
                # Интервал опроса - 30 секунд
                await asyncio.sleep(30)

# =================================================================
# 3. ТОЧКА ВХОДА
# =================================================================
if __name__ == "__main__":
    scanner = HockeyScanner()
    try:
        asyncio.run(scanner.start_scanning())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
