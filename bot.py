import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
PROXY_URL = os.getenv("PROXY_URL") 
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_MATCHES = "tracked_matches.json"

TRACKED_MATCHES = {}

def save_data():
    with open(DB_MATCHES, "w", encoding="utf-8") as f:
        json.dump(TRACKED_MATCHES, f)

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    import aiohttp
    async with aiohttp.ClientSession() as session:
        try: await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def handle_response(response):
    """Перехватчик сетевых ответов"""
    # Ищем пакеты данных Flashscore (хоккей лайв)
    if "feed/f_4_2_" in response.url:
        try:
            raw_data = await response.text()
            if not raw_data: return
            
            matches = raw_data.split("~AA÷")
            print(f"📡 ПЕРЕХВАЧЕНО: {len(matches)-1} матчей в потоке!", flush=True)
            
            for m in matches[1:]:
                # Здесь логика парсинга сырого потока из V43
                if "¬AC÷36¬" in m: # Код перерыва P1
                    m_id = m.split("¬")[0]
                    home = re.search(r"AE÷([^¬]+)", m).group(1)
                    away = re.search(r"AF÷([^¬]+)", m).group(1)
                    print(f"   🎯 Вижу перерыв: {home} - {away} (ID: {m_id})", flush=True)
                    # Можно слать сигнал или запрашивать статку дальше
        except: pass

async def main():
    print(f"--- 🦾 БОТ V44: NUCLEAR INTERCEPTOR ---", flush=True)
    
    async with async_playwright() as p:
        proxy_cfg = {"server": PROXY_URL} if PROXY_URL else None
        
        # Запускаем браузер с защитой от обнаружения
        browser = await p.chromium.launch(
            headless=True, 
            proxy=proxy_cfg,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = await context.new_page()
        
        # ВКЛЮЧАЕМ ПЕРЕХВАТ
        page.on("response", handle_response)

        while True:
            try:
                print("\n🌐 Захожу на Flashscore для захвата данных...", flush=True)
                # Заходим на сайт. Даже если он не прогрузится до конца, 
                # перехватчик сработает на первых же пакетах данных.
                try:
                    await page.goto("https://www.flashscore.ru/hockey/", timeout=60000)
                except:
                    print("⚠️ Таймаут загрузки, но перехватчик мог успеть поймать данные...", flush=True)
                
                # Даем браузеру "подышать" и попринимать пакеты
                await asyncio.sleep(30)
                
                # Обновляем страницу для получения свежего потока
                await page.reload(timeout=60000)
                
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
