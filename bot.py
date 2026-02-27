def parse_games(raw_data):
    if not raw_data: return []
    matches = []
    blocks = raw_data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Вытягиваем данные
            res = dict(re.findall(r'(\w+)÷([^¬]+)', block))
            
            home = res.get('AE', '???')
            away = res.get('AF', '???')
            s1 = res.get('AG', '0')
            s2 = res.get('AH', '0')
            # Статус матча (во Flashscore это часто поле ST или ER)
            status = res.get('ER', '').upper() + res.get('ST', '').upper()
            
            # Расширенный фильтр на 2-й период:
            # Ищем "2", "P2", "S2", "2ND" или "ВТОРОЙ"
            is_second_period = any(x in status for x in ["2", "P2", "S2", "2ND", "ВТОР"])
            
            # Также ловим наш любимый Норильск
            is_norilsk = "норильск" in home.lower() or "норильск" in away.lower()

            if is_second_period or is_norilsk:
                matches.append(f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Статус: {status if status else '2-й период'}")
                logger.info(f"🎯 Нашел матч: {home} - {away} (Статус: {status})")
        except:
            continue
    return matches
