import asyncio
import os
import re
import json
import urllib.request
from playwright.async_api import async_playwright

# --- КОНФИГ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

BLACKLIST_FILE = "blacklist.json"
WHITELIST_FILE = "whitelist.json"

def load_list(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
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

async def main():
    print("--- 🧠 БОТ-АРХИВАРИУС: ТИТАНОВАЯ ВЕРСИЯ (7 ДНЕЙ) ---", flush=True)
    global BLACKLIST, WHITELIST
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        for day in range(8):
            captured = {"text": None, "domain": None, "headers": None}

            async def response_handler(response):
                if captured["text"]: return 
                
                if "flashscore.ninja" in response.url and ("feed/f_4" in response.url or "feed/r_4" in response.url):
                    # МАГИЯ ЗДЕСЬ: Игнорируем сегодняшнюю базу, если ищем прошлые дни
                    if day > 0 and "f_4_0" in response.url:
                        return 
                        
                    try:
                        text = await response.text()
                        if "AA÷" in text:
                            captured["text"] = text
                            req = response.request
                            match = re.search(r"(https://[a-zA-Z0-9.-]+\.flashscore\.ninja)", req.url)
                            if match: captured["domain"] = match.group(1)
                            
                            captured["headers"] = {
                                "x-fsign": req.headers.get("x-fsign", ""),
                                "X-Requested-With": "XMLHttpRequest",
                                "Referer": "https://www.flashscore.com/"
                            }
                            print(f"   🎯 Пойман правильный архив: {response.url.split('/')[-1]}", flush=True)
                    except:
                        pass

            page.on("response", response_handler)
            
            day_label = "СЕГОДНЯ" if day == 0 else f"{day} ДНЕЙ НАЗАД"
            print(f"\n⏳ ПРЫЖОК ВО ВРЕМЕНИ: {day_label} (d=-{day})", flush=True)
            
            await page.goto(f"https://www.flashscore.com/hockey/?d=-{day}", timeout=40000)
            
            for _ in range(20):
                if captured["text"]: break
                await asyncio.sleep(1)

            page.remove_listener("response", response_handler)

            if not captured["text"]:
                print(f"❌ Не удалось поймать архив для дня -{day}. Пропускаю...", flush=True)
                continue

            print(f"✅ База загружена! Начинаю сканирование...", flush=True)
            
            blocks = captured["text"].split("~")
            current_league = "Unknown League"
            
            for block in blocks:
                if block.startswith("ZA÷"):
                    league_match = re.search(r"ZA÷([^¬]+)", block)
                    if league_match:
                        current_league = league_match.group(1).strip()
                    continue
                    
                if block.startswith("AA÷"):
                    if not re.search(r"¬AC÷[389]¬", block): continue 

                    m_id = block.split("¬")[0].replace("AA÷", "")
                    
                    # --- РЕЗЕРВНЫЙ ПОИСК ЛИГИ ---
                    # Если база скрыла название лиги, делаем точечный запрос к матчу и узнаем его
                    if current_league == "Unknown League":
                        sui_url = f"{captured['domain']}/2/x/feed/df_sui_1_{m_id}"
                        try:
                            sui_resp = await context.request.get(sui_url, headers=captured["headers"])
                            sui_text = await sui_resp.text()
                            l_match = re.search(r"ZA÷([^¬]+)", sui_text)
                            if l_match:
                                current_league = l_match.group(1).strip()
                        except:
                            pass
                    
                    if current_league == "Unknown League":
                        continue # Если даже так не нашли - пропускаем от греха подальше
                    
                    # Теперь, когда лига точно известна, проверяем списки
                    if current_league in BLACKLIST or current_league in WHITELIST:
                        continue

                    print(f"   🔍 Изучаю новую лигу: 🏆 {current_league}", flush=True)

                    stat_url = f"{captured['domain']}/2/x/feed/df_st_1_{m_id}"
                    try:
                        stat_response = await context.request.get(stat_url, headers=captured["headers"])
                        stat_data = await stat_response.text()

                        if not stat_data or "SG÷" not in stat_data:
                            print(f"      🗑 Пусто. '{current_league}' -> ЧЕРНЫЙ СПИСОК", flush=True)
                            BLACKLIST.add(current_league)
                            save_list(BLACKLIST_FILE, BLACKLIST)
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

                        if sh:
                            print(f"      ✅ Броски есть! '{current_league}' -> БЕЛЫЙ СПИСОК", flush=True)
                            WHITELIST.add(current_league)
                            save_list(WHITELIST_FILE, WHITELIST)
                        else:
                            print(f"      🗑 Бросков в P1 нет. '{current_league}' -> ЧЕРНЫЙ СПИСОК", flush=True)
                            BLACKLIST.add(current_league)
                            save_list(BLACKLIST_FILE, BLACKLIST)
                            
                    except Exception as e:
                        print(f"      ⚠️ Ошибка проверки статы: {e}", flush=True)
                        
                    await asyncio.sleep(0.3) 

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
