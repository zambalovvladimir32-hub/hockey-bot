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
            
            # В SofaScore статистика лежит в списке 'statistics'
            for period_data in data.get('statistics', []):
                # Нас интересует только статистика за весь матч (ALL)
                if period_data.get('period') == 'ALL':
                    for group in period_data.get('groups', []):
                        for item in group.get('statisticsItems', []):
                            name = item.get('name', '').lower()
                            
                            # Универсальная функция вытягивания чисел
                            def extract(obj, side):
                                # Проверяем и 'homeValue', и просто 'home'
                                val = obj.get(f'{side}Value') or obj.get(side) or '0'
                                # Убираем проценты и лишние символы
                                return int(str(val).split('(')[0].replace('%', '').strip())

                            # 🏒 Ищем БРОСКИ (все возможные варианты названия в JSON)
                            if any(x in name for x in ['shots on goal', 'shots on target', 'удары в створ', 'shotsongoal']):
                                sh = extract(item, 'home') + extract(item, 'away')
                            
                            # ⏳ Ищем ШТРАФ
                            if any(x in name for x in ['penalty minutes', 'штраф', 'penaltyminutes']):
                                pn = extract(item, 'home') + extract(item, 'away')
            
            # Резервный поиск, если броски все еще 0
            if sh == 0:
                for period_data in data.get('statistics', []):
                    if period_data.get('period') == 'ALL':
                        for group in period_data.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'total shots' in item.get('name', '').lower():
                                    sh = extract(item, 'home') + extract(item, 'away')
                                    
            return sh, pn
    except Exception as e:
        log(f"⚠ Ошибка парсинга: {e}")
        return 0, 0
