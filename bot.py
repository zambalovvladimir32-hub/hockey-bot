import asyncio
import os
import re
import json
import urllib.request
import traceback
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")
WHITELIST_FILE = "whitelist.json"

# 🏆 ЗОЛОТАЯ ДВАДЦАТКА (Вшита намертво, чтобы бот работал даже без файла)
HARDCODED_WHITELIST = {
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
}

notified_matches = set()

def load_whitelist():
    leagues = set(HARDCODED_WHITELIST)
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                leagues.update(json.load(f))
        except:
            pass
    return leagues

WHITELIST = load_whitelist()

def send_tg_sync(text):
    if not TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"⚠️ Ошибка TG: {e}")

async def send_tg(text):
    await asyncio.to_thread(send_tg_sync, text)

API_DOMAIN = None
API_HEADERS = None

async def main():
    print("--- 🎯 БОЕВОЙ СНАЙПЕР: АВТОРСКАЯ СТРАТЕГИЯ ЗАПУЩЕНА ---", flush=True)
    print(f"✅ Элитных лиг на радаре: {len(WHITELIST)}")
    
    global API_DOMAIN, API_HEADERS
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        async def token_handler(request):
            global API_DOMAIN, API_HEADERS
            if not API_HEADERS and "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                if match: 
                    API_DOMAIN = match.group(1)
                    API_HEADERS = {
                        "x-fsign": request.headers["x-fsign"],
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://www.flashscore.com/",
                        "Cache-Control": "no-cache"
                    }
                    print("   🔑 Токен-доступ получен. Начинаю охоту!", flush=True)

        page.on("request", token_handler)
        await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
        
        cycle = 1
        while True:
            try:
                print(f"\n🔄 [Скан {cycle}] Проверяю LIVE матчи...", flush=True)
                
                if not API_HEADERS:
                    await asyncio.sleep(5)
                    continue

                live_matches = await page.evaluate('''() => {
                    let matches = [];
                    let currentLeague = "Unknown";
                    let elements = document.querySelectorAll('.event__header, .event__match--live');
                    
                    for (let el of elements) {
                        if (el.classList.contains('event__header')) {
                            let typeNode = el.querySelector('.event__title--type');
                            let nameNode = el.querySelector('.event__title--name');
                            if (typeNode && nameNode) {
                                currentLeague = typeNode.innerText.trim() + ": " + nameNode.innerText.trim();
                            }
                        } else if (el.classList.contains('event__match--live')) {
                            let stageNode = el.querySelector('.event__stage--block');
                            let stageText = stageNode ? stageNode.innerText.toLowerCase() : "";
                            
                            // Нам нужны матчи, которые на ПЕРЕРЫВЕ или в конце 1-го периода
                            if (stageText.includes('1st') || stageText.includes('1-й') || stageText.includes('перерыв') || stageText.includes('break')) {
                                let matchId = el.id.split('_').pop();
                                let home = el.querySelector('.event__participant--home').innerText.trim();
                                let away = el.querySelector('.event__participant--away').innerText.trim();
                                let scoreHome = el.querySelector('.event__score--home').innerText.trim();
                                let scoreAway = el.querySelector('.event__score--away').innerText.trim();
                                let time = stageText.replace(/\\n/g, ' ').trim();
                                
                                matches.push({
                                    id: matchId, 
                                    league: currentLeague,
                                    home: home,
                                    away: away,
                                    scoreHome: scoreHome,
                                    scoreAway: scoreAway,
                                    time: time
                                });
                            }
                        }
                    }
                    return matches;
                }''')

                # Фильтруем только те матчи, которые есть в нашем Золотом Списке
                valid_matches = [m for m in live_matches if m['league'] in WHITELIST]
                
                for match in valid_matches:
                    m_id = match['id']
                    if m_id in notified_matches:
                        continue

                    # 1. ПРОВЕРКА СТАТУСА: Нам нужен именно первый ПЕРЕРЫВ
                    if 'перерыв' not in match['time'] and 'break' not in match['time']:
                        continue 

                    # 2. ПРОВЕРКА ГОЛОВ: Тотал не больше 1 шайбы
                    goals_home = int(match['scoreHome']) if match['scoreHome'].isdigit() else 0
                    goals_away = int(match['scoreAway']) if match['scoreAway'].isdigit() else 0
                    total_goals = goals_home + goals_away
                    
                    if total_goals > 1:
                        continue 

                    stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                    try:
                        stat_resp = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_resp.text()

                        # ДОП. ЗАЩИТА: Убеждаемся, что вкладки 2-го периода еще нет
                        if re.search(r"(2nd Period|2-й период|2\. Period)", stat_data, re.IGNORECASE):
                            continue

                        # 3. ИЗВЛЕКАЕМ БРОСКИ И ШТРАФЫ
                        sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                        pm = re.search(r"SG÷(?:Penalty Minutes|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                        
                        if not sh: continue 

                        shots_home = int(sh.group(1))
                        shots_away = int(sh.group(2))
                        
                        pm_home, pm_away = 0, 0
                        if pm:
                            pm_home, pm_away = int(pm.group(1)), int(pm.group(2))
                        else:
                            pen = re.search(r"SG÷(?:2-min Penalties|2-х минутные удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                            if pen:
                                pm_home, pm_away = int(pen.group(1)) * 2, int(pen.group(2)) * 2

                        total_pm = pm_home + pm_away

                        # 🚨 АВТОРСКИЙ ТРИГГЕР 🚨
                        # - Бросков >= 13
                        # - Штрафов >= 4 минут
                        if (shots_home >= 13 or shots_away >= 13) and total_pm >= 4:
                            
                            msg = (
                                f"🔥 <b>ИДЕАЛЬНАЯ ПУШКА НА 2-Й ПЕРИОД!</b> 🔥\n\n"
                                f"🏆 <b>Лига:</b> {match['league']}\n"
                                f"🏒 <b>Матч:</b> {match['home']} - {match['away']}\n"
                                f"⏱ <b>Статус:</b> Завершен 1-й период\n"
                                f"📊 <b>Счет:</b> {goals_home}:{goals_away} (Тотал <= 1 ✅)\n\n"
                                f"🎯 <b>Броски в створ:</b> {shots_home} - {shots_away} (Норма 13+ ✅)\n"
                                f"⚖️ <b>Штрафное время:</b> {pm_home} - {pm_away} мин. (Норма 4+ ✅)\n\n"
                                f"💡 <i>Агрессия зашкаливает, шайба не летит. Ждем прорыв во 2-м периоде!</i>\n"
                                f"🔗 <a href='https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/1'>Открыть статистику</a>"
                            )
                            
                            print(f"   🔔 СИГНАЛ! {match['home']} vs {match['away']} | СЧЕТ: {goals_home}:{goals_away} | БРОСКИ: {shots_home}-{shots_away} | ШТРАФЫ: {total_pm}м")
                            await send_tg(msg)
                            notified_matches.add(m_id)

                    except Exception as e:
                        print(f"      ⚠️ Ошибка проверки API матча: {e}", flush=True)

                    await asyncio.sleep(0.5)

            except Exception as e:
                print(f"🚨 Ошибка в цикле сканирования: {e}", flush=True)
                traceback.print_exc()
            
            cycle += 1
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Снайпер остановлен вручную.")
