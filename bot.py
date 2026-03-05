import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_MATCHES = "tracked_matches.json"
WHITE_LIST = "whitelist_leagues.json"
GREY_LIST = "greylist_leagues.json"
BLACK_LIST = "blacklist_leagues.json"

TRACKED = {}
WHITELIST = set()
GREYLIST = set()
BLACKLIST = set()

def load_data():
    global TRACKED, WHITELIST, GREYLIST, BLACKLIST
    try:
        if os.path.exists(DB_MATCHES): TRACKED = json.load(open(DB_MATCHES, 'r'))
        if os.path.exists(WHITE_LIST): WHITELIST = set(json.load(open(WHITE_LIST, 'r')))
        if os.path.exists(GREY_LIST): GREYLIST = set(json.load(open(GREY_LIST, 'r')))
        if os.path.exists(BLACK_LIST): BLACKLIST = set(json.load(open(BLACK_LIST, 'r')))
    except: pass

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(list(data) if isinstance(data, set) else data, f, ensure_ascii=False)

async def main():
    print(f"--- 🦾 БОТ V59: ТРЁХУРОВНЕВЫЙ ФИЛЬТР ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        while True:
            try:
                print(f"\n📡 Мониторинг линии...", flush=True)
                await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000, wait_until="domcontentloaded")
                await page.wait_for_selector(".event__match", timeout=15000)

                rows = await page.locator(".event__match").all()
                for row in rows:
                    try:
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED: continue

                        stage = (await row.locator(".event__stage").inner_text()).lower()
                        if "break" not in stage and "перерыв" not in stage: continue

                        # Счет (0:0, 1:0, 0:1)
                        sc_h = await row.locator(".event__score--home").inner_text()
                        sc_a = await row.locator(".event__score--away").inner_text()
                        if (int(sc_h) + int(sc_a)) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()

                        det = await context.new_page()
                        try:
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=25000)
                            
                            # Название лиги
                            league = (await det.locator(".breadcrumb__item").last().inner_text()).strip()

                            if league in BLACKLIST:
                                print(f"   🚫 {league} в ЧЕРНОМ списке. Игнорирую.", flush=True)
                                continue

                            # 1. ПРОВЕРКА: Есть ли вообще вкладка статистики?
                            tabs = await det.locator(".tabs__tab").all_inner_texts()
                            has_stats_tab = any("Stat" in t or "Стат" in t for t in tabs)

                            if not has_stats_tab:
                                print(f"   ⚫ НЕТ СТАТИСТИКИ ВООБЩЕ. {league} -> ЧЕРНЫЙ СПИСОК", flush=True)
                                BLACKLIST.add(league)
                                save_json(BLACK_LIST, BLACKLIST)
                                continue

                            # 2. ПРОВЕРКА: Броски (Shots on Goal)
                            try:
                                await det.wait_for_selector(".stat__row", timeout=5000)
                                content = await det.evaluate("document.body.innerText")
                                
                                if "Shots on Goal" in content or "Броски в створ" in content:
                                    if league not in WHITELIST:
                                        WHITELIST.add(league)
                                        save_json(WHITE_LIST, WHITELIST)
                                        print(f"   ⚪ {league} добавлена в БЕЛЫЙ СПИСОК", flush=True)
                                    
                                    # ЛОГИКА СИГНАЛА
                                    sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ)[\s\n]+(\d+)", content, re.I)
                                    if sh:
                                        t_sh = int(sh.group(1)) + int(sh.group(2))
                                        if t_sh >= 13:
                                            # (Добавь сюда поиск удалений и штрафа из V58)
                                            print(f"   ✅ СИГНАЛ: {home}-{away} (Броски: {t_sh})", flush=True)
                                            # await send_tg(...) 
                                            TRACKED[m_id] = True
                                            save_json(DB_MATCHES, TRACKED)
                                else:
                                    if league not in GREYLIST:
                                        GREYLIST.add(league)
                                        save_json(GREY_LIST, GREYLIST)
                                        print(f"   🔘 {league} -> СЕРЫЙ СПИСОК (стата есть, бросков нет)", flush=True)
                            except:
                                # Если вкладка есть, но строки не прогрузились — это тоже Серый список
                                if league not in GREYLIST:
                                    GREYLIST.add(league)
                                    save_json(GREY_LIST, GREYLIST)
                                    print(f"   🔘 {league} -> СЕРЫЙ СПИСОК (не прогрузилось)", flush=True)
                        finally:
                            await det.close()
                    except: continue

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
