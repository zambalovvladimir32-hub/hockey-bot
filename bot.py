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

async def check_results(context):
    to_delete = []
    for m_id, data in TRACKED_MATCHES.items():
        page = await context.new_page()
        try:
            await page.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=30000)
            status = await page.locator(".detailScore__status").inner_text()
            
            if any(x in status for x in ["Break", "3rd", "3-й", "Finished", "Перерыв", "Завершен"]):
                scores = await page.locator(".detailScore__wrapper").inner_text()
                nums = re.findall(r"\d+", scores)
                if len(nums) >= 2:
                    current_total = int(nums[0]) + int(nums[1])
                    if current_total > data['p1_total']:
                        msg = f"✅ <b>ГОЛ ПОЙМАН! (ЗАШЛО)</b>\n🤝 {data['home']} — {data['away']}\nСтатистика сработала во 2-м периоде 🚀"
                    else:
                        msg = f"❌ <b>БЕЗ ГОЛОВ (МИМО)</b>\n🤝 {data['home']} — {data['away']}\nВторой период прошел всухую."
                    
                    await send_tg(msg)
                    to_delete.append(m_id)
        except Exception: pass
        finally: await page.close()
    
    for m_id in to_delete: del TRACKED_MATCHES[m_id]
    if to_delete: save_data()

