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
# Самый полный фид хоккея
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
            # Параметр ?t нужен, чтобы данные не кешировались
            r = await s.get(f"{URL}?t={int(asyncio.get_event_loop().time())}", headers=headers, proxies=proxies, timeout=20)
            if r.status_code == 200 and len(r.text) > 1000:
                return r.text
    except Exception as e:
        logger.error(f"❌ Ошибка сети: {e}")
    return None

def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Вытаскиваем название команд (обязательно)
            home = block.split('AE÷')[1].split('¬')[0]
            away = block.split('AF÷')[1].split('¬')[0]
            
            # Вытаскиваем счет (если счета нет, значит матч не начался — пропускаем)
            if 'AG÷' not in block:
                continue
                
            s_h = block.split('AG÷')[1].split('¬')[0]
            s_a = block.split('AH÷')[1].split('¬')[0]
            
            # Определяем статус (Период или Пауза)
            status = "LIVE"
            if 'JS÷' in block:
                val = block.split('JS÷')[1].split('¬')[0]
                # Маппинг кодов Flashscore
                status_map = {'1': '1-й период', '2': '2-й период', '3': '3-й период', '6': 'ПЕРЕРЫВ', '10': 'ОТ', '11': 'Буллиты'}
                status = status_map.get(val, "LIVE")
            
            # Если есть время периода (минута)
            if 'BE÷' in block:
                status += f" ({block.split('BE÷')[1].split('¬')[0]}')"

            matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ {status}")
        except:
            continue
    return matches

async def main():
    logger.info("🚀 МОНИТОРИНГ ВСЕХ LIVE СОБЫТИЙ ЗАПУЩЕН")
    reported = {} # Используем словарь, чтобы следить за изменением счета

    while True:
        raw_data = await get_data()
        if raw_data:
            found = parse(raw_data)
            logger.info(f"🔎 Найдено в эфире: {len(found)} матчей")
            
            new_updates = []
            for m in found:
                # Извлекаем "ключ" матча (команды), чтобы не слать дубли
                match_id = m.split('\n')[0] 
                # Если матча нет в списке или в нем изменился счет/статус
                if match_id not in reported or reported[match_id] != m:
                    new_updates.append(m)
                    reported[match_id] = m
            
            if new_updates:
                # Шлем матчи пачками по 10 штук
                for i in range(0, len(new_updates), 10):
                    chunk = new_updates[i:i+10]
                    text = "🥅 **ОБНОВЛЕНИЕ LIVE:**\n\n" + "\n\n".join(chunk)
                    await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
                logger.info(f"📣 Отправлено обновлений: {len(new_updates)}")
        
        # Чтобы словарь не раздувался, чистим его, если там больше 500 записей
        if len(reported) > 500: reported.clear()
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
