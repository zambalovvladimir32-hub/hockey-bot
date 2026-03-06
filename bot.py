import asyncio
import os
from curl_cffi.requests import AsyncSession

# --- КОНФИГ ---
PROXY_URL = os.getenv("PROXY_URL", "") 

async def fetch_api(session, url, headers):
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    try:
        response = await session.get(url, headers=headers, proxies=proxies, impersonate="chrome124", timeout=15)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

async def main():
    print(f"--- ☢️ БОТ V101: ПРОБИВ ФИДОВ ---", flush=True)
    
    headers = {
        "x-fsign": "SW9D1eZo",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.flashscore.com/"
    }

    async with AsyncSession() as session:
        # Тест 1: Лайв
        print("\n📡 ТЕСТ 1: Запрос Лайв-матчей...", flush=True)
        live_url = "https://d.flashscore.com/x/feed/f_4_1_2_ru_1"
        code1, text1 = await fetch_api(session, live_url, headers)
        print(f"   [HTTP {code1}] Ответ: {text1[:100]}", flush=True)

        # Тест 2: Все матчи за сегодня (цифра 0 вместо 1)
        print("\n📡 ТЕСТ 2: Запрос ВСЕХ матчей за сегодня...", flush=True)
        today_url = "https://d.flashscore.com/x/feed/f_4_0_3_ru_1"
        code2, text2 = await fetch_api(session, today_url, headers)
        print(f"   [HTTP {code2}] Ответ: {text2[:100]}", flush=True)

        # Анализ
        if "~AA÷" in text2:
            print("\n✅ ВЫВОД: Защита пробита на 100%! В лайве сейчас просто физически нет матчей. Ждем вечера.", flush=True)
        elif text1 == "0" and text2 == "0":
            print("\n❌ ВЫВОД: Ключ 'x-fsign' устарел или Flashscore требует куки. Нужно парсить токен динамически.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
