async def main():
    print("--- 🧠 БОТ-АРХИВАРИУС: ГИБРИДНЫЙ ПАРСЕР (НЕУБИВАЕМЫЙ DOM) ---", flush=True)
    global API_DOMAIN, API_HEADERS, BLACKLIST, WHITELIST
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        # Ловим токен ОДИН раз за всю сессию
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
                    print("   🔑 API-Токен успешно украден!", flush=True)

        page.on("request", handle_request)

        for day in range(8):
            day_label = "СЕГОДНЯ" if day == 0 else f"{day} ДНЕЙ НАЗАД"
            print(f"\n⏳ ПРЫЖОК ВО ВРЕМЕНИ: {day_label} (d=-{day})", flush=True)
            
            await page.goto(f"https://www.flashscore.com/hockey/?d=-{day}", timeout=60000)
            
            # Ждем матчи
            try:
                await page.wait_for_selector('.event__match', timeout=20000)
                await asyncio.sleep(3) # Даем время на рендер заголовков
            except:
                print(f"❌ На странице нет матчей для дня -{day}. Идем дальше...", flush=True)
                continue

            if not API_HEADERS:
                print("⚠️ Токен еще не пойман, ждем...", flush=True)
                await asyncio.sleep(3)

            # --- НЕУБИВАЕМЫЙ JS-ЭКСТРАКТОР ---
            leagues_dict = await page.evaluate('''() => {
                const data = {};
                let currentLeague = "Unknown League";
                const elements = document.querySelectorAll('.event__header, .event__match');
                
                for (const el of elements) {
                    if (el.classList.contains('event__header')) {
                        // Ищем классы, если их нет - берем весь текст заголовка
                        let typeNode = el.querySelector('.event__title--type');
                        let nameNode = el.querySelector('.event__title--name');
                        
                        if (typeNode && nameNode) {
                            currentLeague = typeNode.innerText.trim() + ": " + nameNode.innerText.trim();
                        } else {
                            // Лом: берем текст, убираем переносы строк, отрезаем лишнее
                            currentLeague = el.innerText.replace(/\\n/g, ' ').replace(/\s+/g, ' ').trim();
                        }
                    } else if (el.classList.contains('event__match')) {
                        if (!data[currentLeague]) {
                            let matchId = el.id; // Обычно id="g_4_A1B2C3D4"
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

            print(f"✅ Найдено лиг на странице: {len(leagues_dict)}. Проверяю статистику...", flush=True)

            for league, m_id in leagues_dict.items():
                if league in BLACKLIST or league in WHITELIST:
                    continue

                print(f"   🔍 Изучаю новую лигу: 🏆 {league}", flush=True)

                if not API_DOMAIN or not API_HEADERS:
                    print("      ⚠️ Нет API ключа!", flush=True)
                    continue

                stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                try:
                    stat_response = await context.request.get(stat_url, headers=API_HEADERS)
                    stat_data = await stat_response.text()

                    if not stat_data or "SG÷" not in stat_data:
                        print(f"      🗑 Пусто. '{league}' -> ЧЕРНЫЙ СПИСОК", flush=True)
                        BLACKLIST.add(league)
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
                        print(f"      ✅ Броски есть! '{league}' -> БЕЛЫЙ СПИСОК", flush=True)
                        WHITELIST.add(league)
                        save_list(WHITELIST_FILE, WHITELIST)
                    else:
                        print(f"      🗑 Бросков в P1 нет. '{league}' -> ЧЕРНЫЙ СПИСОК", flush=True)
                        BLACKLIST.add(league)
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
