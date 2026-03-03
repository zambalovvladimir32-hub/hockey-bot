import asyncio
from playwright.async_api import async_playwright

async def main():
    print("--- 🚜 ЗАВОДИМ ТЯЖЕЛУЮ АРТИЛЛЕРИЮ (НАТИВНЫЙ СТЕЛС) ---", flush=True)
    
    async with async_playwright() as p:
        print("⏳ Запуск Chromium...", flush=True)
        
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled' # Скрываем флаг робота
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        # МАГИЯ ЗДЕСЬ: Нативный скрипт-невидимка вместо сломанной библиотеки
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("🌍 Заходим на сайт Flashscore...", flush=True)
        try:
            await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
            
            print("⏳ Ждем прогрузки матчей...", flush=True)
            await page.wait_for_selector(".event__match", timeout=20000)
            
            matches = await page.locator(".event__match").all()
            print(f"\n✅ УСПЕХ! Пробили Cloudflare. Найдено матчей: {len(matches)}", flush=True)
            
            for i, match in enumerate(matches[:5]): 
                home = await match.locator(".event__participant--home").inner_text()
                away = await match.locator(".event__participant--away").inner_text()
                score_home = await match.locator(".event__score--home").inner_text()
                score_away = await match.locator(".event__score--away").inner_text()
                print(f" 🏒 {home} [{score_home}:{score_away}] {away}", flush=True)
                
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}", flush=True)
            html = await page.content()
            print(f"🔍 Кусок HTML: {html[:300]}", flush=True)
            
        finally:
            await browser.close()
            print("🛑 Браузер закрыт.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
