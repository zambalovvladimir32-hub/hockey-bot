def parse(data):
    matches = []
    blocks = data.split('~AA÷')
    
    # Собираем все найденные статусы для отладки
    all_statuses = set()
    
    for block in blocks[1:]:
        # Вытаскиваем все возможные маркеры периода/статуса
        tags = {}
        for t in ['AB', 'AC', 'JS', 'TT', 'NS']:
            if f'{t}÷' in block:
                val = block.split(f'{t}÷')[1].split('¬')[0]
                tags[t] = val
                all_statuses.add(f"{t}:{val}")

        # УСЛОВИЕ: Ищем 2-й период
        # В хоккее это обычно JS÷2 или TT÷2, иногда при AB÷3 (Live)
        is_live = tags.get('AB') == '3'
        is_second_period = tags.get('JS') == '2' or tags.get('TT') == '2'

        if is_second_period:
            try:
                home = block.split('AE÷')[1].split('¬')[0]
                away = block.split('AF÷')[1].split('¬')[0]
                # Счет (если есть)
                s_h = block.split('AG÷')[1].split('¬')[0] if 'AG÷' in block else '0'
                s_a = block.split('AH÷')[1].split('¬')[0] if 'AH÷' in block else '0'
                
                matches.append(f"🏒 **{home} {s_h}:{s_a} {away}**\n⏱ Идет 2-й период")
            except:
                continue
    
    if not matches:
        # Если пусто, пишем в лог, какие вообще статусы есть в данных
        logger.info(f"🧪 В данных найдены статусы: {sorted(list(all_statuses))}")
    
    return matches
