import asyncio
from playwright.async_api import async_playwright

async def main():
    print("--- 🚜 ЗАВОДИМ ТЯЖЕЛУЮ АРТИЛЛЕРИЮ (PLAYWRIGHT) ---", flush=True)
    
    async with async_playwright() as p:
        print("⏳ Запуск Chromium...", flush=True)
        
        # МАГИЯ ЗДЕСЬ: добавили команды против крашей браузера на сервере
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage', # Выключаем лимит 64 МБ (спасает от крашей)
                '--disable-gpu'            # Отключаем виртуальную видеокарту
            ]
        )
        
        # Маскируемся под обычного пользователя, чтобы Cloudflare не напрягался
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("🌍 Заходим на сайт Flashscore...", flush=True)
        try:
            # Увеличил таймаут загрузки до 60 секунд (на сервере первый запуск бывает долгим)
            await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
            
            print("⏳ Ждем прогрузки матчей...", flush=True)
            # Ждем появления хотя бы одного матча
            await page.wait_for_selector(".event__match", timeout=20000)
            
            matches = await page.locator(".event__match").all()
            print(f"\n✅ УСПЕХ! Пробили защиту. Найдено матчей на странице: {len(matches)}", flush=True)
            
            for i, match in enumerate(matches[:5]): 
                home = await match.locator(".event__participant--home").inner_text()
                away = await match.locator(".event__participant--away").inner_text()
                score_home = await match.locator(".event__score--home").inner_text()
                score_away = await match.locator(".event__score--away").inner_text()
                print(f" 🏒 {home} [{score_home}:{score_away}] {away}", flush=True)
                
            print("\n🔥 Отлично! Браузер работает как часы.")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            # Если словим ошибку, выведем HTML страницы, чтобы понять, что видит браузер
            html = await page.content()
            print(f"🔍 Кусок HTML, который видел браузер: {html[:500]}")
            
        finally:
            await browser.close()
            print("🛑 Браузер закрыт.")

if __name__ == "__main__":
    asyncio.run(main())
