import asyncio
from playwright.async_api import async_playwright

async def main():
    print("--- ☢️ БОТ V105: СЕТЕВОЙ РЕНТГЕН ---", flush=True)
    
    async with async_playwright() as p:
        # Добавляем маскировку под обычный браузер
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox', 
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled'
        ])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Шпион: Ловим ВСЕ скрытые запросы сайта
        async def handle_request(request):
            if request.resource_type in ["xhr", "fetch"]:
                # Фильтруем мусор, оставляем только важное
                if "flashscore" in request.url and ("feed" in request.url or "api" in request.url or "x/" in request.url):
                    print(f"   [СЕТЬ] Перехвачен запрос: {request.url[:120]}", flush=True)

        page.on("request", handle_request)

        print("📡 Захожу на сайт Flashscore...", flush=True)
        try:
            await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000)
            
            # Читаем заголовок страницы. Это самое важное!
            title = await page.title()
            print(f"\n📝 ЗАГОЛОВОК СТРАНИЦЫ: {title}", flush=True)
            
            if "Just a moment" in title or "Cloudflare" in title:
                print("❌ ВЕРДИКТ: Нас заблокировал Cloudflare (выдал капчу).", flush=True)
            else:
                print("✅ ВЕРДИКТ: Мы прошли на сайт! Слушаю трафик...", flush=True)

            print("⏳ Жду 10 секунд, пока прогрузятся фиды...", flush=True)
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"⚠️ Ошибка: {e}", flush=True)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
