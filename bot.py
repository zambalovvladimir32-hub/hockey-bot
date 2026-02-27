import asyncio
import os
import logging
import re
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

URL = "https://d.flashscore.ru/x/feed/f_4_0_2_ru-ru_1"
FSIGN = "SW9D1eZo" 

async def get_flashscore_data():
    headers = {
        "x-fsign": FSIGN,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with AsyncSession(impersonate="chrome120") as session:
        try:
            resp = await session.get(URL, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.text
            logger.error(f"🚫 Ошибка сервера: {resp.status_code}")
            return None
        except Exception as e:
            logger.error(f"🔥 Ошибка сети: {e}")
            return None

def parse_games(raw_data):
    if not raw_data: return []
    matches = []
    blocks = raw_data.split('~AA÷')
    
    seen_statuses = set()

    for block in blocks[1:]:
        try:
            # Превращаем блок в словарь тегов
            res = dict(re.findall(r'(\w+)÷([^¬]+)', block))
            
            home = res.get('AE', '???')
            away = res.get('AF', '???')
            
            # Собираем все поля, которые могут отвечать за период
            # Обычно это NS, TT, EP или ER
            st1 = res.get('NS', '')
            st2 = res.get('TT', '')
            st3 = res.get('EP', '')
            st4 = res.get('ER', '')
            
            current_status = f"NS:{st1}|TT:{st2}|EP:{st3}|ER:{st4}"
            seen_statuses.add(current_status)

            # ПРОВЕРКА: Если хотя бы в одном из статусных полей есть "2"
            # Но исключаем, если это просто счет (проверяем именно статус)
            is_2nd = any(res.get(key) == "2" for key in ['NS', 'TT', 'EP', 'ER', 'ST'])
            
            # Доп. проверка на текст "П2" или "2-Й" во всем блоке
            if not is_2nd:
                if "П2" in block or "P2" in block.upper() or "2ND" in block.upper():
                    is_2nd = True

            if is_2nd:
                s1, s2 = res.get('AG', '0'), res.get('AH', '0')
                msg = f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Период обнаружен! (Код: {current_status})"
                matches.append(msg)
                logger.info(f"✅ НАЙДЕНО: {home} - {away} с кодами {current_status}")
                
        except Exception as e:
            continue
    
    # Выводим в лог все уникальные комбинации статусов, что увидел бот
    if seen_statuses:
        logger.info(f"🔎 Все найденные статусы в лайве: {list(seen_statuses)[:5]}")
            
    return matches

async def main():
    logger.info("📡 ЗАПУСК ГЛУБОКОГО СКАНИРОВАНИЯ...")
    while True:
        raw = await get_flashscore_data()
        if raw:
            games = parse_games(raw)
            if games:
                report = "🥅 **LIVE: НАЙДЕН 2-Й ПЕРИОД!**\n\n" + "\n\n".join(games[:10])
                try:
                    await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
                    logger.info("📨 Сообщение отправлено в Telegram!")
                except Exception as e:
                    logger.error(f"❌ Ошибка ТГ: {e}")
            else:
                logger.info("⏳ 2-й период пока не опознан в кодах. Жду следующего тика...")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
