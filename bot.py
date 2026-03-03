import asyncio
from playwright.async_api import async_playwright

async def main():
    print("--- 🚜 ЗАВОДИМ ТЯЖЕЛУЮ АРТИЛЛЕРИЮ (PLAYWRIGHT) ---", flush=True)
    
    # Запускаем невидимый браузер
    async with async_playwright() as p:
        print("⏳ Запуск Chromium...")
        # args=['--no-sandbox'] нужен для работы внутри серверов типа Railway
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = await browser.new_page()
        
        print("🌍 Заходим на сайт Flashscore...", flush=True)
        try:
            # Идем прямо на хоккейный лайв
            await page.goto("https://www.flashscore.com/hockey/", timeout=30000)
            
            # Ждем, пока загрузятся элементы матчей
            print("⏳ Ждем прогрузки матчей...", flush=True)
            await page.wait_for_selector(".event__match", timeout=15000)
            
            # Собираем названия команд, которые сейчас играют
            matches = await page.locator(".event__match").all()
            print(f"\n✅ УСПЕХ! Пробили защиту. Найдено матчей на странице: {len(matches)}")
            
            for i, match in enumerate(matches[:5]): # Выведем первые 5 для проверки
                home = await match.locator(".event__participant--home").inner_text()
                away = await match.locator(".event__participant--away").inner_text()
                score_home = await match.locator(".event__score--home").inner_text()
                score_away = await match.locator(".event__score--away").inner_text()
                print(f" 🏒 {home} [{score_home}:{score_away}] {away}")
                
            print("\n🔥 Отлично! Браузер работает. Дальше научим его кликать на вкладку 'Статистика'!")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки или Cloudflare не пустил: {e}")
            
        finally:
            await browser.close()
            print("🛑 Браузер закрыт.")

if __name__ == "__main__":
    asyncio.run(main())
