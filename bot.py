import asyncio
import os
import aiohttp
import re

# --- КОНФИГ ---
PROXY_URL = os.getenv("PROXY_URL") # Формат: http://user:pass@ip:port
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def get_flashscore_data(endpoint):
    """Забирает сырые данные из бэкенда Flashscore"""
    headers = {
        "x-fsign": "SW9D1eZo", # Секретный ключ Flashscore
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.flashscore.ru/"
    }
    # Используем прокси только если он прописан
    connector = aiohttp.ProxyConnector.from_url(PROXY_URL) if PROXY_URL else None
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            url = f"https://d.flashscore.ru/x/feed/{endpoint}"
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            print(f"📡 Ошибка сети: {e}")
    return None

async def main():
    print(f"--- 🦾 БОТ V42: GHOST MODE (FLASH-API) ---", flush=True)
    
    while True:
        try:
            print("\n📡 Слушаю поток данных Flashscore...", flush=True)
            # f_4_2_ — это код для лайв-хоккея
            raw_data = await get_flashscore_data("f_4_2_3_ru_1")
            
            if not raw_data:
                print("❌ Поток пуст. Прокси всё еще тупит.", flush=True)
            else:
                # Магия парсинга сырого текста (Flashscore отдает данные через спецсимволы)
                matches = raw_data.split("~AA÷")
                print(f"📊 В потоке найдено событий: {len(matches)-1}", flush=True)
                
                for m in matches[1:]:
                    try:
                        m_id = m.split("¬")[0]
                        # Проверяем стадию (EP - перерыв)
                        if "¬AC÷36¬" in m or "перерыв" in m.lower():
                            home = re.search(r"AE÷([^¬]+)", m).group(1)
                            away = re.search(r"AF÷([^¬]+)", m).group(1)
                            score = re.search(r"AG÷([^¬]+)¬AH÷([^¬]+)", m)
                            
                            if score:
                                sc_h, sc_a = int(score.group(1)), int(score.group(2))
                                if (sc_h + sc_a) <= 1:
                                    print(f"   🎯 ПОЙМАН ПЕРЕРЫВ: {home} - {away} ({sc_h}:{sc_a})", flush=True)
                                    # Тут мы делаем второй быстрый запрос за статой этого матча
                                    # ... (логика сбора бросков)
                    except: continue

            await asyncio.sleep(60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
