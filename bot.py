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
    print("--- 🧠 БОТ-АРХИВАРИУС V5: ИДЕАЛЬНЫЙ РЕНТГЕН ---", flush=True)
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
                    print("   🔑 API-Токен захвачен! Перехожу на рентген.", flush=True)

        page.on("request", token_handler)

        for day in range(8):
            try:
                day_label = "СЕГОДНЯ" if day == 0 else f"{day} ДНЕЙ НАЗАД"
                print(f"\n⏳ ПРЫЖОК ВО ВРЕМЕНИ: {day_label} (d=-{day})", flush=True)
                
                captured_text = None
                
                async def response_handler(response):
                    nonlocal captured_text
                    if captured_text: return
                    if "flashscore.ninja" in response.url and ("feed/f_4" in response.url or "feed/r_4" in response.url):
                        if day > 0 and "f_4_0" in response.url:
                            return 
                        try:
                            text = await response.text()
                            if "ZA÷" in text and "AA÷" in text:
                                captured_text = text
                        except: pass

                page.on("response", response_handler)
                await page.goto(f"https://www.flashscore.com/hockey/?d=-{day}", timeout=40000)
                
                for _ in range(15):
                    if captured_text: break
                    await asyncio.sleep(1)
                
                page.remove_listener("response", response_handler)

                if not captured_text:
                    print(f"❌ Не удалось поймать сырую базу для дня -{day}.", flush=True)
                    continue

                # --- 1. ВЫТАСКИВАЕМ ПО 1 МАТЧУ ИЗ КАЖДОЙ ЛИГИ (БЕЗ ФИЛЬТРОВ) ---
                match_ids_to_check = []
                blocks = captured_text.split("~")
                need_match = False
                
                for block in blocks:
                    if block.startswith("ZA÷"):
                        need_match = True  # Увидели новую лигу, включаем "пылесос"
                    elif block.startswith("AA÷") and need_match:
                        m_id = block.split("¬")[0].replace("AA÷", "")
                        if len(m_id) == 8:
                            match_ids_to_check.append(m_id)
                            need_match = False # Матч найден, выключаем до следующей лиги

                print(f"✅ Найдено турниров в базе: {len(match_ids_to_check)}. Сканирую имена...", flush=True)

                if not API_DOMAIN or not API_HEADERS:
                    print("⚠️ Нет API ключа, жду...", flush=True)
                    await asyncio.sleep(3)

                # --- 2. РЕНТГЕН КАЖДОГО МАТЧА ЧЕРЕЗ API ---
                for m_id in match_ids_to_check:
                    try:
                        # Узнаем НАСТОЯЩЕЕ имя лиги через сводку матча (SUI)
                        sui_url = f"{API_DOMAIN}/2/x/feed/df_sui_1_{m_id}"
                        sui_resp = await context.request.get(sui_url, headers=API_HEADERS)
                        sui_text = await sui_resp.text()
                        
                        league_match = re.search(r"ZA÷([^¬]+)", sui_text)
                        if not league_match:
                            continue
                            
                        league_name = league_match.group(1).strip()

                        if league_name in BLACKLIST or league_name in WHITELIST:
                            continue

                        print(f"   🔍 🏆 {league_name}", flush=True)

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
    asyncio.run(main())
