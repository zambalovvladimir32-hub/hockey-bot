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

# 🏆 ЗОЛОТАЯ ДВАДЦАТКА
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
        except: pass
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
    print("--- 🛡 БОЕВОЙ СНАЙПЕР V13: АБСОЛЮТНОЕ ОРУЖИЕ ---", flush=True)
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
            if "flashscore.ninja" in request.url and "x-fsign" in request.headers:
                match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", request.url)
                if match: 
                    API_DOMAIN = match.group(1)
                    API_HEADERS = {
                        "x-fsign": request.headers["x-fsign"],
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://www.flashscore.com/",
                        "Cache-Control": "no-cache"
                    }

        page.on("request", token_handler)
        
        cycle = 1
        while True:
            try:
                print(f"\n🔄 [Скан {cycle}] Обновляю страницу и собираю свежие данные...", flush=True)
                
                # 1. ПОЛНАЯ ПЕРЕЗАГРУЗКА: Гарантирует актуальный DOM и свежий токен
                await page.goto("https://www.flashscore.com/hockey/", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(2)
                
                if not API_HEADERS:
                    print("   ⚠️ Жду API токен...")
                    await asyncio.sleep(3)
                    continue

                # 2. ПОДГОТОВКА СТРАНИЦЫ (Скрипт-Бульдозер)
                await page.evaluate('''async () => {
                    // Кликаем на вкладку LIVE, чтобы убрать лишние матчи
                    let tabs = document.querySelectorAll('.filters__tab');
                    for (let tab of tabs) {
                        if (tab.textContent.includes('LIVE')) {
                            tab.click();
                            break;
                        }
                    }
                    await new Promise(r => setTimeout(r, 1000));
                    
                    // Скроллим в самый низ, чтобы выгрузились все лиги
                    let lastScrollTop = -1;
                    while (true) {
                        window.scrollBy(0, 1500);
                        await new Promise(r => setTimeout(r, 200));
                        if (document.documentElement.scrollTop === lastScrollTop) break;
                        lastScrollTop = document.documentElement.scrollTop;
                    }
                }''')
                
                # 3. ЖЕСТКОЕ ИЗВЛЕЧЕНИЕ (Парсинг по ID и тегам)
                live_matches = await page.evaluate('''() => {
                    let matches = [];
                    let currentLeague = "Unknown";
                    
                    // Берем заголовки и ВСЕ матчи по их префиксу ID (g_4_)
                    let elements = document.querySelectorAll('.event__header, [id^="g_4_"]');
                    
                    for (let el of elements) {
                        if (el.classList.contains('event__header')) {
                            // ХИМИЧЕСКАЯ ОЧИСТКА: Удаляем SVG и бьем по HTML-тегам
                            let rawHtml = el.innerHTML.replace(/<svg\\b[^>]*>.*?<\\/svg>/gi, '').replace(/<img\\b[^>]*>/gi, '');
                            let textParts = rawHtml.split(/<[^>]+>/).map(s => s.trim()).filter(s => s.length > 0);
                            
                            if (textParts.length >= 2) {
                                currentLeague = textParts[0] + ": " + textParts[1];
                            } else if (textParts.length === 1) {
                                currentLeague = textParts[0];
                            }
                        } 
                        else if (el.id && el.id.startsWith('g_4_')) {
                            let stageText = el.textContent.toLowerCase();
                            
                            if (stageText.includes('1st') || stageText.includes('1-й') || stageText.includes('перерыв') || stageText.includes('break') || stageText.includes('period 1')) {
                                let matchId = el.id.split('_').pop();
                                
                                let homeNode = el.querySelector('.event__participant--home');
                                let awayNode = el.querySelector('.event__participant--away');
                                let home = homeNode ? homeNode.textContent.trim() : "Team 1";
                                let away = awayNode ? awayNode.textContent.trim() : "Team 2";
                                
                                let scoreHomeNode = el.querySelector('.event__score--home');
                                let scoreAwayNode = el.querySelector('.event__score--away');
                                
                                let hMatch = (scoreHomeNode ? scoreHomeNode.textContent : "").match(/\\d+/);
                                let aMatch = (scoreAwayNode ? scoreAwayNode.textContent : "").match(/\\d+/);
                                
                                let scoreHome = hMatch ? hMatch[0] : "0";
                                let scoreAway = aMatch ? aMatch[0] : "0";
                                
                                let stageNode = el.querySelector('.event__stage--block');
                                let time = stageNode ? stageNode.textContent.trim() : "1st";
                                
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

                valid_matches = []
                
                # 4. УМНАЯ СВЕРКА
                for m in live_matches:
                    print(f"   [РАДАР] {m['home']} - {m['away']} | 🏆 {m['league']}")
                    
                    live_league_lower = m['league'].lower()
                    
                    for wl_league in WHITELIST:
                        base_league = wl_league.split(" - ")[0].strip().lower()
                        if base_league in live_league_lower:
                            valid_matches.append(m)
                            break 
                
                print(f"👀 Итог сканирования: Найдено в 1-м периоде {len(live_matches)} | Подходят под Белый Список: {len(valid_matches)}")

                # 5. РЕНТГЕН СТАТИСТИКИ (Авторская Стратегия)
                for match in valid_matches:
                    m_id = match['id']
                    if m_id in notified_matches:
                        continue

                    # Проверка перерыва
                    time_lower = match['time'].lower()
                    if 'перерыв' not in time_lower and 'break' not in time_lower:
                        continue 

                    goals_home = int(match['scoreHome'])
                    goals_away = int(match['scoreAway'])
                    total_goals = goals_home + goals_away
                    
                    if total_goals > 1:
                        continue 

                    stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                    try:
                        stat_resp = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_resp.text()

                        if re.search(r"(2nd Period|2-й период|2\. Period)", stat_data, re.IGNORECASE):
                            continue

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

                        # 🚨 ТРИГГЕР: >=13 бросков и >= 4 мин штрафа
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
                        pass

                    await asyncio.sleep(0.5)

            except Exception as e:
                print(f"🚨 Системная Ошибка: {e}", flush=True)
                traceback.print_exc()
            
            cycle += 1
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
