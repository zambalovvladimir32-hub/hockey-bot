async def get_stats_with_curl(session, mid):
    try:
        # ШАГ 1: "Открываем" матч, чтобы сервер разрешил забрать статику
        main_url = f"https://www.flashscore.ru/match/{mid}/#/match-summary/match-statistics/0"
        await session.get(main_url, impersonate="chrome110", timeout=10)
        
        # ШАГ 2: Теперь запрашиваем сами цифры
        url = f"https://www.flashscore.ru/x/feed/df_st_1_{mid}"
        headers = {
            "x-fsign": "SW9D1eZo",
            "referer": main_url, # Обязательно ссылаемся на страницу матча
            "x-requested-with": "XMLHttpRequest"
        }
        
        r = await session.get(url, headers=headers, impersonate="chrome110", timeout=10)
        content = r.text
        
        # Если в ответе нет '158' (код бросков), значит данных еще нет на сайте
        if '158' not in content and '2' not in content:
            return 0, 0
            
        sh, pn = 0, 0
        for s in content.split('~'):
            if '158' in s: # Броски
                res = re.findall(r'(\d+)', s)
                if len(res) >= 2: sh = int(res[-2]) + int(res[-1])
            if '2' in s and 'PN' in s: # Штрафы
                res = re.findall(r'(\d+)', s)
                if len(res) >= 2: pn = int(res[-2]) + int(res[-1])
        return sh, pn
    except:
        return 0, 0
