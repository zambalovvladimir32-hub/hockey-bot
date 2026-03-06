# 2. БЕСКОНЕЧНЫЙ ЦИКЛ API
        while True:
            try:
                print("\n📡 Обновляю базу...", flush=True)
                response = await context.request.get(EXACT_FEED_URL, headers=API_HEADERS)
                text = await response.text()
                
                if text == "0" or not text:
                    print("⚠️ Токен протух. Обновляю страницу...", flush=True)
                    EXACT_FEED_URL = None
                    await page.reload(timeout=30000)
                    await asyncio.sleep(5)
                    continue

                matches = text.split("~AA÷")
                
                # Считаем ТОЛЬКО реальный лайв (периоды и перерывы)
                # 2 - идет игра, 36 - перерыв P1, 37 - перерыв P2, 38 - перерыв перед ОТ
                live_statuses = [2, 36, 37, 38] 
                live_count = 0
                for m in matches[1:]:
                    ac_match = re.search(r"¬AC÷(\d+)¬", m)
                    if ac_match and int(ac_match.group(1)) in live_statuses:
                        live_count += 1
                            
                print(f"📊 Реального хоккея в лайве: {live_count}", flush=True)

                for match_data in matches[1:]:
                    try:
                        m_id = match_data.split("¬")[0]
                        
                        # ЖЕСТКИЙ ФИЛЬТР: Нас интересует СТРОГО статус 36 (Перерыв после 1-го периода)
                        if "¬AC÷36¬" not in match_data: continue 
                        if m_id in TRACKED_MATCHES: continue

                        home_match = re.search(r"AE÷([^¬]+)", match_data)
                        away_match = re.search(r"AF÷([^¬]+)", match_data)
                        home = home_match.group(1) if home_match else "Home"
                        away = away_match.group(1) if away_match else "Away"

                        sc_h_match = re.search(r"AG÷(\d+)", match_data)
                        sc_a_match = re.search(r"AH÷(\d+)", match_data)
                        sc_h = int(sc_h_match.group(1)) if sc_h_match else 0
                        sc_a = int(sc_a_match.group(1)) if sc_a_match else 0

                        # Фильтр на тотал меньше 1.5
                        if (sc_h + sc_a) > 1: continue

                        print(f"   🎯 ПЕРЕРЫВ P1: {home} - {away} ({sc_h}:{sc_a}). Проверяю статку...", flush=True)

                        # Запрос статистики
                        stat_url = f"{API_DOMAIN}/2/x/feed/df_st_1_{m_id}"
                        stat_response = await context.request.get(stat_url, headers=API_HEADERS)
                        stat_data = await stat_response.text()

                        if stat_data and "SG÷" in stat_data:
                            sh = re.search(r"SG÷(?:Shots on Goal|Броски в створ)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            wh = re.search(r"SG÷(?:Penalties|Удаления)¬SH÷(\d+)¬SI÷(\d+)", stat_data)
                            pim = re.search(r"SG÷(?:PIM|Штрафное время)¬SH÷(\d+)¬SI÷(\d+)", stat_data)

                            if sh:
                                t_sh = int(sh.group(1)) + int(sh.group(2))
                                t_wh = int(wh.group(1)) + int(wh.group(2)) if wh else 0
                                t_pim = int(pim.group(1)) + int(pim.group(2)) if pim else 0

                                print(f"      📈 СТАТА: Бр={t_sh}, Удал={t_wh}, Штраф={t_pim}", flush=True)

                                if t_sh >= 13 and t_pim >= 2 and t_wh >= 1:
                                    msg = (f"🚨 <b>СИГНАЛ P1 (NINJA API)</b>\n"
                                           f"🤝 {home} — {away} ({sc_h}:{sc_a})\n"
                                           f"🎯 Броски: {t_sh} | ❌ Удаления: {t_wh} | ⏳ Штраф: {t_pim} мин\n"
                                           f"🔗 <a href='https://www.flashscore.com/match/{m_id}/#/match-summary/match-statistics/0'>Открыть матч</a>")
                                    await send_tg(msg)
                                    TRACKED_MATCHES.add(m_id)
                                    print("      ✅ СИГНАЛ В КАНАЛЕ!", flush=True)
                                else:
                                    print("      ⚠️ Стата не подходит.", flush=True)
                            else:
                                print("      🧐 Нет бросков в API для этого матча.", flush=True)
                        else:
                            print("      ❌ Статистики еще нет в базе.", flush=True)

                    except Exception as e:
                        print(f"   ⚠️ Ошибка матча: {e}", flush=True)

                print("💤 Жду 60 секунд...", flush=True)
                await asyncio.sleep(60)
            except Exception as e:
                print(f"⚠️ Ошибка цикла: {e}", flush=True)
                await asyncio.sleep(20)
