async def get_sofascore_stats(session, event_id):
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as r:
            if r.status != 200: return 0, 0
            data = await r.json()
            sh, pn = 0, 0
            
            for period_data in data.get('statistics', []):
                # Нам нужна статистика за весь матч ('ALL')
                if period_data.get('period') == 'ALL':
                    for group in period_data.get('groups', []):
                        for item in group.get('statisticsItems', []):
                            key = item.get('name', '').lower()
                            
                            # Функция для безопасного извлечения числа
                            def get_val(item_obj, side):
                                # Пробуем сначала 'homeValue', потом 'home'
                                res = item_obj.get(f'{side}Value') or item_obj.get(side) or '0'
                                return int(str(res).replace('%', ''))

                            # 🏒 Ищем БРОСКИ (все варианты названий)
                            if any(x in key for x in ['shots on goal', 'shots on target', 'удары в створ', 'броски в створ']):
                                sh = get_val(item, 'home') + get_val(item, 'away')
                            
                            # ⏳ Ищем ШТРАФ
                            if any(x in key for x in ['penalty minutes', 'штраф', 'penaltyminutes']):
                                pn = get_val(item, 'home') + get_val(item, 'away')
            
            # Если броски всё еще 0, берем "Total shots" (иногда в КХЛ так)
            if sh == 0:
                for period_data in data.get('statistics', []):
                    if period_data.get('period') == 'ALL':
                        for group in period_data.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'total shots' in item.get('name', '').lower():
                                    sh = get_val(item, 'home') + get_val(item, 'away')
                                    
            return sh, pn
    except Exception as e:
        log(f"⚠ Ошибка парсинга: {e}")
        return 0, 0
