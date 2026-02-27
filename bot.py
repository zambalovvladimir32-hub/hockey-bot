import asyncio
import os
import logging
import sys
from aiogram import Bot
from curl_cffi.requests import AsyncSession

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PROXY = os.getenv("PROXY_URL")

bot = Bot(token=TOKEN)

# ВАЖНО: Ссылка f_4_0_3 запрашивает ВСЕ лиги, а не только избранные
URL = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/hockey/",
    }
    try:
        async with AsyncSession(impersonate="chrome110") as s:
            proxies = {"http": PROXY, "https": PROXY} if PROXY else None
            # Используем метку времени для обхода кэша
            r = await s.get(f"{URL}?v={int(asyncio.get_event_loop().time())}", headers=headers, proxies=proxies, timeout=25)
            if r.status_code == 200 and len(r.text) > 1000:
                logger.info(f"📡 Получен полный пакет: {len(r.text)} байт")
                return r.text
    except Exception as e:
        logger.error(f"❌ Сбой сети: {e}")
    return None

def parse(data):
    matches = []
    # Flashscore делит матчи через ~AA÷
    blocks = data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Если в блоке нет счета (AG), значит это не живой матч или ошибка данных
            if 'AG÷' not in block:
                continue

            home = block.split('AE÷')[1].split('¬')[0]
            away = block.split('AF÷')[1].split('¬')[0]
            s_h = block.split('AG÷')[1].split('¬')[0]
            s_a = block.split('AH÷')[1].split('¬')[0]
            
            # Определяем статус периода
            p_text = "LIVE"
            if 'JS÷' in block:
                val = block.split('JS÷')[1].split('¬')[0]
                status_codes = {'1': '1-й пер.', '2': '2-й пер.', '3': '3-й пер.', '6': 'ПЕРЕРЫВ', '10': 'ОТ', '11': 'Буллиты'}
                p_text = status_codes.get(val, "LIVE")

            matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ {p_text}")
        except:
            continue
    return matches

async def main():
    logger.info("🚀 ГЛОБАЛЬНЫЙ МОНИТОРИНГ ЗАПУЩЕН")
    # Храним последние версии матчей, чтобы не слать одно и то же
    last_state = {}

    while True:
        raw_data = await get_data()
        if raw_data:
            found_matches = parse(raw_data)
            logger.info(f"🔎 Найдено в эфире: {len(found_matches)} матчей")
            
            updates = []
            for m in found_matches:
                # Ключ - это названия команд
                key = m.split('\n')[0]
                # Если счет или статус изменились - шлем апдейт
                if key not in last_state or last_state[key] != m:
                    updates.append(m)
                    last_state[key] = m
            
            if updates:
                # Разбиваем на сообщения по 8 матчей
                for i in range(0, len(updates), 8):
                    chunk = updates[i:i+8]
                    text = "🥅 **ОБНОВЛЕНИЕ LIVE:**\n\n" + "\n\n".join(chunk)
                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"📣 Отправлено {len(updates)} обновлений")
            else:
                logger.info("⏸ Изменений в матчах пока нет.")

        if len(last_state) > 1000: last_state.clear()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
