import asyncio
import os
import json
import re
import aiohttp
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
        with open(DB_MATCHES, "r", encoding="utf-8") as f:
            TRACKED_MATCHES = json.load(f)

async def send_tg(text):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except Exception as e: print(f"ТГ ошибка: {e}", flush=True)

# --- ПРОВЕРКА РЕЗУЛЬТАТОВ ---
async def check_results(context):
    to_delete = []
    for m_id, data in TRACKED_MATCHES.items():
        page = await context.new_page()
        try:
            await page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=30000)
            status_el = page.locator(".detailScore__status")
            if await status_el.count() == 0: continue
            status = await status_el.inner_text()
            
            if any(x in status for x in ["Break", "3rd", "3-й", "Finished", "Перерыв", "Завершен"]):
                scores = await page.locator(".detailScore__wrapper").inner_text()
                nums = re.findall(r"\d+", scores)
                if len(nums) >= 2:
                    current_total = int(nums[0]) + int(nums[1])
                    if current_total > data['p1_total']:
                        msg = f"✅ <b>ГОЛ ПОЙМАН!</b>\n🤝 {data['home']} — {data['away']}\nСтавка на 2-й период зашла! 🚀"
                    else:
                        msg = f"❌ <b>БЕЗ ГОЛОВ</b>\n🤝 {data['home']} — {data['away']}\nВторой период прошел всухую."
                    await send_tg(msg)
                    to_delete.append(m_id)
        except Exception: pass
        finally: await page.close()
    
    for m_id in to_delete: del TRACKED_MATCHES[m_id]
    if to_delete: save_data()

# --- ОСНОВНОЙ ПАРСЕР ---
async def main():
    print("--- 🦾 БОТ V23: АКТИВНЫЙ СКАНЕР ТАБЛИЦЫ ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        main_page = await context.new_page()
        
        while True:
            try:
                if TRACKED_MATCHES: 
                    await check_results(context)

                print("\n📡 Обновляю Flashscore...", flush=True)
                await main_page.goto("https://www.flashscore.com/hockey/", timeout=60000)
                await main_page.wait_for_selector(".event__match", timeout=20000)
                
                rows = await main_page.locator(".event__header, .event__match").all()
                cur_league = "Неизвестная лига"
                matches_checked = 0
                
                for row in rows:
                    cls = await row.get_attribute("class") or ""
                    
                    if "event__header" in cls:
                        try:
                            l_text = await row.evaluate("el => el.textContent")
                            parts = [p.strip() for p in l_text.split('\n') if p.strip()]
                            cur_league = " - ".join(parts[:2]) if len(parts) >= 2 else parts[0]
                        except: pass
                        continue
                    
                    if "event__match" in cls:
                        matches_checked += 1
                        stage_loc = row.locator(".event__stage")
                        if await stage_loc.count() == 0: continue
                        stage = await stage_loc.inner_text()
                        stage_lower = (stage or "").lower()
                        
                        if not ("break" in stage_lower or "перерыв" in stage_lower): continue
                        if any(x in stage_lower for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                        
                        m_id = (await row.get_attribute("id") or "").split("_")[-1]
                        if not m_id or m_id in TRACKED_MATCHES: continue

                        sc_h_loc, sc_a_loc = row.locator(".event__score--home"), row.locator(".event__score--away")
                        if await sc_h_loc.count() == 0 or await sc_a_loc.count() == 0: continue

                        sc_h_txt, sc_a_txt = await sc_h_loc.inner_text(), await sc_a_loc.inner_text()
                        if not sc_h_txt.isdigit() or not sc_a_txt.isdigit(): continue
                        
                        sc_h, sc_a = int(sc_h_txt), int(sc_a_txt)
                        if (sc_h + sc_a) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🔍 КАНДИДАТ: {home} - {away} ({sc_h}:{sc_a} | {cur_league})", flush=True)
                        
                        det = await context.new_page()
                        try:
                            # 1. ПРОВЕРКА НА ЛИШНИЕ ПЕРИОДЫ
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=20000)
                            await det.wait_for_selector(".smv__periodHeader", timeout=5000)
                            headers = await det.locator(".smv__periodHeader").all_inner_texts()
                            if len(headers) > 1:
                                print("      ❌ Пропуск: Уже есть 2-й период.", flush=True)
                                continue

                            # 2. ПЕРЕХОД В СТАТИСТИКУ И ОЖИДАНИЕ ТАБЛИЦЫ
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000)
                            
                            total_sh, total_wh, total_pim = None, 0, 0
                            
                            try:
                                # Ждем появления хотя бы одной строки статистики (например, "Shots")
                                await det.wait_for_selector(".stat__row", timeout=8000)
                                stat_rows = await det.locator(".stat__row").all()
                                
                                for s_row in stat_rows:
                                    name = (await s_row.locator(".stat__categoryName").inner_text()).lower()
                                    h_val = await s_row.locator(".stat__homeValue").inner_text()
                                    a_val = await s_row.locator(".stat__awayValue").inner_text()
                                    
                                    val_sum = int(h_val) + int(a_val)
                                    
                                    if any(x in name for x in ["shot", "броски в створ", "střely на"]):
                                        if total_sh is None: total_sh = val_sum # Только первый заголовок про броски
                                    elif any(x in name for x in ["penalties", "удаления", "vyloučení"]):
                                        total_wh = val_sum
                                    elif any(x in name for x in ["pim", "penalty minutes", "штрафное время"]):
                                        total_pim = val_sum
                            except Exception as e:
                                print(f"      ⚠️ Статистика не прогрузилась вовремя.", flush=True)

                            if total_sh is None:
                                print(f"      ❌ Не удалось найти броски в таблице.", flush=True)
                                continue

                            print(f"      📊 Итог P1: Броски={total_sh}, Штрафы={total_pim}м, Удаления={total_wh}", flush=True)

                            # --- УСЛОВИЯ СТРАТЕГИИ ---
                            if total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                       f"🏆 {cur_league}\n"
                                       f"🤝 {home} — {away}\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🥅 Счет P1: <b>{sc_h}:{sc_a}</b>\n"
                                       f"🎯 Броски: <b>{total_sh}</b>\n"
                                       f"❌ Удаления: <b>{total_wh}</b>\n"
                                       f"⏳ Штраф: <b>{total_pim} мин</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🕒 <i>Ждем гол во 2-м периоде...</i>")
                                await send_tg(msg)
                                TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": sc_h + sc_a}
                                save_data()
                                print("      ✅ СИГНАЛ ОТПРАВЛЕН!", flush=True)
                            else:
                                print("      ❌ Не подходит по цифрам.", flush=True)
                        except Exception as e:
                            print(f"      ⚠️ Ошибка: {e}", flush=True)
                        finally: await det.close()
                
                print(f"💤 Проверено: {matches_checked}. Жду 60 сек...", flush=True)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
            
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
