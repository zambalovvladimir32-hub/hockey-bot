import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def main():
    print("--- 🚜 ЗАВОДИМ ТЯЖЕЛУЮ АРТИЛЛЕРИЮ (PLAYWRIGHT СТЕЛС) ---", flush=True)
    
    async with async_playwright() as p:
        print("⏳ Запуск Chromium...", flush=True)
        
        # Настройки против крашей на сервере
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage', # Спасает от нехватки памяти в Docker
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # Делаем браузер максимально похожим на реальный ПК
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        
        # МАГИЯ ЗДЕСЬ: Надеваем плащ-невидимку
        await stealth_async(page)
        
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
                
            print("\n🔥 Отлично! Мы внутри. Дальше прикрутим клик на статистику.")
                
        except Exception as e:
            print(f"❌ Ошибка или Cloudflare не пустил: {e}")
            html = await page.content()
            print(f"🔍 Кусок HTML, который увидел браузер: {html[:300]}")
            
        finally:
            await browser.close()
            print("🛑 Браузер закрыт.")

if __name__ == "__main__":
    asyncio.run(main())
