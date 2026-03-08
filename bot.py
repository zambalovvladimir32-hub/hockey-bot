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
STRATEGY_MIN_PIM = 4      

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
tracked_matches = {} # 🎯 БАЗА ДЛЯ АВТО-ДОЖИМА И ОТЧЕТОВ

def load_whitelist():
    leagues = set(HARDCODED_WHITELIST)
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                user_leagues = json.load(f)
                leagues.update(user_leagues)
        except Exception as e: 
            pass
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

async def send_tg(text):
    await asyncio.to_thread(send_tg_sync, text)

API_DOMAIN = None
API_HEADERS = None

async def main():
    print("--- 🎯 БОЕВОЙ СНАЙПЕР: МОДУЛЬ АВТО-ДОЖИМА АКТИВИРОВАН ---", flush=True)
    print(f"✅ Всего лиг на радаре: {len(WHITELIST)}")
    
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
                    print("   🔑 API-Токен захвачен. База открыта!", flush=True)

        page.on("request", token_handler)
        await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
        
        cycle = 1
        while True:
            try:
                print(f"\n🔄 [Скан {cycle}] Радар крутится... | 🎯 В слежке: {len(tracked_matches)}", flush=True)
                
                if not API_HEADERS:
                    await asyncio.sleep(5)
                    continue

                await page.evaluate('''async () => {
                    let liveTab = Array.from(document.querySelectorAll('.filters__tab')).find(el => el.textContent.includes('LIVE'));
                    if (liveTab) liveTab.click();
                    await new Promise(r => setTimeout(r, 1000));
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(r => setTimeout(r, 500));
                }''')

                # ТЕПЕРЬ СОБИРАЕМ ВООБЩЕ ВСЕ МАТЧИ В ЛАЙВЕ
                live_matches = await page.evaluate('''() => {
                    let matches = [];
                    let elements = document.querySelectorAll('[id^="g_4_"]');
                    
                    for (let el of elements) {
                        let stageNode = el.querySelector('[class*="stage--block"]');
                        let stageText = stageNode ? stageNode.textContent.toLowerCase() : "";
                        
                        let currentLeague = "Unknown";
                        let prev = el.previousElementSibling;
                        
                        while (prev && prev.id && prev.id.startsWith('g_4_')) {
                            prev = prev.previousElementSibling;
                        }
                        
                        if (prev) {
                            let titleAttr = prev.getAttribute('title');
                            if (titleAttr && titleAttr.includes(':')) {
                                currentLeague = titleAttr;
                            } else {
                                let raw = prev.innerHTML.replace(/<svg[^>]*>.*?<\\/svg>/gi, '').replace(/<[^>]+>/g, '|');
                                let parts = raw.split('|').map(s => s.trim()).filter(s => s.length > 1);
                                if (parts.length >= 2) {
                                    currentLeague = parts[0] + ": " + parts[1];
                                } else if (parts.length === 1) {
                                    currentLeague = parts[0];
                                } else {
                                    currentLeague = prev.textContent.trim().replace(/\\n/g, ': ');
                                }
                            }
                        }

                        let matchId = el.id.split('_').pop();
                        let home = el.querySelector('[class*="participant--home"]')?.textContent.trim() || "Team 1";
                        let away = el.querySelector('[class*="participant--away"]')?.textContent.trim() || "Team 2";
                        let hMatch = (el.querySelector('[class*="score--home"]')?.textContent || "").match(/\\d+/);
                        let aMatch = (el.querySelector('[class*="score--away"]')?.textContent || "").match(/\\d+/);
                        
                        matches.push({
                            id: matchId, 
                            league: currentLeague,
                            home: home,
                            away: away,
                            scoreHome: hMatch ? hMatch[0] : "0",
                            scoreAway: aMatch ? aMatch[0] : "0",
                            time: stageText.replace(/\\n/g, ' ').trim()
                        });
                    }
                    return matches;
                }''')

                valid_matches_for_new_signals = []
                
                # ПРОГОНЯЕМ МАТЧИ ЧЕРЕЗ ФИЛЬТРЫ
                for m in live_matches:
                    m_id = m['id']
                    stageText = m['time']
                    goals_home = int(m['scoreHome'])
                    goals_away = int(m['scoreAway'])
                    total_goals = goals_home + goals_away

                    # ==================================================
                    # 1. МОДУЛЬ ОТЧЕТОВ: ПРОВЕРЯЕМ УЖЕ НАЙДЕННЫЕ МАТЧИ
                    # ==================================================
                    if m_id in tracked_matches:
                        tracked = tracked_matches[m_id]

                        # ⚽ ПРОВЕРКА НА ГОЛ (Тотал стал больше, чем был)
                        if total_goals > tracked['initial_goals']:
                            msg = (
                                f"✅ <b>ЦЕЛЬ ПОРАЖЕНА! (ГОЛ)</b> ✅\n\n"
                                f"🏆 <b>Лига:</b> {escape_html(tracked['league'])}\n"
                                f"🏒 <b>Матч:</b> {escape_html(tracked['home'])} - {escape_html(tracked['away'])}\n"
                                f"🥅 <b>Счет стал:</b> {goals_home}:{goals_away}\n"
                                f"💸 <i>Ставка зашла! Идем дальше!</i>"
                            )
                            print(f"   🎯 ОТЧЕТ: ГОЛ! {tracked['home']} - {tracked['away']} ({goals_home}:{goals_away})")
                            await send_tg(msg)
                            del tracked_matches[m_id] # Удаляем из слежки
                            continue

                        # 🛑 ПРОВЕРКА НА МИНУС (Начался второй перерыв или матч кончился)
                        is_2nd_break = any(x in stageText for x in ['перерыв', 'break', 'pause', 'intermission', 'rust']) and any(x in stageText for x in ['2nd', '2-й', '2.'])
                        is_finished = any(x in stageText for x in ['завершен', 'finished', 'конец', 'ft', 'после'])

                        if is_2nd_break or is_finished:
                            msg = (
                                f"❌ <b>ПРОМАХ (МИНУС)</b> ❌\n\n"
                                f"🏆 <b>Лига:</b> {escape_html(tracked['league'])}\n"
                                f"🏒 <b>Матч:</b> {escape_html(tracked['home'])} - {escape_html(tracked['away'])}\n"
                                f"🛑 <b>Итог:</b> Второй период засушили.\n"
                                f"📉 <b>Счет остался:</b> {goals_home}:{goals_away}"
                            )
                            print(f"   ☠️ ОТЧЕТ: МИНУС. {tracked['home']} - {tracked['away']} ({goals_home}:{goals_away})")
                            await send_tg(msg)
                            del tracked_matches[m_id] # Удаляем из слежки
                            continue
                        
                        # Если гола нет и перерыв еще не настал - просто идем дальше
                        continue 

                    # ==================================================
                    # 2. МОДУЛЬ РАДАРА: ИЩЕМ НОВЫЕ СИГНАЛЫ
                    # ==================================================
                    if m_id in notified_matches:
                        continue # Если уже давали сигнал, но слежка кончилась, пропускаем

                    # Ищем ТОЛЬКО 1-й перерыв для новых сигналов
                    is_1st_break = any(x in stageText for x in ['перерыв', 'break', 'pause', 'intermission', 'rust']) and not any(x in stageText for x in ['2nd', '2-й', '3rd', '3-й', '2.', '3.'])

                    if is_1st_break:
                        live_league_lower = m['league'].lower()
                        for wl_league in WHITELIST:
                            base_league = wl_league.split(" - ")[0].strip().lower()
                            parts = [p.strip() for p in base_league.split(':')]
                            
                            if len(parts) >= 2:
                                country_match = (parts[0] in live_league_lower) or (parts[0] == "czech republic" and "czechia" in live_league_lower)
                                league_match = (parts[-1] in live_league_lower) or (parts[-1] == "ehl" and "elitehockey" in live_league_lower) or (parts[-1] == "del" and "deutsche" in live_league_lower)
                                
                                if country_match and league_match:
                                    m['beautiful_league'] = wl_league
                                    valid_matches_for_new_signals.append(m)
                                    break
                            else:
                                if base_league in live_league_lower:
                                    m['beautiful_league'] = wl_league
                                    valid_matches_for_new_signals.append(m)
                                    break

                # ==================================================
                # 3. ТЯНЕМ СТАТИСТИКУ И СТРЕЛЯЕМ СИГНАЛАМИ
                # ==================================================
                if len(valid_matches_for_new_signals) > 0:
                    print(f"👀 Найдено новых матчей на перерыве: {len(valid_matches_for_new_signals)}")

                for match in valid_matches_for_new_signals:
                    m_id = match['id']
                    goals_home = int(match['scoreHome'])
                    goals_away = int(match['scoreAway'])
                    total_goals = goals_home + goals_away
                    
                    if total_goals > STRATEGY_MAX_GOALS:
                        print(f"   ❌ Пропуск: {match['home']} - {match['away']} | Слишком много голов: {total_goals}")
                        continue 

                    stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                    try:
                        stat_resp = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_resp.text()

                        if re.search(r"(2nd Period|2-й период|2\. Period)", stat_data, re.IGNORECASE):
                            continue

                        sh = re.search(r"SG÷(?:Shots on Goal|Shots|Броски в створ|Броски)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                        pm = re.search(r"SG÷(?:PIM|Penalty Minutes|Штрафное время|Штраф)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                        
                        if not sh: 
                            continue 

                        shots_home = int(sh.group(1))
                        shots_away = int(sh.group(2))
                        total_shots = shots_home + shots_away
                        
                        pm_home, pm_away = 0, 0
                        if pm:
                            pm_home, pm_away = int(pm.group(1)), int(pm.group(2))
                        else:
                            pen = re.search(r"SG÷(?:Penalties|2-min Penalties|2-х минутные удаления|Удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data, re.IGNORECASE)
                            if pen:
                                pm_home, pm_away = int(pen.group(1)) * 2, int(pen.group(2)) * 2

                        total_pm = pm_home + pm_away

                        print(f"   📊 СТАТА | {match['home']} - {match['away']} | Броски: {total_shots}/{STRATEGY_MIN_SHOTS} | Штраф: {total_pm}м/{STRATEGY_MIN_PIM}м")

                        # ФИНАЛЬНЫЙ ТРИГГЕР
                        if total_shots >= STRATEGY_MIN_SHOTS and total_pm >= STRATEGY_MIN_PIM:
                            
                            safe_league = escape_html(match['beautiful_league'])
                            safe_home = escape_html(match['home'])
                            safe_away = escape_html(match['away'])

                            msg = (
                                f"🔥 <b>ИДЕАЛЬНАЯ ПУШКА НА 2-Й ПЕРИОД!</b> 🔥\n\n"
                                f"🏆 <b>Лига:</b> {safe_league}\n"
                                f"🏒 <b>Матч:</b> {safe_home} - {safe_away}\n"
                                f"⏱ <b>Статус:</b> Перерыв после 1-го периода\n"
                                f"📊 <b>Счет:</b> {goals_home}:{goals_away} (Тотал ≤ {STRATEGY_MAX_GOALS} ✅)\n\n"
                                f"🎯 <b>Броски в створ:</b> {shots_home} - {shots_away} (Всего {total_shots}, Норма {STRATEGY_MIN_SHOTS}+ ✅)\n"
                                f"⚖️ <b>Штрафное время:</b> {pm_home} - {pm_away} мин. (Всего {total_pm}м, Норма {STRATEGY_MIN_PIM}+ ✅)\n\n"
                                f"💡 <i>Беру матч под наблюдение. Ждем гол!</i>\n"
                                f"🔗 <a href='https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/1'>Открыть статистику</a>"
                            )
                            
                            print(f"   ✅ СИГНАЛ! Беру в слежку: {match['home']} - {match['away']}")
                            await send_tg(msg)
                            
                            # ДОБАВЛЯЕМ В БАЗУ ДЛЯ АВТО-ДОЖИМА
                            notified_matches.add(m_id)
                            tracked_matches[m_id] = {
                                'home': match['home'],
                                'away': match['away'],
                                'league': match['beautiful_league'],
                                'initial_goals': total_goals
                            }
                        else:
                            print(f"   ❌ Не хватило цифр: {match['home']} - {match['away']}")

                    except Exception as e:
                        pass

                    await asyncio.sleep(0.5)

            except Exception as e:
                print(f"🚨 Ошибка: {e}", flush=True)
            
            cycle += 1
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
