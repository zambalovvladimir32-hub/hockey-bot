import asyncio
import os
import re
import json
import urllib.request
import traceback
from playwright.async_api import async_playwright

# ==========================================
# ⚙️ ПАНЕЛЬ УПРАВЛЕНИЯ ТВОЕЙ СТРАТЕГИЕЙ ⚙️
# ==========================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
WHITELIST_FILE = "whitelist.json"

# 🚨 ТВОИ ТРИГГЕРЫ (ОБЩИЕ НА ДВЕ КОМАНДЫ) 🚨
STRATEGY_MAX_GOALS = 1    
STRATEGY_MIN_SHOTS = 13   
STRATEGY_MIN_PIM = 2       # Снизили до 2 минут (было 4)
STRATEGY_MIN_PENALTIES = 1 # Добавили от 1 удаления

# 🏆 БАЗОВЫЙ БЕЛЫЙ СПИСОК
HARDCODED_WHITELIST = [
    "AUSTRIA: ICE Hockey League",
    "AUSTRIA: ICE Hockey League - Play Offs",
    "CZECH REPUBLIC: Extraliga",
    "CZECH REPUBLIC: Maxa liga - Play Offs",
    "EUROPE: Champions League - Play Offs",
    "FINLAND: Liiga",
    "FINLAND: Mestis - Play Offs",
    "FINLAND: Mestis - Relegation",
    "GERMANY: DEL",
    "GERMANY: DEL2",
    "NORWAY: EHL - Play Offs",
    "NORWAY: EHL - Relegation",
    "POLAND: Polish Hockey League - Play Offs",
    "RUSSIA: KHL",
    "SWEDEN: HockeyAllsvenskan",
    "SWEDEN: SHL",
    "SWITZERLAND: National League",
    "USA: AHL",
    "USA: NHL",
    "USA: SPHL"
]

notified_matches = set()
tracked_matches = {} 

def load_whitelist():
    leagues = set(HARDCODED_WHITELIST)
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                user_leagues = json.load(f)
                leagues.update(user_leagues)
        except: pass
    return leagues

WHITELIST = load_whitelist()

def escape_html(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def send_tg_sync(text):
    if not TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"⚠️ Ошибка TG: {e}")

async def main():
    print(f"--- 🎯 БОЕВОЙ СНАЙПЕР: ЛОВУШКА РАСШИРЕНА (PIM >= {STRATEGY_MIN_PIM}) ---", flush=True)
    
    global API_DOMAIN, API_HEADERS
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(user_agent="Mozilla/5.0")
        page = await context.new_page()

        async def token_handler(request):
            global API_DOMAIN, API_HEADERS
            if not API_HEADERS and "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                if match: 
                    API_DOMAIN = match.group(1)
                    API_HEADERS = {"x-fsign": request.headers["x-fsign"], "Referer": "https://www.flashscore.com/"}
                    print("   🔑 API-Токен захвачен.")

        page.on("request", token_handler)
        await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
        
        while True:
            try:
                if not API_HEADERS:
                    await asyncio.sleep(5); continue

                await page.evaluate('''async () => {
                    let liveTab = Array.from(document.querySelectorAll('.filters__tab')).find(el => el.textContent.includes('LIVE'));
                    if (liveTab) liveTab.click();
                    await new Promise(r => setTimeout(r, 1000));
                }''')

                # Сбор всех матчей
                live_matches = await page.evaluate('''() => {
                    let matches = [];
                    document.querySelectorAll('[id^="g_4_"]').forEach(el => {
                        let hMatch = (el.querySelector('[class*="score--home"]')?.textContent || "").match(/\\d+/);
                        let aMatch = (el.querySelector('[class*="score--away"]')?.textContent || "").match(/\\d+/);
                        matches.push({
                            id: el.id.split('_').pop(),
                            home: el.querySelector('[class*="participant--home"]')?.textContent.trim() || "T1",
                            away: el.querySelector('[class*="participant--away"]')?.textContent.trim() || "T2",
                            scoreHome: hMatch ? hMatch[0] : "0",
                            scoreAway: aMatch ? aMatch[0] : "0",
                            time: el.querySelector('[class*="stage--block"]')?.textContent.toLowerCase() || ""
                        });
                    });
                    return matches;
                }''')

                for m in live_matches:
                    m_id = m['id']
                    goals = int(m['scoreHome']) + int(m['scoreAway'])

                    # ОТЧЕТЫ
                    if m_id in tracked_matches:
                        tracked = tracked_matches[m_id]
                        if goals > tracked['initial_goals'] and not any(x in m['time'] for x in ['3rd', '3-й', '3.']):
                            await send_tg(f"✅ <b>ГОЛ ВО 2-М!</b>\n{escape_html(tracked['home'])} - {escape_html(tracked['away'])}\nСчет: {m['scoreHome']}:{m['scoreAway']}")
                            del tracked_matches[m_id]; continue
                        if any(x in m['time'] for x in ['2nd', '2-й', '2.']) and any(y in m['time'] for y in ['break', 'pause', 'перерыв']):
                            if goals == tracked['initial_goals']:
                                await send_tg(f"❌ <b>МИНУС (СУХО)</b>\n{escape_html(tracked['home'])} - {escape_html(tracked['away'])}")
                                del tracked_matches[m_id]; continue

                    # НОВЫЕ СИГНАЛЫ (1-й перерыв)
                    if m_id not in notified_matches and goals <= STRATEGY_MAX_GOALS:
                        if any(x in m['time'] for x in ['break', 'pause', 'перерыв']) and not any(y in m['time'] for y in ['2nd', '2-й', '2.']):
                            
                            stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                            try:
                                resp = await context.request.get(stat_url, headers=API_HEADERS)
                                stat_data = await resp.text()
                                
                                sh = re.search(r"SG÷(?:Shots on Goal|Shots)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                                pm = re.search(r"SG÷(?:PIM|Penalty Minutes)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                                pen = re.search(r"SG÷(?:Penalties|2-min Penalties)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)

                                if sh:
                                    total_shots = int(sh.group(1)) + int(sh.group(2))
                                    total_pim = (int(pm.group(1)) + int(pm.group(2))) if pm else 0
                                    total_pen = (int(pen.group(1)) + int(pen.group(2))) if pen else 0

                                    # ПРОВЕРКА ОБНОВЛЕННЫХ ТРИГГЕРОВ
                                    if total_shots >= STRATEGY_MIN_SHOTS and (total_pim >= STRATEGY_MIN_PIM or total_pen >= STRATEGY_MIN_PENALTIES):
                                        await send_tg(f"🔥 <b>ПУШКА!</b>\n🏒 {escape_html(m['home'])} - {escape_html(m['away'])}\n📊 Счет: {m['scoreHome']}:{m['scoreAway']}\n🎯 Броски: {total_shots}\n⚖️ Штраф: {total_pim}м ({total_pen} уд.)")
                                        notified_matches.add(m_id)
                                        tracked_matches[m_id] = {'home': m['home'], 'away': m['away'], 'initial_goals': goals}
                                    else:
                                        print(f"   ❌ {m['home']} - {m['away']} | Стата: {total_shots}бр, {total_pim}м ({total_pen}уд)")
                            except: pass

                await asyncio.sleep(60)
            except Exception as e:
                print(f"🚨 Ошибка: {e}"); await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
