def parse_games(raw_data):
    if not raw_data: return []
    matches = []
    blocks = raw_data.split('~AA÷')
    
    for block in blocks[1:]:
        try:
            # Вытягиваем данные из блока
            res = dict(re.findall(r'(\w+)÷([^¬]+)', block))
            
            home = res.get('AE', '???')
            away = res.get('AF', '???')
            s1 = res.get('AG', '0')
            s2 = res.get('AH', '0')
            
            # Проверяем все возможные поля статуса: ER, ST, EP
            # Склеиваем их в одну строку для надежности
            raw_status = (res.get('ER', '') + res.get('ST', '') + res.get('EP', '')).upper()
            
            # ЛОГ ДЛЯ ТЕБЯ: Бот будет писать в логи Railway реальный статус каждого матча
            if home != '???':
                logger.info(f"Матч: {home} | Статус в базе: '{raw_status}'")

            # Максимально широкий фильтр (Латиница + Кириллица + Цифры)
            trigger_words = ["2", "P2", "П2", "2ND", "ВТОР", "ВТО", "S2"]
            is_second_period = any(x in raw_status for x in trigger_words)
            
            is_norilsk = "норильск" in home.lower() or "норильск" in away.lower()

            if is_second_period or is_norilsk:
                msg = f"🏒 **{home} {s1}:{s2} {away}**\n⏱ Статус: {raw_status if raw_status else '2-й период'}"
                matches.append(msg)
                logger.info(f"✅ ЕСТЬ КОНТАКТ: {home} подходит!")
        except Exception as e:
            continue
    return matches
