def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    # Собираем все найденные статусы для диагностики
    found_statuses = set()
    
    for block in blocks[1:]:
        # Собираем метки статусов, чтобы понять логику Flashscore
        for tag in ['TT÷', 'JS÷', 'NS÷', 'AB÷']:
            if tag in block:
                val = block.split(tag)[1].split('¬')[0]
                found_statuses.add(f"{tag}{val}")

        # Проверяем все возможные варианты 2-го периода
        # В хоккее часто используется JS÷2 или TT÷2 при AB÷3 (Live)
        is_live = 'AB÷3' in block
        is_second_period = any(x in block for x in ['TT÷2', 'JS÷2', 'NS÷2'])
        
        if is_second_period and is_live:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                # Счет
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период")
            except:
                continue
    
    if not matches:
        # Эта строчка в логах Railway скажет нам правду
        logger.info(f"🧪 Диагностика статусов: {list(found_statuses)}")
    
    return matches
