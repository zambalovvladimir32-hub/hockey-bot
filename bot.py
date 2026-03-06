import asyncio
import os
import re
from curl_cffi.requests import AsyncSession

# --- КОНФИГ ---
PROXY_URL = os.getenv("PROXY_URL", "") 

async def get_fresh_token(session):
    """Секретная миссия: воруем свежий токен с главной страницы"""
    print("\n🕵️ Ворую свежий ключ авторизации (x-fsign)...", flush=True)
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    try:
        # Заходим на главную страницу, чтобы получить куки и код
        response = await session.get("https://www.flashscore.com/", proxies=proxies, impersonate="chrome124", timeout=15)
        
        # Ищем переменную feed_sign в JSON-конфиге страницы
        match = re.search(r'"feed_sign"\s*:\s*"([^"]+)"', response.text)
        if match:
            token = match.group(1)
            print(f"   🔑 Успех! Свежий ключ добыт: {token}", flush=True)
            return token
        else:
            print("   ❌ Ключ не найден в коде страницы. Flashscore обновил дизайн?", flush=True)
            return None
    except Exception as e:
        print(f"   ⚠️ Ошибка при получении ключа: {e}", flush=True)
        return None

async def fetch_api(session, url, headers):
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    try:
        response = await session.get(url, headers=headers, proxies=proxies, impersonate="chrome124", timeout=15)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

async def main():
    print(f"--- ☢️ БОТ V102: THE KEYMASTER (ДИНАМИЧЕСКИЙ ТОКЕН) ---", flush=True)
    
    # AsyncSession автоматически сохранит все cookies от первой загрузки сайта
    async with AsyncSession() as session:
        while True:
            # 1. Добываем свежий ключ
            token = await get_fresh_token(session)
            
            if not token:
                print("💤 Жду 30 секунд и пробую снова...", flush=True)
                await asyncio.sleep(30)
                continue
                
            # Собираем правильные заголовки
            headers = {
                "x-fsign": token,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.flashscore.com/"
            }

            # 2. ТЕСТ: Лайв
            print("\n📡 Запрашиваю Лайв-матчи со свежим ключом...", flush=True)
            live_url = "https://d.flashscore.com/x/feed/f_4_1_2_ru_1"
            code1, text1 = await fetch_api(session, live_url, headers)
            print(f"   [HTTP {code1}] Ответ: {text1[:100]}", flush=True)

            # 3. ТЕСТ: Все матчи сегодня
            print("\n📡 Запрашиваю Все матчи за сегодня...", flush=True)
            today_url = "https://d.flashscore.com/x/feed/f_4_0_3_ru_1"
            code2, text2 = await fetch_api(session, today_url, headers)
            print(f"   [HTTP {code2}] Ответ: {text2[:100]}", flush=True)

            # Если мы пробили защиту, выходим из цикла тестов (дальше будем писать рабочий парсинг)
            if "~AA÷" in text2:
                print("\n✅ БИНГО! МЫ ВЗЛОМАЛИ БАЗУ FLASHSCORE!", flush=True)
                break
            else:
                print("\n❌ Ответ всё еще пустой (0). Либо мы не угадали URL фида, либо нужна дополнительная защита.", flush=True)
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
