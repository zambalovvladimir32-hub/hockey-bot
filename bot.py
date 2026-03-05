import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 

async def main():
    print(f"--- 🦾 БОТ V39: ПОИСК ПРИЧИНЫ ---", flush=True)
    
    async with async_playwright() as p:
        proxy_cfg = {"server": PROXY_URL} if PROXY_URL else None
        browser = await p.chromium.launch(headless=True, proxy=proxy_cfg, args=['--no-sandbox'])
        
        # Создаем контекст с очень длинным временем ожидания и реалистичным профилем
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()
        
        while True:
            try:
                print(f"\n📡 Пытаюсь пробить Flashscore LIVE...", flush=True)
                # Идем сразу в лайв-раздел
                url = "https://www.flashscore.com/hockey/?s=2"
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                
                # Ждем подольше, чтобы JS успел отрисовать матчи
                await asyncio.sleep(15)

                # 1. ТЕСТ: ЧТО ВООБЩЕ НА СТРАНИЦЕ?
                title = await page.title()
                content = await page.evaluate("document.body.innerText")
                
                print(f"📄 Заголовок: {title}", flush=True)
                
                # 2. ПРОБУЕМ ВСЕ СЕЛЕКТОРЫ МИРА
                # Ищем по классу, по ID, по атрибутам
                selectors = [".event__match", "[id^='g_4_']", ".leagues--live", ".event__participant"]
                found_something = False
                
                for sel in selectors:
                    count = await page.locator(sel).count()
                    if count > 0:
                        print(f"✅ Нашел элементы по селектору '{sel}': {count}", flush=True)
                        found_something = True
                
                if not found_something:
                    print(f"❌ МАТЧЕЙ НЕ ВИДНО. Текст страницы (кусок):", flush=True)
                    print(f"--- НАЧАЛО ДАМПА ---", flush=True)
                    # Выводим первые 1000 символов, чтобы понять, где мы
                    print(content[:1000].replace('\n', ' '), flush=True)
                    print(f"--- КОНЕЦ ДАМПА ---", flush=True)
                    
                    if "Verify you are human" in content or "Cloudflare" in content:
                        print("⛔️ БЛОКИРОВКА: Нас просят пройти капчу/проверку браузера.", flush=True)
                    elif "No live games" in content or "There are no" in content:
                        print("⏸ ПУСТО: В лайве сейчас реально нет хоккея (бывает редко).", flush=True)
                else:
                    # Если нашли — просто выведем первый попавшийся матч для теста
                    first_match = await page.locator(".event__match").first.inner_text()
                    print(f"🚀 УСПЕХ! Вижу матч: {first_match.replace(chr(10), ' ')}", flush=True)
                    
                    # Здесь будет твой основной код парсинга, когда мы поймем, что видим матчи
                
                print(f"💤 Жду 2 минуты...", flush=True)
                await asyncio.sleep(120)

            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
