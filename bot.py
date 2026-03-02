async def get_stats(session, mid):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/"
    }
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, headers=headers, timeout=10) as r:
            if r.status != 200: return 0, 0
            data = await r.json()
            periods = data.get('statistics', [])
            if not periods: return 0, 0

            # 1. Берем 'ALL' или первый доступный период
            target = next((p for p in periods if p.get('period') == 'ALL'), periods[0])
            
            sh, pn = 0, 0
            for group in target.get('groups', []):
                for item in group.get('statisticsItems', []):
                    # Проверяем и ИМЯ, и КЛЮЧ (key в API всегда на английском и стабильнее)
                    name = str(item.get('name', '')).lower()
                    key = str(item.get('key', '')).lower()
                    
                    def get_val(side):
                        # Пробуем все варианты ключей SofaScore (Value, Total, или просто имя стороны)
                        for k in [f'{side}Value', f'{side}Total', side]:
                            v = item.get(k)
                            if v is not None:
                                try:
                                    # Чистим: отсекаем скобки (%), дроби (11/20) и лишние знаки
                                    return int(str(v).split('(')[0].split('/')[0].replace('%','').strip())
                                except: continue
                        return 0

                    # 🏒 БРОСКИ В СТВОР
                    # Проверяем по системному ключу или по набору слов
                    is_shot = 'shotsongoal' in key or 'shotsontarget' in key or \
                              (any(x in name for x in ['створ', 'target', 'goal', 'броски']) and 'block' not in name)
                    
                    if is_shot and sh == 0: # Берем первое найденное совпадение
                        sh = get_val('home') + get_val('away')
                    
                    # ⏳ ШТРАФНОЕ ВРЕМЯ
                    is_penalty = 'penaltyminutes' in key or any(x in name for x in ['penalty', 'штраф', 'мин'])
                    if is_penalty and pn == 0:
                        pn = get_val('home') + get_val('away')
            
            return sh, pn
    except: return 0, 0
