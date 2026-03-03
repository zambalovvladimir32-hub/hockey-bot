import asyncio
from playwright.async_api import async_playwright

async def main():
    print("--- 🚜 ТЯЖЕЛАЯ АРТИЛЛЕРИЯ: ШАГ 2 (ЧИТАЕМ СТАТУ) ---", flush=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            print("1️⃣ Идем на главную за списком матчей...", flush=True)
            await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
            await page.wait_for_selector(".event__match", timeout=20000)
            
            # Берем САМЫЙ ПЕРВЫЙ матч из лайва
            first_match = page.locator(".event__match").first
            
            # Вытаскиваем его ID (он лежит в атрибуте id, выглядит как "g_4_XXXXXXX")
            match_id_raw = await first_match.get_attribute("id")
            match_id = match_id_raw.split("_")[-1] # Отрезаем "g_4_" и получаем чистый ID
            
            home = await first_match.locator(".event__participant--home").inner_text()
            away = await first_match.locator(".event__participant--away").inner_text()
            
            print(f"✅ Взят матч: {home} - {away} (ID: {match_id})", flush=True)
            
            # Формируем прямую ссылку на вкладку статистики
            stats_url = f"https://www.flashscore.com/match/{match_id}/#/match-summary/match-statistics/0"
            print(f"2️⃣ Прыгаем на вкладку статистики: {stats_url}", flush=True)
            
            await page.goto(stats_url, timeout=30000)
            
            # Даем странице 3 секунды, чтобы прогрузить графики и цифры
            await page.wait_for_timeout(3000)
            
            # Собираем ВЕСЬ текст из блока статистики, чтобы найти броски
            print("⏳ Ищу данные на странице...", flush=True)
            
            # Обычно вся стата лежит в контейнере #detail
            stats_text = await page.locator("#detail").inner_text()
            
            print("\n🔥🔥🔥 БИНГО! ВОТ ЧТО МЫ НАШЛИ НА ВКЛАДКЕ СТАТИСТИКИ:")
            print("--------------------------------------------------")
            print(stats_text)
            print("--------------------------------------------------")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}", flush=True)
            
        finally:
            await browser.close()
            print("🛑 Браузер закрыт.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
