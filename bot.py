import asyncio
import os
import re
import json
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
TRACKED_MATCHES = set()

API_DOMAIN = None
API_HEADERS = None
FEED_URL = None

BLACKLIST_FILE = "blacklist.json"

def load_list(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_list(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(list(data), f, ensure_ascii=False, indent=4)

BLACKLIST = load_list(BLACKLIST_FILE)

async def send_tg(text):
    import aiohttp
    if not TOKEN or not CHAT_ID: return
    async with aiohttp.ClientSession() as session:
        try: await session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})
        except: pass

async def main():
    print("--- ☢️ БОТ V111: ULTIMATE SNIPER (ИСПРАВЛЕННЫЙ ЛАЙВ) ---", flush=True)
    global API_DOMAIN, API_HEADERS, FEED_URL, BLACKLIST
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        async def handle_request(request):
            global API_DOMAIN, API_HEADERS, FEED_URL
            if "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                # Ищем СТРОГО лайв-фид (содержит f_4_1)
                if "feed/f_4_1" in request.url and not FEED_URL:
                    FEED_URL = request.url
                    match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                    if match: API_DOMAIN = match.group(1)
                    
                    # Добавлены заголовки против кэширования
                    API_HEADERS = {
                        "x-fsign": request.headers["x-fsign"],
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://www.flashscore.com/",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache"
                    }
                    print(f"   🎯 Пойман URL ЛАЙВ-базы: {FEED_URL.split('/')[-1]}", flush=True)

        page.on("request", handle_request)

        print("📡 Захожу на вкладку LIVE...", flush=True)
        await page.goto("https://www.flashscore.com/hockey/?s=2", timeout=40000)
        
        for _ in range(15):
            if FEED_URL: break
            await asyncio.sleep(1)

        if not FEED_URL:
            print("❌ Не удалось поймать ЛАЙВ фид. Возможно, сейчас вообще нет матчей в лайве. Перезапуск...")
            await browser.close()
            return

        print(f"✅ Прицел захвачен! В Черном списке лиг: {len(BLACKLIST)}", flush=True)

        while True:
            try:
                print("\n📡 Обновляю базу...", flush=True)
                response = await context.request.get(FEED_URL, headers=API_HEADERS)
                text = await response.text()
                
                if text == "0" or not text:
                    print("⚠️ Токен протух. Обновляю страницу...", flush=True)
                    FEED_URL = None
                    await page.reload(timeout=30000)
                    await asyncio.sleep(5)
                    continue

                blocks = text.split("~")
                live_count = 0
                current_league = "Unknown League"
                
                for block in blocks:
                    if block.startswith("ZA÷"):
                        league_match = re.search(r"ZA÷([^¬]+)", block)
                        if league_match:
                            current_league = league_match.group(1).strip()
                        continue
                        
                    if block.startswith("AA÷"):
                        ac_match = re.search(r"¬AC÷(\d+)¬", block)
                        # ПРАВИЛЬНЫЕ хоккейные статусы: 12 (P1), 13 (P2), 14 (P3), 15 (OT), 16 (Pen), 36-38 (Перерывы)
                        if ac_match and int(ac_match.group(1)) in [12, 13, 14, 15, 16, 36, 37, 38]:
                            live_count += 1
                            
                        # ЖЕСТКИЙ ФИЛЬТР: Только перерыв после 1-го периода
                        if "¬AC÷36¬" not in block: continue 
                        
                        m_id = block.split("¬")[0].replace("AA÷", "")
                        if m_id in TRACKED_MATCHES: continue
                        
                        if current_league in BLACKLIST:
                            continue

                        home_match = re.search(r"AE÷([^¬]+)", block)
                        away_match = re.search(r"AF÷([^¬]+)", block)
                        home = home_match.group(1) if home_match else "Home"
                        away = away_match.group(1) if away_match else "Away"

                        sc_h_match = re.search(r"AG÷(\d+)", block)
                        sc_a_match = re.search(r"AH÷(\d+)", block)
                        sc_h = int(sc_h_match.group(1)) if sc_h_match else 0
                        sc_a = int(sc_a_match.group(1)) if sc_a_match else 0

                        if (sc_h + sc_a) > 1: continue

                        print(f"   🎯 ПЕРЕРЫВ P1: {home} - {away} | 🏆 {current_league}", flush=True)

                        stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                        stat_response = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_response.text()

                        if not stat_data or "SG÷" not in stat_data:
                            print(f"      🗑 Нет статистики. Лига '{current_league}' отправлена в ЧЕРНЫЙ СПИСОК!", flush=True)
                            BLACKLIST.add(current_league)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            TRACKED_MATCHES.add(m_id)
                            continue

                        p1_data = None
                        if "~SE÷" in stat_data:
                            for tab in stat_data.split("~SE÷"):
                                if re.search(r"^(1st Period|1-й период|1\. Period|Period 1)", tab, re.IGNORECASE):
                                    p1_data = tab
                                    break
                        
                        if not p1_data:
                            p1_data = stat_data

                        sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", p1_data, re.IGNORECASE)
                        wh = re.search(r"SG÷(?:Penalties|Удаления)¬SH÷(\d+)¬SI÷(\d+)", p1_data, re.IGNORECASE)
                        pim = re.search(r"SG÷(?:PIM|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", p1_data, re.IGNORECASE)

                        if sh:
                            t_sh = int(sh.group(1)) + int(sh.group(2))
                            t_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                            t_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0

                            print(f"      📈 СТАТА (Только 1-й период): Бр={t_sh}, Удал={t_wh}, Штраф={t_pim}", flush=True)

                            if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                msg = (f"🚨 <b>СИГНАЛ P1 (ULTIMATE)</b>\n"
                                       f"🏆 <b>{current_league}</b>\n"
                                       f"🤝 {home} — {away} ({sc_h}:{sc_a})\n"
                                       f"🎯 Броски (P1): {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин\n"
                                       f"🔗 <a href='https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/1'>Открыть статистику P1</a>")
                                await send_tg(msg)
                                print("      ✅ СИГНАЛ В КАНАЛЕ!", flush=True)
                            else:
                                print("      ⚠️ Стата не подходит по условиям.", flush=True)
                        else:
                            print(f"      🗑 В 1-м периоде нет бросков. Лига '{current_league}' в ЧЕРНЫЙ СПИСОК!", flush=True)
                            BLACKLIST.add(current_league)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            
                        TRACKED_MATCHES.add(m_id)

                print(f"📊 Хоккея в лайве (идут на льду): {live_count}", flush=True)
                print("💤 Жду 60 секунд...", flush=True)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())
