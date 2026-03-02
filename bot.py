async def get_stats_final(session, mid):
    # Пробуем альтернативный фид, который сложнее заблокировать
    try:
        # Попытка №1: Прямой фид статы с обновленным реферером
        url = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
        headers = {
            "x-fsign": "SW9D1eZo", # Попробуем этот, если не даст - сменим
            "referer": f"https://www.flashscore.ru/match/{mid}/",
            "x-requested-with": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"
        }
        
        r = await session.get(url, headers=headers, impersonate="chrome120", timeout=10)
        
        # Если пришел пустой ответ или без кода бросков (158)
        if '158' not in r.text:
            # Попытка №2: Запрос через "мобильный" канал (иногда там нет защиты)
            mob_url = f"https://m.flashscore.ru/x/feed/df_st_0_{mid}"
            r = await session.get(mob_url, headers=headers, impersonate="chrome120", timeout=10)

        content = r.text
        sh, pn = 0, 0
        for s in content.split('~'):
            if '158' in s: # Броски
                res = re.findall(r'(\d+)', s)
                if len(res) >= 2: sh = int(res[-2]) + int(res[-1])
            if '2' in s and 'PN' in s: # Штраф
                res = re.findall(r'(\d+)', s)
                if len(res) >= 2: pn = int(res[-2]) + int(res[-1])
        return sh, pn
    except: return 0, 0
