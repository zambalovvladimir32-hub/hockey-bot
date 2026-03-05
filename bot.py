import asyncio
import os
import aiohttp
import re

# --- КОНФИГ ---
PROXY_URL = os.getenv("PROXY_URL")  # Должен быть http://user:pass@ip:port
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def get_flashscore_data(endpoint):
    """Забирает сырые данные напрямую через API Flashscore"""
    headers = {
        "x-fsign": "SW9D1eZo",  # Ключ авторизации потока
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.flashscore.ru/",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://d.flashscore.ru/x/feed/{endpoint}"
            # В aiohttp прокси передается параметром proxy в сам запрос
            async with session.get(url, headers=headers, proxy=PROXY_URL, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    print(f"📡 Сервер ответил статусом: {resp.status}")
        except Exception as e:
            print(f"📡 Ошибка соединения: {e}")
    return None

async def main():
    print(f"--- 🦾 БОТ V43: GHOST MODE (STABLE) ---", flush=True)
    
    while True:
        try:
            print("\n📡 Запрашиваю свежий поток LIVE...", flush=True)
            # f_4_2_3_ru_1 — это код ленты хоккейных лайв-матчей
            raw_data = await get_flashscore_data("f_4_2_3_ru_1")
            
            if not raw_data:
                print("❌ Поток пуст или прокси заблокирован.", flush=True)
            else:
                # Flashscore разделяет матчи меткой ~AA÷
                matches = raw_data.split("~AA÷")
                found_count = len(matches) - 1
                print(f"📊 В потоке событий: {found_count}", flush=True)
                
                if found_count > 0:
                    for m in matches[1:]:
                        try:
                            # Парсим ID матча и команды из сырого текста
                            m_id = m.split("¬")[0]
                            # AC÷36 — код перерыва во Flashscore
                            if "¬AC÷36¬" in m or "перерыв" in m.lower():
                                home = re.search(r"AE÷([^¬]+)", m).group(1)
                                away = re.search(r"AF÷([^¬]+)", m).group(1)
                                score_h = re.search(r"AG÷(\d+)", m)
                                score_a = re.search(r"AH÷(\d+)", m)
                                
                                if score_h and score_a:
                                    sc_h, sc_a = int(score_h.group(1)), int(score_a.group(2))
                                    if (sc_h + sc_a) <= 1:
                                        print(f"   🎯 ПЕРЕРЫВ: {home} {sc_h}:{sc_a} {away} (ID: {m_id})", flush=True)
                                        # Тут бот может запросить статку конкретно по m_id
                        except: continue
                else:
                    print("🧐 Поток получен, но активных матчей в нем сейчас нет.")

            await asyncio.sleep(60)
        except Exception as e:
            print(f"⚠️ Ошибка цикла: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
