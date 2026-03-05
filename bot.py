import asyncio
import os
import json
import re
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
DB_MATCHES = "tracked_matches.json"

TRACKED_MATCHES = {}

def save_data():
    with open(DB_MATCHES, "w", encoding="utf-8") as f:
        json.dump(TRACKED_MATCHES, f)

def load_data():
    global TRACKED_MATCHES
    if os.path.exists(DB_MATCHES):
        try:
            with open(DB_MATCHES, "r", encoding="utf-8") as f:
                TRACKED_MATCHES = json.load(f)
        except: TRACKED_MATCHES = {}

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    import aiohttp
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try: await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V54: СТАБИЛИЗАЦИЯ ЗАГРУЗКИ ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = await context.new_page()
        # Блокируем картинки
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Загружаю Flashscore...", flush=True)
                await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000, wait_until="domcontentloaded")
                
                # ЖДЕМ, ПОКА ПОЯВИТСЯ ПЕРВЫЙ РЕАЛЬНЫЙ СТАТУС (убиваем скелет)
                try:
                    await page.wait_for_selector(".event__stage", timeout=15000)
                except:
                    print("⚠️ Данные в таблице не появились (скелет завис). Перезагружаю...", flush=True)
                    continue

                all_rows = await page.locator(".event__match").all()
                live_matches = []

                for row in all_rows:
                    # Проверяем наличие элемента статуса перед чтением
                    stage_loc = row.locator(".event__stage")
                    if await stage_loc.count() > 0:
                        stage_text = (await stage_loc.inner_text()).lower()
                        # Если это реально лайв (есть время или период)
                        if any(x in stage_text for x in ["period", "break", "перерыв", "1st", "2nd", "3rd"]) or ":" in stage_text:
                            live_matches.append((row, stage_text))

                print(f"📊 Всего строк: {len(all_rows)} | РЕАЛЬНО В ЛАЙВЕ: {len(live_matches)}", flush=True)
                
                for row, stage_text in live_matches:
                    try:
                        # Фильтр только на ПЕРЕРЫВ P1
                        if not any(x in stage_text for x in ["break", "перерыв"]): continue
                        if any(x in stage_text for x in ["2nd", "3rd", "2-й", "3-й"]): continue

                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        # Счет
                        score_h_loc = row.locator(".event__score--home")
                        score_a_loc = row.locator(".event__score--away")
                        
                        if await score_h_loc.count() > 0 and await score_a_loc.count() > 0:
                            sc_h = await score_h_loc.inner_text()
                            sc_a = await score_a_loc.inner_text()
                            if sc_h.isdigit() and sc_a.isdigit():
                                if (int(sc_h) + int(sc_a)) > 1: continue
                            else: continue
                        else: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🎯 ПОЙМАН ПЕРЕРЫВ: {home} - {away} ({sc_h}:{sc_a})", flush=True)

                        det = await context.new_page()
                        try:
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=25000)
                            await det.wait_for_selector(".stat__row", timeout=10000)
                            
                            st_text = await det.evaluate("document.body.innerText")
                            
                            sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ)[\s\n]+(\d+)", st_text, re.I)
                            wh = re.search(r"(\d+)[\s\n]+(?:Penalties|Удаления)[\s\n]+(\d+)", st_text, re.I)
                            pim = re.search(r"(\d+)[\s\n]+(?:PIM|Штраф)[\s\n]+(\d+)", st_text, re.I)

                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                t_wh = (int(wh.group(1)) + int(wh.group(2))) if wh else 0
                                t_pim = (int(pim.group(1)) + int(pim.group(2))) if pim else 0
                                
                                print(f"      📈 Стата: Бр={t_sh}, Свистки={t_wh}, Штраф={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ P1</b>\n"
                                           f"🤝 {home} — {away} ({sc_h}:{sc_a})\n"
                                           f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин")
                                    await send_tg(msg)
                                    TRACKED_MATCHES[m_id] = True
                                    save_data()
                        except: pass
                        finally: await det.close()

                    except: continue

                print("💤 Сплю 60 сек...", flush=True)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
