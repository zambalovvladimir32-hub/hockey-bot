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
            
            # Проходим по всем периодам, ищем 'ALL'
            for period_data in data.get('statistics', []):
                if period_data.get('period') == 'ALL':
                    for group in period_data.get('groups', []):
                        for item in group.get('statisticsItems', []):
                            key = item.get('name', '').lower()
                            
                            # 🏒 Ищем БРОСКИ (проверяем все варианты названий в API)
                            if any(x in key for x in ['shots on goal', 'shots on target', 'удары в створ', 'броски в створ']):
                                h_val = str(item.get('home', '0')).replace('%','')
                                a_val = str(item.get('away', '0')).replace('%','')
                                sh = int(h_val) + int(a_val)
                            
                            # ⏳ Ищем ШТРАФ
                            if any(x in key for x in ['penalty minutes', 'штраф', 'penaltyminutes']):
                                h_pn = str(item.get('home', '0'))
                                a_pn = str(item.get('away', '0'))
                                pn = int(h_pn) + int(a_pn)
            
            # Если броски всё еще 0, ищем "Total shots" (иногда в КХЛ они так значатся)
            if sh == 0:
                for period_data in data.get('statistics', []):
                    if period_data.get('period') == 'ALL':
                        for group in period_data.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'total shots' in item.get('name', '').lower():
                                    sh = int(item.get('home', 0)) + int(item.get('away', 0))
                                    
            return sh, pn
    except Exception as e:
        log(f"⚠ Ошибка парсинга статы: {e}")
        return 0, 0
