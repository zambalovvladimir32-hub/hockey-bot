import asyncio
import os
import aiohttp
import re

# --- НОВЫЕ ДАННЫЕ ПРОКСИ ---
# Формат: http://username:password@ip:port
NEW_PROXY = "http://EyHqKx:17G5qf@196.17.64.151:8000"

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def test_proxy():
    """Проверка: видит ли прокси интернет"""
    async with aiohttp.ClientSession() as session:
        try:
            # Сначала проверяем на простом сайте
            async with session.get("http://icanhazip.com", proxy=NEW_PROXY, timeout=10) as resp:
                ip = (await resp.text()).strip()
                print(f"✅ ТЕСТ ПРОКСИ ПРОЙДЕН! Твой IP в сети: {ip}", flush=True)
                return True
        except Exception as e:
            print(f"❌ ТЕСТ ПРОКСИ ПРОВАЛЕН: {e}", flush=True)
            return False

async def get_data(endpoint):
    """Прямой запрос к узлам данных Flashscore"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-fsign": "SW9D1eZo",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.ru/"
    }
    async with aiohttp.ClientSession() as session:
        try:
            url = f"https://d.flashscore.ru/x/feed/{endpoint}"
            async with session.get(url, headers=headers, proxy=NEW_PROXY, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.text()
                print(f"📡 Ошибка сервера: {resp.status}", flush=True)
        except Exception as e:
            print(f"📡 Ошибка соединения: {e}", flush=True)
    return None

async def main():
    print(f"--- 🦾 БОТ V46: ТЕСТ НОВОГО ПРОКСИ ---", flush=True)
    
    # 1. Сначала проверяем связь
    if not await test_proxy():
        print("⛔️ С таким прокси ловить нечего. Проверь логин/пароль.", flush=True)
        return

    while True:
        try:
            print("\n📡 Скребу хоккейный лайв-поток...", flush=True)
            # f_4_1_2_ru_1 — Код хоккейного лайва
            raw_data = await get_data("f_4_1_2_ru_1")
            
            if raw_data and "~AA÷" in raw_data:
                matches = raw_data.split("~AA÷")
                found = len(matches) - 1
                print(f"✅ УСПЕХ! Нашел событий: {found}", flush=True)
                
                for m in matches[1:]:
                    # Если находим перерыв P1 (код 36)
                    if "¬AC÷36¬" in m or "перерыв" in m.lower():
                        m_id = m.split("¬")[0]
                        teams = re.findall(r"A[EF]÷([^¬]+)", m)
                        if len(teams) >= 2:
                            print(f"   🎯 ПЕРЕРЫВ: {teams[0]} - {teams[1]} (ID: {m_id})", flush=True)
            else:
                print("❌ Данные не получены. Возможно, Flashscore сменил ключи.", flush=True)

            await asyncio.sleep(60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}", flush=True)
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
