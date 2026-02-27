def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    # Собираем все найденные статусы для диагностики, если матчей нет
    found_statuses = set()
    
    for block in blocks[1:]:
        # Вытягиваем все важные теги
        tags = {}
        for t in ['AB', 'JS', 'TT', 'NS']:
            if f'{t}÷' in block:
                tags[t] = block.split(f'{t}÷')[1].split('¬')[0]
        
        if tags:
            found_statuses.add(f"AB:{tags.get('AB')} JS:{tags.get('JS')} TT:{tags.get('TT')}")

        # Условие для 2-го периода в хоккее: 
        # Обычно это JS÷2 или TT÷2 при AB÷3 (матч в эфире)
        is_live = tags.get('AB') == '3'
        is_2nd_period = tags.get('JS') == '2' or tags.get('TT') == '2'
        
        if is_2nd_period and is_live:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                # Текущий счет
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период")
            except:
                continue
    
    if not matches:
        logger.info(f"🔎 Во 2-м периоде пусто. Статусы в фиде: {list(found_statuses)[:5]}...")
        
    return matches
