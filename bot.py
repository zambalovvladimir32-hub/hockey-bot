import asyncio
import os
import json
import re
import aiohttp
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
PROXY_URL = os.getenv("PROXY_URL") 
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
        try: await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print(f"--- 🦾 БОТ V38: THE CONTENT SNIPER ---", flush=True)
    load_data()
    
    async with async_playwright() as p:
        proxy_cfg = {"server": PROXY_URL} if PROXY_URL else None
        browser = await p.chromium.launch(headless=True, proxy=proxy_cfg, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        main_page = await context.new_page()
        # Блокируем мусор для скорости
        await main_page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "media"] else route.continue_())

        while True:
            try:
                print(f"\n📡 Загружаю Flashscore... (Proxy: {bool(PROXY_URL)})", flush=True)
                
                # Идем на чешскую версию, раз у тебя на скрине была она (она часто стабильнее)
                url = "https://www.flashscore.com/hockey/"
                await main_page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(10) # Ждем прогрузки JS

                # --- ДИАГНОСТИКА ПУСТОТЫ ---
                title = await main_page.title()
                content_snippet = await main_page.evaluate("document.body.innerText.substring(0, 500)")
                
                # Пробуем разные селекторы матчей
                matches = await main_page.locator(".event__match, [id^='g_4_'], .leagues--live .event__match").all()
                match_count = len(matches)
                
                print(f"📄 Заголовок: {title}", flush=True)
                print(f"📊 Матчей нашел: {match_count}", flush=True)

                if match_count == 0:
                    print(f"🧐 ЧТО ВИДИТ БОТ: {content_snippet.replace(chr(10), ' ')}", flush=True)
                    if "Blocked" in content_snippet or "Access Denied" in content_snippet or "Verify" in content_snippet:
                        print("❌ НАС ЗАБАНИЛИ (Cloudflare/Bot Detection)", flush=True)
                    continue

                for row in matches:
                    try:
                        # Пытаемся выцепить стадию матча
                        stage_text = await row.inner_text()
                        if not any(x in stage_text.lower() for x in ["break", "перерыв", "pauza"]): continue
                        if any(x in stage_text.lower() for x in ["2nd", "3rd", "2-й", "3-й"]): continue

                        m_id = (await row.get_attribute("id") or "").split("_")[-1]
                        if not m_id or m_id in TRACKED_MATCHES: continue

                        # Читаем участников
                        teams = await row.locator(".event__participant").all_inner_texts()
                        if len(teams) < 2: continue
                        home, away = teams[0], teams[1]

                        print(f"   🎯 ПОЙМАН КАНДИДАТ: {home} - {away}. Иду в статку...", flush=True)
                        
                        det = await context.new_page()
                        try:
                            # Прямой заход в статистику
                            await det.goto(f"https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0", timeout=30000, wait_until="domcontentloaded")
                            await asyncio.sleep(5)
                            
                            stat_text = await det.evaluate("document.body.innerText")
                            
                            # Поиск статы (Regex)
                            sh = re.search(r"(\d+)[\s\n]+(?:Shots on Goal|Střely na branku|Броски в створ)[\s\n]+(\d+)", stat_text, re.I)
                            wh = re.search(r"(\d+)[\s\n]+(?:Penalties|Vyloučení|Удаления)[\s\n]+(\d+)", stat_text, re.I)
                            pim = re.search(r"(\d+)[\s\n]+(?:PIM|Trestné minuty|Штрафное время)[\s\n]+(\d+)", stat_text, re.I)

                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                t_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                                t_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0
                                
                                print(f"      📈 Бр: {t_sh} | Свист: {t_wh} | Штр: {t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ: ПЕРЕРЫВ P1</b>\n"
                                           f"🤝 {home} — {away}\n"
                                           f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин")
                                    await send_tg(msg)
                                    TRACKED_MATCHES[m_id] = {"home": home, "away": away, "p1_total": 0}
                                    save_data()
                            else:
                                print("      ❌ Стата не найдена внутри матча.", flush=True)
                        except: pass
                        finally: await det.close()
                    except: continue

                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
