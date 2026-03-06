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

def send_tg_sync(text):
    if not TOKEN or not CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"⚠️ Ошибка отправки в TG: {e}")

async def send_tg(text):
    await asyncio.to_thread(send_tg_sync, text)

async def send_tg_chunked(text):
    for i in range(0, len(text), 4000):
        await send_tg(text[i:i+4000])
        await asyncio.sleep(1)

API_DOMAIN = None
API_HEADERS = None

async def main():
    print("--- 🧠 БОТ-АРХИВАРИУС: ГИБРИДНЫЙ ПАРСЕР (ЗАЩИТА ОТ КРАШЕЙ) ---", flush=True)
    global API_DOMAIN, API_HEADERS, BLACKLIST, WHITELIST
    
    async with async_playwright() as p:
        # Добавил флаги для экономии памяти в Docker
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage', 
                '--disable-blink-features=AutomationControlled',
                '--disable-gpu',
                '--single-process' # Экономит ОЗУ
            ]
        )
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        async def handle_request(request):
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
                    print("   🔑 API-Токен успешно пойман!", flush=True)

        page.on("request", handle_request)

        for day in range(8):
            try:
                day_label = "СЕГОДНЯ" if day == 0 else f"{day} ДНЕЙ НАЗАД"
                print(f"\n⏳ ПРЫЖОК ВО ВРЕМЕНИ: {day_label} (d=-{day})", flush=True)
                
                await page.goto(f"https://www.flashscore.com/hockey/?d=-{day}", timeout=60000)
                
                # Ждем матчи с перехватом ошибки (если матчей нет, не крашимся)
                try:
                    await page.wait_for_selector('.event__match', timeout=15000)
                    await asyncio.sleep(3) # Рендер DOM
                except Exception:
                    print(f"❌ Матчи на странице не прогрузились (или их нет). Идем дальше...", flush=True)
                    continue

                if not API_HEADERS:
                    print("⚠️ Токен еще не пойман, жду 3 секунды...", flush=True)
                    await asyncio.sleep(3)

                # --- НЕУБИВАЕМЫЙ JS-ЭКСТРАКТОР ---
                leagues_dict = await page.evaluate('''() => {
                    const data = {};
                    let currentLeague = "Unknown League";
                    const elements = document.querySelectorAll('.event__header, .event__match');
                    
                    for (const el of elements) {
                        if (el.classList.contains('event__header')) {
                            let typeNode = el.querySelector('.event__title--type');
                            let nameNode = el.querySelector('.event__title--name');
                            
                            if (typeNode && nameNode) {
                                currentLeague = typeNode.innerText.trim() + ": " + nameNode.innerText.trim();
                            } else {
                                currentLeague = el.innerText.replace(/\\n/g, ' ').replace(/\s+/g, ' ').trim();
                            }
                        } else if (el.classList.contains('event__match')) {
                            if (!data[currentLeague]) {
                                let matchId = el.id; 
                                if (matchId) {
                                    let parts = matchId.split('_');
                                    let m_id = parts[parts.length - 1];
                                    if (m_id && m_id.length === 8) {
                                        data[currentLeague] = m_id;
                                    }
                                }
                            }
                        }
                    }
                    return data;
                }''')

                print(f"✅ Найдено уникальных лиг: {len(leagues_dict)}. Идет проверка...", flush=True)

                for league, m_id in leagues_dict.items():
                    if league in BLACKLIST or league in WHITELIST:
                        continue

                    print(f"   🔍 🏆 {league}", flush=True)

                    if not API_DOMAIN or not API_HEADERS:
                        continue

                    stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                    try:
                        stat_response = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_response.text()

                        if not stat_data or "SG÷" not in stat_data:
                            print(f"      🗑 Пусто -> ЧС", flush=True)
                            BLACKLIST.add(league)
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
                            WHITELIST.add(league)
                            save_list(WHITELIST_FILE, WHITELIST)
                        else:
                            print(f"      🗑 Нет бросков -> ЧС", flush=True)
                            BLACKLIST.add(league)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            
                    except Exception as e:
                        print(f"      ⚠️ Ошибка проверки API: {e}", flush=True)
                        
                    await asyncio.sleep(0.3) 

            except Exception as e:
                print(f"🚨 КРИТИЧЕСКАЯ ОШИБКА НА ДНЕ {day}: {e}", flush=True)
                traceback.print_exc()
                # Пересоздаем страницу на случай полного зависания вкладки
                await page.close()
                page = await context.new_page()

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
            print("⚠️ Белый список пуст.", flush=True)

        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлено вручную.")
    except Exception as e:
        print(f"ФАТАЛЬНЫЙ КРАШ: {e}")
