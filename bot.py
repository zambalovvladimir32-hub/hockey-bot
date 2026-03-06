import asyncio
import os
import re
from playwright.async_api import async_playwright

API_DOMAIN = None
API_HEADERS = None
FEED_URL = None

async def main():
    print("--- ☢️ БОТ: ПОИСК МАТЧЕЙ С ПОЛНОЙ СТАТОЙ ---", flush=True)
    global API_DOMAIN, API_HEADERS, FEED_URL
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        async def handle_request(request):
            global API_DOMAIN, API_HEADERS, FEED_URL
            if "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                if "feed/f_4" in request.url and not FEED_URL:
                    FEED_URL = request.url
                    match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                    if match: API_DOMAIN = match.group(1)
                    
                    API_HEADERS = {
                        "x-fsign": request.headers["x-fsign"],
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://www.flashscore.com/"
                    }

        page.on("request", handle_request)

        print("📡 Захожу на главную страницу хоккея...", flush=True)
        await page.goto("https://www.flashscore.com/hockey/", timeout=40000)
        
        for _ in range(15):
            if FEED_URL: break
            await asyncio.sleep(1)

        if not FEED_URL:
            print("❌ Не удалось поймать фид.")
            await browser.close()
            return

        print("\n✅ Качаю базу сегодняшнего дня...", flush=True)
        response = await context.request.get(FEED_URL, headers=API_HEADERS)
        text = await response.text()
        
        matches = text.split("~AA÷")
        print(f"📊 Ищу матчи с бросками среди {len(matches)-1} событий...", flush=True)
        
        found_stats = 0
        for match_data in matches[1:]:
            if not re.search(r"¬AC÷[389]¬", match_data): continue 
            
            m_id = match_data.split("¬")[0]
            if len(m_id) != 8: continue

            home_match = re.search(r"AE÷([^¬]+)", match_data)
            away_match = re.search(r"AF÷([^¬]+)", match_data)
            home = home_match.group(1) if home_match else "Home"
            away = away_match.group(1) if away_match else "Away"
            
            # Запрашиваем статистику
            stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
            stat_response = await context.request.get(stat_url, headers=API_HEADERS)
            stat_data = await stat_response.text()

            # Если стата есть, пытаемся вытащить данные (re.IGNORECASE игнорирует большие/маленькие буквы)
            if stat_data and "SG÷" in stat_data:
                sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                wh = re.search(r"SG÷(?:Penalties|Удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                pim = re.search(r"SG÷(?:PIM|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)

                if sh:
                    t_sh = int(sh.group(1)) + int(sh.group(2))
                    t_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                    t_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0

                    print(f"\n   🏒 {home} - {away} (ID: {m_id})")
                    print(f"      📈 СТАТА: Броски={t_sh}, Удаления={t_wh}, Штраф={t_pim}")
                    found_stats += 1

            if found_stats >= 3: # Стоп после 3 успешных находок
                break

        if found_stats == 0:
            print("\n🤷‍♂️ Не нашел ни одного матча с бросками. Возможно, регулярку нужно подкрутить.")

        print("\n🏁 Тест парсера завершен!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
