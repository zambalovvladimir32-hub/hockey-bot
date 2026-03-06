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

BLACKLIST_FILE = "blacklist.json"
WHITELIST_FILE = "whitelist.json"

def load_list(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_list(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(list(data), f, ensure_ascii=False, indent=4)

BLACKLIST = load_list(BLACKLIST_FILE)
WHITELIST = load_list(WHITELIST_FILE)

# Если в прошлом запуске NHL или другие топы улетели в ЧС по ошибке - удаляем их оттуда
for false_negative in ["USA: NHL", "USA: AHL", "SWEDEN: SHL"]:
    if false_negative in BLACKLIST:
        BLACKLIST.remove(false_negative)

def send_tg_sync(text):
    if not TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

async def send_tg(text):
    await asyncio.to_thread(send_tg_sync, text)

async def send_tg_chunked(text):
    for i in range(0, len(text), 4000):
        await send_tg(text[i:i+4000])
        await asyncio.sleep(1)

API_DOMAIN = None
API_HEADERS = None

async def main():
    print("--- 🧠 БОТ-АРХИВАРИУС V7: АБСОЛЮТНОЕ ОРУЖИЕ ---", flush=True)
    global API_DOMAIN, API_HEADERS, BLACKLIST, WHITELIST
    
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
                    print("   🔑 API-Токен успешно захвачен!", flush=True)

        page.on("request", token_handler)

        for day in range(8):
            try:
                day_label = "СЕГОДНЯ" if day == 0 else f"{day} ДНЕЙ НАЗАД"
                print(f"\n⏳ ПРЫЖОК ВО ВРЕМЕНИ: {day_label} (d=-{day})", flush=True)
                
                await page.goto(f"https://www.flashscore.com/hockey/?d=-{day}", timeout=60000)
                
                try:
                    await page.wait_for_selector('.event__match', timeout=15000)
                    await asyncio.sleep(2)
                except:
                    print(f"❌ На странице нет матчей для дня -{day}.", flush=True)
                    continue

                if not API_HEADERS:
                    print("⚠️ Токен еще не пойман, жду...", flush=True)
                    await asyncio.sleep(3)

                # --- 1. УМНЫЙ ПАРСИНГ ID МАТЧЕЙ ---
                # Берем только по 1 матчу из лиги, и ТОЛЬКО если у него есть счет (сыгран)
                match_ids = await page.evaluate('''() => {
                    let ids = [];
                    let headers = document.querySelectorAll('.event__header');
                    for (let header of headers) {
                        let el = header.nextElementSibling;
                        while(el && !el.classList.contains('event__header')) {
                            if (el.classList.contains('event__match')) {
                                let scoreHome = el.querySelector('.event__score--home');
                                // Условие: матч должен иметь счет (не быть будущим)
                                if (scoreHome && scoreHome.innerText.trim() !== '') {
                                    let id = el.id.split('_').pop();
                                    ids.push(id);
                                    break; // Нашли 1 сыгранный матч - переходим к следующей лиге
                                }
                            }
                            el = el.nextElementSibling;
                        }
                    }
                    return ids;
                }''')

                print(f"✅ Найдено сыгранных лиг на странице: {len(match_ids)}. Сканирую...", flush=True)

                # --- 2. ИЗВЛЕЧЕНИЕ ИМЕНИ ЛИГИ ИЗ HTML + ПРОВЕРКА СТАТИСТИКИ ---
                for m_id in match_ids:
                    try:
                        # Получаем HTML-код страницы матча (быстрый GET запрос)
                        html_url = f"https://www.flashscore.com/match/{m_id}/#/match-summary"
                        html_resp = await context.request.get(html_url)
                        html_text = await html_resp.text()

                        # Ищем идеальное имя лиги в теге <title>
                        # Пример: <title>Команда 1 - Команда 2 | Hockey, USA: NHL | Flashscore.com</title>
                        title_match = re.search(r"Hockey,\s*([^|<]+)", html_text, re.IGNORECASE)
                        if not title_match:
                            continue
                            
                        league_name = title_match.group(1).strip()

                        # Если мы уже проверили эту лигу в прошлые дни - пропускаем!
                        if league_name in BLACKLIST or league_name in WHITELIST:
                            continue

                        print(f"   🔍 🏆 {league_name}", flush=True)

                        # Проверяем броски
                        stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                        stat_resp = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_resp.text()

                        if not stat_data or "SG÷" not in stat_data:
                            print(f"      🗑 Пусто -> ЧС", flush=True)
                            BLACKLIST.add(league_name)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            continue

                        p1_data = stat_data
                        if "~SE÷" in stat_data:
                            for tab in stat_data.split("~SE÷"):
                                if re.search(r"^(1st Period|1-й период|1\. Period|Period 1)", tab, re.IGNORECASE):
                                    p1_data = tab
                                    break

                        sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", p1_data, re.IGNORECASE)

                        if sh:
                            print(f"      ✅ Броски есть! -> БЕЛЫЙ СПИСОК", flush=True)
                            WHITELIST.add(league_name)
                            save_list(WHITELIST_FILE, WHITELIST)
                        else:
                            print(f"      🗑 Нет бросков -> ЧС", flush=True)
                            BLACKLIST.add(league_name)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            
                    except Exception as e:
                        pass
                        
                    await asyncio.sleep(0.3) 

            except Exception as e:
                print(f"🚨 ОШИБКА НА ДНЕ {day}: {e}", flush=True)
                traceback.print_exc()

        print(f"\n🏁 ПУТЕШЕСТВИЕ ВО ВРЕМЕНИ ЗАВЕРШЕНО!")
        print(f"📊 Итоговые знания: {len(WHITELIST)} хороших лиг, {len(BLACKLIST)} мусорных.")
        print("📨 Отправляю отчет в Telegram...", flush=True)

        if WHITELIST:
            sorted_whitelist = sorted(list(WHITELIST))
            tg_msg = f"🏆 <b>БЕЛЫЙ СПИСОК ЛИГ ({len(WHITELIST)} шт.)</b>\n<i>Собрано за 7 дней:</i>\n\n"
            for league in sorted_whitelist:
                tg_msg += f"✅ {league}\n"
            
            await send_tg_chunked(tg_msg)
            print("✅ Отчет успешно отправлен в TG!", flush=True)
        else:
            await send_tg("🤷‍♂️ За 7 дней не найдено ни одной хорошей лиги.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
