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
    print(f"--- 🦾 БОТ V55: АНАЛИЗАТОР СТАТИСТИКИ ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Мониторинг Flashscore...", flush=True)
                await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000, wait_until="domcontentloaded")
                await page.wait_for_selector(".event__stage", timeout=15000)

                rows = await page.locator(".event__match").all()
                live_count = 0
                
                for row in rows:
                    stage_loc = row.locator(".event__stage")
                    if await stage_loc.count() == 0: continue
                    
                    stage_text = (await stage_loc.inner_text()).lower()
                    if not any(x in stage_text for x in ["period", "break", "перерыв", "1st"]): continue
                    if any(x in stage_text for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                    
                    live_count += 1
                    m_id = (await row.get_attribute("id")).split("_")[-1]
                    if m_id in TRACKED_MATCHES: continue

                    # Только перерывы
                    if "break" in stage_text or "перерыв" in stage_text:
                        sc_h = await row.locator(".event__score--home").inner_text()
                        sc_a = await row.locator(".event__score--away").inner_text()
                        
                        if sc_h.isdigit() and sc_a.isdigit() and (int(sc_h) + int(sc_a)) <= 1:
                            home = await row.locator(".event__participant--home").inner_text()
                            away = await row.locator(".event__participant--away").inner_text()
                            print(f"   🎯 ПЕРЕРЫВ: {home} - {away} ({sc_h}:{sc_a}). Проверяю данные...", flush=True)

                            det = await context.new_page()
                            try:
                                await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=25000)
                                await asyncio.sleep(5) # Даем стате прогрузиться
                                
                                # Берем весь текст страницы для диагностики
                                st_text = await det.evaluate("document.body.innerText")
                                
                                # Ищем всё, что напоминает статку
                                sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Броски в створ)[\s\n]+(\d+)", st_text, re.I)
                                wh = re.search(r"(\d+)[\s\n]+(?:Penalties|Удаления)[\s\n]+(\d+)", st_text, re.I)
                                pim = re.search(r"(\d+)[\s\n]+(?:PIM|Штрафное время)[\s\n]+(\d+)", st_text, re.I)

                                if sh:
                                    t_sh = int(sh.group(1)) + int(sh.group(2))
                                    t_wh = (int(wh.group(1)) + int(wh.group(2))) if wh else 0
                                    t_pim = (int(pim.group(1)) + int(pim.group(2))) if pim else 0
                                    
                                    print(f"      📈 СТАТА НАЙДЕНА: Бр={t_sh}, Удаления={t_wh}, Штраф={t_pim}", flush=True)

                                    if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                        await send_tg(f"🚨 <b>СИГНАЛ P1</b>\n🤝 {home}-{away}\n🎯 Броски: {t_sh}\n⏳ Штраф: {t_pim}")
                                        TRACKED_MATCHES[m_id] = True
                                        save_data()
                                        print("      ✅ СИГНАЛ ОТПРАВЛЕН!", flush=True)
                                    else:
                                        print(f"      ⚠️ Не подходит по критериям (Бр {t_sh}/13, Штр {t_pim}/2)", flush=True)
                                else:
                                    # Если бросков нет - пишем, какие параметры вообще есть
                                    found_params = re.findall(r"[A-Z][a-z\s]{3,20}", st_text)
                                    print(f"      ❌ БРОСКИ НЕ НАЙДЕНЫ. Вижу на странице: {found_params[:5]}...", flush=True)
                            except Exception as e:
                                print(f"      ⚠️ Ошибка на странице матча: {e}", flush=True)
                            finally:
                                await det.close()

                print(f"📊 В лайве: {live_count} | Жду 60 сек...", flush=True)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
