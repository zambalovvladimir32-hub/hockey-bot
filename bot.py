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
WHITELIST_FILE = "whitelist.json" # Файл для твоих личных лиг

# 🚨 ТВОИ ТРИГГЕРЫ 🚨
STRATEGY_MAX_GOALS = 1    # Максимум голов (в сумме)
STRATEGY_MIN_SHOTS = 13   # Минимум бросков (хотя бы у одной команды)
STRATEGY_MIN_PIM = 4      # Минимум штрафных минут (в сумме за 1 период)

# 🏆 БАЗОВЫЙ БЕЛЫЙ СПИСОК (Можешь добавлять сюда или в whitelist.json)
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

# --- ЗАГРУЗКА ВСЕХ ТВОИХ ЛИГ ---
def load_whitelist():
    leagues = set(HARDCODED_WHITELIST)
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                user_leagues = json.load(f)
                leagues.update(user_leagues)
                print(f"📁 Подгружено {len(user_leagues)} лиг из файла whitelist.json")
        except Exception as e: 
            print(f"⚠️ Ошибка чтения whitelist.json: {e}")
    return leagues

WHITELIST = load_whitelist()

# --- ОТПРАВКА В ТЕЛЕГРАМ ---
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
    print("--- 🎯 БОЕВОЙ СНАЙПЕР: СТРАТЕГИЯ АКТИВИРОВАНА ---", flush=True)
    print(f"✅ Всего лиг на радаре: {len(WHITELIST)}")
    print(f"⚙️ Настройки: Голы <= {STRATEGY_MAX_GOALS} | Броски >= {STRATEGY_MIN_SHOTS} | Штрафы >= {STRATEGY_MIN_PIM}м")
    
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
                    print("   🔑 API-Токен захвачен. Погнали!", flush=True)

        page.on("request", token_handler)
        await page.goto("https://www.flashscore.com/hockey/", timeout=60000)
        
        cycle = 1
        while True:
            try:
                print(f"\n🔄 [Скан {cycle}] Жду ПЕРЕРЫВЫ в LIVE матчах...", flush=True)
                
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

                # СБОР МАТЧЕЙ (ТОЛЬКО НА ПЕРЕРЫВЕ) И СТРУКТУРНЫЙ ПАРСИНГ ЛИГ
                live_matches = await page.evaluate('''() => {
                    let matches = [];
                    let elements = document.querySelectorAll('[id^="g_4_"]');
                    
                    for (let el of elements) {
                        let stageNode = el.querySelector('[class*="stage--block"]');
                        let stageText = stageNode ? stageNode.textContent.toLowerCase() : "";
                        
                        // ИЩЕМ ТОЛЬКО ПЕРЕРЫВ ПОСЛЕ 1-ГО ПЕРИОДА
                        if (stageText.includes('перерыв') || stageText.includes('break')) {
                            if (!stageText.includes('2nd') && !stageText.includes('2-й') && !stageText.includes('3rd') && !stageText.includes('3-й')) {
                                
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
                        }
                    }
                    return matches;
                }''')

                valid_matches = []
                
                # 🧠 СВЕРКА ЛИГ (Независимо от порядка слов)
                for m in live_matches:
                    print(f"   [РАДАР-ПЕРЕРЫВ] {m['home']} - {m['away']} | 🏆 {m['league']}")
                    live_league_lower = m['league'].lower()
                    
                    for wl_league in WHITELIST:
                        base_league = wl_league.split(" - ")[0].strip().lower()
                        required_parts = [p.strip() for p in base_league.split(':')]
                        
                        if all(part in live_league_lower for part in required_parts):
                            # Подменяем кривое название с сайта на красивое из твоей базы
                            m['beautiful_league'] = wl_league
                            valid_matches.append(m)
                            break 
                
                print(f"👀 Итог: Найдено на 1-м перерыве: {len(live_matches)} | В белом списке: {len(valid_matches)}")

                # 🚀 ПРОВЕРКА ПО ТВОЕЙ СТРАТЕГИИ 🚀
                for match in valid_matches:
                    m_id = match['id']
                    if m_id in notified_matches:
                        continue

                    # 1. ПРОВЕРКА ГОЛОВ
                    goals_home = int(match['scoreHome'])
                    goals_away = int(match['scoreAway'])
                    total_goals = goals_home + goals_away
                    if total_goals > STRATEGY_MAX_GOALS:
                        continue 

                    # 2. ПРОВЕРКА СТАТИСТИКИ (За 1-й период)
                    stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                    try:
                        stat_resp = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_resp.text()

                        # Защита: Если началась статистика 2-го периода, скипаем
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

                        # 3. ФИНАЛЬНЫЙ ТРИГГЕР: Броски и Штрафы
                        if (shots_home >= STRATEGY_MIN_SHOTS or shots_away >= STRATEGY_MIN_SHOTS) and total_pm >= STRATEGY_MIN_PIM:
                            
                            msg = (
                                f"🔥 <b>ИДЕАЛЬНАЯ ПУШКА НА 2-Й ПЕРИОД!</b> 🔥\n\n"
                                f"🏆 <b>Лига:</b> {match['beautiful_league']}\n"
                                f"🏒 <b>Матч:</b> {match['home']} - {match['away']}\n"
                                f"⏱ <b>Статус:</b> Перерыв после 1-го периода\n"
                                f"📊 <b>Счет:</b> {goals_home}:{goals_away} (Тотал <= {STRATEGY_MAX_GOALS} ✅)\n\n"
                                f"🎯 <b>Броски в створ:</b> {shots_home} - {shots_away} (Норма {STRATEGY_MIN_SHOTS}+ ✅)\n"
                                f"⚖️ <b>Штрафное время:</b> {pm_home} - {pm_away} мин. (Норма {STRATEGY_MIN_PIM}+ ✅)\n\n"
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
                print(f"🚨 Ошибка: {e}", flush=True)
            
            cycle += 1
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
