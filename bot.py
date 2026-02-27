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
# Ссылка на все LIVE матчи хоккея
URL = "https://www.flashscore.ru/x/feed/f_4_1_3_ru-ru_1"

async def get_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-fsign": "SW9D1eZo",
        "x-requested-with": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/",
    }
    try:
        async with AsyncSession(impersonate="chrome110") as s:
            proxies = {"http": PROXY, "https": PROXY} if PROXY else None
            # Добавляем случайное число, чтобы данные всегда были свежими
            r = await s.get(f"{URL}?v={asyncio.get_event_loop().time()}", headers=headers, proxies=proxies, timeout=20)
            if r.status_code == 200 and len(r.text) > 500:
                logger.info(f"📡 Получено {len(r.text)} байт")
                return r.text
    except Exception as e:
        logger.error(f"❌ Ошибка сети: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    for block in blocks[1:]:
        # AB÷3 — это железный признак того, что матч ИДЕТ ПРЯМО СЕЙЧАС (Live)
        # Также проверяем AB÷2 (перерыв)
        if 'AB÷3' in block or 'AB÷2' in block:
            try:
                # Названия команд
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                
                # Текущий счет
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                # Попробуем понять, какой период/минута (для красоты)
                period = "LIVE"
                if 'JS÷' in block:
                    p_val = block.split('JS÷')[1].split('¬')[0]
                    if p_val == '1': period = "1-й период"
                    elif p_val == '2': period = "2-й период"
                    elif p_val == '3': period = "3-й период"
                    elif p_val == '6': period = "Перерыв"

                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Статус: {period}")
            except:
                continue
    return matches

async def main():
    logger.info("🚀 БОТ ВКЛЮЧЕН: МОНИТОРИНГ ВСЕГО LIVE")
    reported = set()

    while True:
        raw_data = await get_data()
        if raw_data:
            found = parse(raw_data)
            
            new_to_send = []
            for m in found:
                # Создаем уникальный ключ для матча, чтобы не спамить одним и тем же
                # Если счет изменится, бот пришлет обновление (так даже лучше)
                if m not in reported:
                    new_to_send.append(m)
                    reported.add(m)
            
            if new_to_send:
                # Отправляем по 5 матчей в одном сообщении, чтобы не забанил Телеграм
                for i in range(0, len(new_to_send), 5):
                    chunk = new_to_send[i:i+5]
                    text = "🥅 **ТЕКУЩИЕ LIVE МАТЧИ:**\n\n" + "\n\n".join(chunk)
                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"📣 Отправлено новых событий: {len(new_to_send)}")
            else:
                logger.info("🔎 Живых матчей пока нет или всё уже отправлено.")

        # Очищаем память каждые 3 часа
        if len(reported) > 300: reported.clear()
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
