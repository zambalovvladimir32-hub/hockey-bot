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
    print(f"--- 🦾 БОТ V53: СТРОГИЙ ЛАЙВ-ФИЛЬТР ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = await context.new_page()
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Загружаю Flashscore (Live-only)...", flush=True)
                # Идем в раздел LIVE
                await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(8) 

                all_rows = await page.locator(".event__match").all()
                live_matches = []

                # Фильтруем: оставляем только те, где ЕСТЬ реальный статус (время или период)
                for row in all_rows:
                    stage = (await row.locator(".event__stage").inner_text()).lower()
                    # Если в статусе есть цифры (минуты) или слово "Period" или "Break" - это наш клиент
                    if any(x in stage for x in ["period", "break", "перерыв", "1st", "2nd", "3rd"]) or ":" in stage:
                        live_matches.append(row)

                print(f"📊 Нашел строк: {len(all_rows)} | РЕАЛЬНО В ЛАЙВЕ: {len(live_matches)}", flush=True)
                
                for row in live_matches:
                    try:
                        stage_text = (await row.locator(".event__stage").inner_text()).lower()
                        
                        # Нам нужен только перерыв ПОСЛЕ 1-го периода (Break или 1st)
                        # Но исключаем 2-й и 3-й
                        if not any(x in stage_text for x in ["break", "1st", "перерыв"]): continue
                        if any(x in stage_text for x in ["2nd", "3rd", "2-й", "3-й"]): continue

                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        # Счет
                        score_h = await row.locator(".event__score--home").inner_text()
                        score_a = await row.locator(".event__score--away").inner_text()
                        
                        if not (score_h.isdigit() and score_a.isdigit()): continue
                        if (int(score_h) + int(score_a)) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🎯 ПЕРЕРЫВ: {home} - {away}. Иду за статой...", flush=True)

                        det = await context.new_page()
                        try:
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=20000)
                            await det.wait_for_selector(".stat__row", timeout=10000)
                            
                            st_text = await det.evaluate("document.body.innerText")
                            
                            # Броски, Удаления, Штраф
                            sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ)[\s\n]+(\d+)", st_text, re.I)
                            wh = re.search(r"(\d+)[\s\n]+(?:Penalties|Удаления)[\s\n]+(\d+)", st_text, re.I)
                            pim = re.search(r"(\d+)[\s\n]+(?:PIM|Штраф)[\s\n]+(\d+)", st_text, re.I)

                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                t_wh = (int(wh.group(1)) + int(wh.group(2))) if wh else 0
                                t_pim = (int(pim.group(1)) + int(pim.group(2))) if pim else 0
                                
                                print(f"      📊 Итог: Бр={t_sh}, Свистки={t_wh}, Штраф={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ P1</b>\n"
                                           f"🤝 {home} — {away} ({score_h}:{score_a})\n"
                                           f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин")
                                    await send_tg(msg)
                                    TRACKED_MATCHES[m_id] = True
                                    save_data()
                        except: pass
                        finally: await det.close()

                    except: continue

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
