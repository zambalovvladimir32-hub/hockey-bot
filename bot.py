import asyncio
import os
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
API_DOMAIN = None
API_HEADERS = None
RESULTS_FEED_URL = None

async def main():
    print("--- ☢️ БОТ: ТЕСТ ПАРСЕРА НА АРХИВЕ ---", flush=True)
    global API_DOMAIN, API_HEADERS, RESULTS_FEED_URL
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        # 1. ПЕРЕХВАТЧИК: Ловим базу завершенных матчей
        async def handle_request(request):
            global API_DOMAIN, API_HEADERS, RESULTS_FEED_URL
            if "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                if "feed/f_4" in request.url and not RESULTS_FEED_URL:
                    RESULTS_FEED_URL = request.url
                    match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                    if match: API_DOMAIN = match.group(1)
                    
                    API_HEADERS = {
                        "x-fsign": request.headers["x-fsign"],
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://www.flashscore.com/"
                    }
                    print(f"   🎯 Пойман URL архива: {RESULTS_FEED_URL.split('/')[-1]}", flush=True)

        page.on("request", handle_request)

        print("📡 Захожу на вкладку РЕЗУЛЬТАТЫ...", flush=True)
        # Идем именно на вкладку results
        await page.goto("https://www.flashscore.com/hockey/results/", timeout=40000)
        
        for _ in range(15):
            if RESULTS_FEED_URL: break
            await asyncio.sleep(1)

        if not RESULTS_FEED_URL:
            print("❌ Не удалось поймать архивный фид.", flush=True)
            await browser.close()
            return

        print("\n✅ Качаю базу завершенных матчей...", flush=True)
        response = await context.request.get(RESULTS_FEED_URL, headers=API_HEADERS)
        text = await response.text()
        
        matches = text.split("~AA÷")
        print(f"📊 Найдено матчей в архиве: {len(matches)-1}", flush=True)

        # Берем ровно 5 завершенных матчей для теста
        count = 0
        for match_data in matches[1:]:
            # Ищем статус 3 (Матч завершен)
            if "¬AC÷3¬" not in match_data: continue 
            
            m_id = match_data.split("¬")[0]
            home_match = re.search(r"AE÷([^¬]+)", match_data)
            away_match = re.search(r"AF÷([^¬]+)", match_data)
            home = home_match.group(1) if home_match else "Home"
            away = away_match.group(1) if away_match else "Away"
            
            print(f"\n   🏒 {home} - {away} (Завершен)")
            
            # Запрашиваем статистику
            stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
            stat_response = await context.request.get(stat_url, headers=API_HEADERS)
            stat_data = await stat_response.text()

            if stat_data and "SG÷" in stat_data:
                sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                wh = re.search(r"SG÷(?:Penalties|Удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                pim = re.search(r"SG÷(?:PIM|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", stat_data)

                t_sh = int(sh.group(1)) + int(sh.group(2)) if sh else 0
                t_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                t_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0

                print(f"      📈 СТАТА (Весь матч): Броски={t_sh}, Удаления={t_wh}, Штраф={t_pim}")
            else:
                print("      🧐 Нет детальной статистики для этого матча (низшая лига / товарняк).")
            
            count += 1
            if count >= 5:
                break

        print("\n🏁 Тест парсера статистики успешно завершен!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