async def main():
    print("--- 🦾 БОТ V17: АБСОЛЮТНЫЙ РЕГЕКС ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0...")
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
                    cls = await row.get_attribute("class")
                    
                    # 1. ЖЕЛЕЗОБЕТОННЫЙ ЗАХВАТ ЛИГИ (Через JS)
                    if "event__header" in cls:
                        try:
                            header_text = await row.evaluate("el => el.innerText")
                            lines = [x.strip() for x in header_text.split('\n') if x.strip()]
                            if len(lines) >= 2: cur_league = f"{lines[0]}: {lines[1]}"
                            elif len(lines) == 1: cur_league = lines[0]
                        except: pass
                        continue
                    
                    if "event__match" in cls:
                        matches_checked += 1
                        
                        stage_loc = row.locator(".event__stage")
                        if await stage_loc.count() == 0: continue
                        stage = await stage_loc.inner_text()
                        if not stage: continue
                        stage_lower = stage.lower()
                        
                        if not ("break" in stage_lower or "перерыв" in stage_lower): continue
                        if any(x in stage_lower for x in ["2nd", "3rd", "2-й", "3-й"]): continue
                        
                        m_id = (await row.get_attribute("id")).split("_")[-1]
                        if m_id in TRACKED_MATCHES: continue

                        sc_h_loc = row.locator(".event__score--home")
                        sc_a_loc = row.locator(".event__score--away")
                        if await sc_h_loc.count() == 0 or await sc_a_loc.count() == 0: continue

                        sc_h_txt, sc_a_txt = await sc_h_loc.inner_text(), await sc_a_loc.inner_text()
                        if not sc_h_txt.strip().isdigit() or not sc_a_txt.strip().isdigit(): continue
                        
                        sc_h, sc_a = int(sc_h_txt.strip()), int(sc_a_txt.strip())
                        if (sc_h + sc_a) > 1: continue

                        home = await row.locator(".event__participant--home").inner_text()
                        away = await row.locator(".event__participant--away").inner_text()
                        
                        print(f"   🔍 КАНДИДАТ: {home.strip()} - {away.strip()} (Счет: {sc_h}:{sc_a} | {cur_league})", flush=True)
                        
                        det = await context.new_page()
                        try:
                            # Идем СТРОГО на вкладку 1-го периода (/match-statistics/1)
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/1", timeout=30000)
                            await det.wait_for_timeout(4000) # Даем время отрендерить вкладку
                            
                            # Берем весь видимый текст страницы целиком
                            content = await det.evaluate("document.body.innerText")
                            
                            total_sh = None
                            total_wh = None
                            total_pim = None
                            
                            # МАГИЯ РЕГЕКСА: Ищем паттерн "Цифра -> Пробелы/Слова -> Цифра"
                            
                            # Броски
                            m_sh = re.search(r"(\d+)[\s\n]+(Shots on Goal|Броски в створ ворот|Střely na branku|Střely na|Броски в створ)[\s\n]+(\d+)", content, re.IGNORECASE)
                            if m_sh: total_sh = int(m_sh.group(1)) + int(m_sh.group(3))
                            else:
                                m_sh_fb = re.search(r"(\d+)[\s\n]+(Shots|Броски|Střely)[\s\n]+(\d+)", content, re.IGNORECASE)
                                if m_sh_fb: total_sh = int(m_sh_fb.group(1)) + int(m_sh_fb.group(3))

                            # Свистки (Удаления / Penalties)
                            m_wh = re.search(r"(\d+)[\s\n]+(Penalties|Удаления|Vyloučení|2-min penalties)[\s\n]+(\d+)", content, re.IGNORECASE)
                            if m_wh: total_wh = int(m_wh.group(1)) + int(m_wh.group(3))

                            # Штрафные минуты (PIM)
                            m_pim = re.search(r"(\d+)[\s\n]+(PIM|Penalty Minutes|Штрафное время|Trestné minuty|Trestné min\.)[\s\n]+(\d+)", content, re.IGNORECASE)
                            if m_pim: total_pim = int(m_pim.group(1)) + int(m_pim.group(3))

                            if total_sh is None:
                                print(f"      ❌ Нет статы бросков (или страница не прогрузилась).", flush=True)
                                continue

                            # Резервная проверка удалений по ленте (если в таблице пусто)
                            if total_pim is None or total_wh is None:
                                await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary", timeout=20000)
                                await det.wait_for_timeout(2000)
                                total_pim = total_pim or 0
                                total_wh = total_wh or 0
                                try:
                                    incidents = await det.locator(".smv__incident").all_inner_texts()
                                    for inc in incidents:
                                        matches = re.findall(r"\b(\d+)\s*(?:'|min|мин)\b", inc.lower())
                                        for m in matches:
                                            val = int(m)
                                            if val in [2, 4, 5, 10, 20]:
                                                total_pim += val
                                                total_wh += 1
                                except: pass

                            total_pim = total_pim or 0
                            total_wh = total_wh or 0

                            print(f"      📊 Итог: Броски={total_sh}, Штрафы={total_pim}м, Свистки={total_wh}", flush=True)

                            # --- ЛОГИКА СТРАТЕГИИ ---
                            if total_sh >= 13 and total_pim >= 2 and total_wh >= 1:
                                msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                       f"🏆 {cur_league}\n"
                                       f"🤝 {home.strip()} — {away.strip()}\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🥅 Счет P1: <b>{sc_h}:{sc_a}</b>\n"
                                       f"🎯 Броски: <b>{total_sh}</b>\n"
                                       f"❌ Удаления: <b>{total_wh}</b>\n"
                                       f"⏳ Штраф: <b>{total_pim} мин</b>\n"
                                       f"━━━━━━━━━━━━━━━━━━\n"
                                       f"🕒 <i>Ждем гол во 2-м периоде... Отчет придет позже!</i>")
                                await send_tg(msg)
                                
                                TRACKED_MATCHES[m_id] = {"home": home.strip(), "away": away.strip(), "p1_total": sc_h + sc_a}
                                save_data()
                                print("      ✅ СИГНАЛ В ТЕЛЕГРАМЕ!", flush=True)
                            else:
                                print("      ❌ Пропуск по цифрам (не дотянули).", flush=True)
                        except Exception as e:
                            print(f"      ⚠️ Ошибка чтения деталей: {e}", flush=True)
                        finally: await det.close()
                
                print(f"💤 Проверено: {matches_checked}. Сплю 60 сек...", flush=True)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
            
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
