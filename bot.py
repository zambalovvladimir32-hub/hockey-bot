def parse_logical_second(data):
    matches = []
    sections = data.split('~ZA÷')
    
    for section in sections[1:]:
        league = section.split('¬')[0]
        blocks = section.split('~AA÷')
        
        for block in blocks[1:]:
            try:
                if 'AB÷' not in block: continue
                
                # 1. Сбор всех статусов
                ab = block.split('AB÷')[1].split('¬')[0]
                ac = block.split('AC÷')[1].split('¬')[0] if 'AC÷' in block else ""
                cr = block.split('CR÷')[1].split('¬')[0] if 'CR÷' in block else ""
                tt = block.split('TT÷')[1].split('¬')[0] if 'TT÷' in block else ""

                # --- ТРОЙНОЙ ФИЛЬТР ОТ 3-ГО ПЕРИОДА ---
                
                # А. Проверка по кодам (основная)
                # 3 = 3й период, 46 = перерыв перед 3-м, 6 = конец
                if ac in ['3', '46', '6', '4', '5'] or cr == '3':
                    continue

                # Б. Проверка по счету (самая надежная)
                # XC÷ - счет 3-го периода. Если этот тег есть в блоке, 3-й период НАЧАЛСЯ.
                if 'XC÷' in block:
                    continue

                # В. Проверка по тексту времени
                time_label = tt.upper()
                if any(x in time_label for x in ["P3", "3-Й", "3RD", "3."]):
                    continue

                # 2. Только LIVE (2=идет матч, 3=перерыв)
                if ab not in ['2', '3']: continue

                # 3. Идентификация Перерыва (1-2) или 2-го периода
                # AC:45 - железный код перерыва после 1-го периода
                is_break = (ac == '45' or "ПЕРЕРЫВ" in time_label or "PAUSE" in time_label)
                
                # Если это не перерыв и не 1-й период (ac:1), значит это 2-й
                if ac == '1' or cr == '1' or "1-Й" in time_label:
                    continue

                # Собираем данные
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else "0"
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else "0"
                
                # Берем счет 1-го периода для контроля
                s1 = block.split('XA÷')[1].split('¬')[0] if 'XA÷' in block else "0:0"
                
                status_text = "☕️ ПЕРЕРЫВ (1-2)" if is_break else "⏱ 2-Й ПЕРИОД"
                if tt and tt != "?": status_text += f" [{tt}]"

                matches.append({
                    'id': f"{home}{away}{s_h}{s_a}", 
                    'text': f"🏒 **{home} {s_h}:{s_a} {away}**\n🏆 {league}\n{status_text}\n(1-й пер: {s1})"
                })
            except:
                continue
    return matches
