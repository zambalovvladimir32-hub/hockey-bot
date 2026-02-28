import asyncio
import os
import logging
import sys
from datetime import datetime
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bot_log.log"), # Сохраняем логи в файл
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)

URLS = [
    "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1",
    "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"
]

class MatchTracker:
    """Класс для отслеживания состояний матчей, чтобы не спамить дублями."""
    def __init__(self):
        self.sent_matches = {} # {match_id: last_status_string}

    def should_send(self, match_id, current_state):
        if match_id not in self.sent_matches:
            self.sent_matches[match_id] = current_state
            return True
        if self.sent_matches[match_id] != current_state:
            self.sent_matches[match_id] = current_state
            return True
        return False

tracker = MatchTracker()

async def fetch_flashscore_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
    }
    combined_data = ""
    async with AsyncSession(impersonate="chrome110") as session:
        proxies = {"http": PROXY, "https": PROXY} if PROXY else None
        for url in URLS:
            try:
                # Добавляем cache-buster, чтобы данные всегда были свежими
                ts = int(datetime.now().timestamp())
                response = await session.get(f"{url}?t={ts}", headers=headers, proxies=proxies, timeout=20)
                if response.status_code == 200:
                    combined_data += response.text
                else:
                    logger.warning(f"Ошибка доступа к API: {response.status_code}")
            except Exception as e:
                logger.error(f"Сетевая ошибка при запросе к {url}: {e}")
    return combined_data

def parse_hockey_logic(raw_data):
    found_matches = []
    if not raw_data: return found_matches

    # Разбивка на лиги и матчи
    sections = raw_data.split('~ZA÷')
    for section in sections[1:]:
        league_name = section.split('¬')[0]
        match_blocks = section.split('~AA÷')
        
        for block in match_blocks[1:]:
            try:
                # 1. Извлечение базовых кодов
                match_id = block.split('¬')[0]
                status_live = block.split('AB÷')[1].split('¬')[0] # 2 или 3
                period_code = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else ""
                period_num = block.split('CR÷')[1].split('¬')[0] if 'CR÷' in block else ""
                timer_text = block.split('TT÷')[1].split('¬')[0].upper() if 'TT÷' in block else ""

                # 2. ЖЕСТКИЕ БЛОКИРОВКИ (1-й и 3-й периоды)
                # XC÷ - признак начала 3-го периода
                # AC: 1(1-й), 3(3-й), 46(пауза перед 3-м), 6(конец)
                if 'XC÷' in block or period_code in ['1', '3', '46', '6', '4', '5'] or period_num in ['1', '3']:
                    continue
                
                if any(x in timer_text for x in ["P3", "3-Й", "3RD", "1-Й", "1ST"]):
                    continue

                # 3. ПРОВЕРКА ЛАЙВА
                if status_live not in ['2', '3']:
                    continue

                # 4. ВЫДЕЛЕНИЕ ЦЕЛЕВЫХ СОСТОЯНИЙ
                is_break = (period_code == '45' or "ПЕРЕРЫВ" in timer_text or "PAUSE" in timer_text)
                # Если мы прошли бан-лист выше, значит это либо перерыв 1-2, либо 2-й период
                
                # 5. СБОР ИНФОРМАЦИИ О МАТЧЕ
                home_team = block.split('AE÷')[1].split('¬')[0]
                away_team = block.split('AF÷')[1].split('¬')[0]
                score_home = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                score_away = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                
                # Счет первого периода (для красоты)
                score_p1 = block.split('XA÷')[1].split('¬')[0] if 'XA÷' in block else "0:0"

                # Формируем статус для сообщения
                display_status = "☕️ ПЕРЕРЫВ (1-2)" if is_break else "⏱ 2-Й ПЕРИОД"
                if timer_text and timer_text != "?": 
                    display_status += f" [{timer_text}]"

                # Уникальный ключ состояния: если изменится счет или статус, мы отправим апдейт
                state_key = f"{score_home}:{score_away}_{is_break}"
                
                found_matches.append({
                    'id': match_id,
                    'state': state_key,
                    'text': (
                        f"🏒 **{home_team} {score_home}:{score_away} {away_team}**\n"
                        f"🏆 {league_name}\n"
                        f"{display_status}\n"
                        f"📊 1-й период: `{score_p1}`"
                    )
                })
            except Exception:
                continue
    return found_matches

async def main():
    logger.info("🛡 СИСТЕМА МОНИТОРИНГА ВТОРОГО ПЕРИОДА ЗАПУЩЕНА")
    
    while True:
        raw_html = await fetch_flashscore_data()
        current_matches = parse_hockey_logic(raw_html)
        
        logger.info(f"Проверка: найдено {len(current_matches)} матчей в активной фазе.")

        for match in current_matches:
            if tracker.should_send(match['id'], match['state']):
                try:
                    await bot.send_message(CHANNEL_ID, match['text'], parse_mode="Markdown")
                    logger.info(f"📣 Отправлено сообщение: {match['id']}")
                    # Небольшая пауза между сообщениями в ТГ
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Ошибка отправки в Telegram: {e}")

        # Очистка старых данных раз в пару часов, чтобы словарь не раздувался
        if len(tracker.sent_matches) > 1000:
            tracker.sent_matches.clear()
            logger.info("🧹 Память трекера очищена")

        # Частота опроса. 35-40 сек — золотая середина.
        await asyncio.sleep(40)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
