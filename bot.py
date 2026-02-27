def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    # Собираем все найденные статусы для диагностики
    found_statuses = set()
    
    for block in blocks[1:]:
        # Собираем метки статусов (TT, NS, JS), чтобы понять код Flashscore
        for tag in ['TT÷', 'NS÷', 'JS÷']:
            if tag in block:
                status_val = block.split(tag)[1].split('¬')[0]
                found_statuses.add(f"{tag}{status_val}")

        # Проверяем все возможные варианты метки 2-го периода
        # В хоккее часто используется JS÷2 или комбинация NS÷2 + TT÷2
        is_second_period = any(x in block for x in ['TT÷2', 'JS÷2'])
        
        if is_second_period:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                # Пробуем достать текущий счет
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период")
            except:
                continue
    
    if not matches:
        logger.info(f"🧪 Диагностика: найденные метки статусов в данных: {list(found_statuses)}")
    
    return matches
