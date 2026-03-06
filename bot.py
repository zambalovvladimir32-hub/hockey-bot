import asyncio
import os
import re
from playwright.async_api import async_playwright
from curl_cffi.requests import AsyncSession

# --- КОНФИГ ---
PROXY_URL = os.getenv("PROXY_URL", "") 
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

X_FSIGN = None

async def steal_token():
    """Секретная миссия: запускаем браузер-шпион, перехватываем ключ и исчезаем"""
    global X_FSIGN
    print("\n🕵️ Запускаю шпиона для кражи ключа (x-fsign)...", flush=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context()
        page = await context.new_page()

        # Слушаем ВСЕ сетевые запросы браузера
        async def intercept_request(request):
            global X_FSIGN
            if "x-fsign" in request.headers:
                X_FSIGN = request.headers["x-fsign"]

        page.on("request", intercept_request)
        
        try:
            # Идем в хоккей, чтобы он точно запросил хоккейный фид
            await page.goto("https://www.flashscore.com/hockey/", timeout=30000)
            await asyncio.sleep(5) # Ждем, пока JS отработает и отправит запрос
        except Exception as e:
            print(f"   ⚠️ Ошибка шпиона: {e}", flush=True)
        finally:
            await browser.close()
            
    return X_FSIGN

async def fetch_api(session, url, headers):
    proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
    try:
        response = await session.get(url, headers=headers, proxies=proxies, impersonate="chrome124", timeout=15)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

async def main():
    print(f"--- ☢️ БОТ V103: ГИБРИДНЫЙ ПЕРЕХВАТЧИК ---", flush=True)
    
    global X_FSIGN
    
    async with AsyncSession() as session:
        while True:
            # 1. Воруем ключ, если его еще нет
            if not X_FSIGN:
                X_FSIGN = await steal_token()
                
            if not X_FSIGN:
                print("💤 Не удалось украсть ключ. Пробую снова через 30 сек...", flush=True)
                await asyncio.sleep(30)
                continue
                
            print(f"   🔑 Рабочий ключ: {X_FSIGN}", flush=True)

            headers = {
                "x-fsign": X_FSIGN,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.flashscore.com/"
            }

            # 2. Прямой запрос к API
            print("\n📡 Запрашиваю Лайв-матчи по хоккею...", flush=True)
            live_url = "https://d.flashscore.com/x/feed/f_4_1_3_ru_1" # 4-хоккей, 1-лайв
            code, text = await fetch_api(session, live_url, headers)
            
            # Если токен протух (вернул 0), сбрасываем его и воруем заново
            if text == "0":
                print("❌ Токен устарел или заблокирован. Сбрасываю...", flush=True)
                X_FSIGN = None
                continue
                
            print(f"   [HTTP {code}] УСПЕХ! Ответ базы: {text[:100].replace(chr(10), ' ')}...", flush=True)
            
            # Проверяем, есть ли матчи
            if "~AA÷" in text:
                matches = text.split("~AA÷")
                print(f"📊 Скачано сырых матчей в лайве: {len(matches)-1}", flush=True)
                # Дальше пойдет логика парсинга, пока просто смотрим, пробита ли защита
                break
            else:
                print("🤷‍♂️ Доступ открыт, но матчей сейчас нет. Жду 60 сек...", flush=True)
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
