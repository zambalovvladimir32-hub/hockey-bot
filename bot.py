async def get_flash_stats(session, mid):
    try:
        # Эмуляция захода на страницу, как делает Livescore
        await session.get(f"https://www.flashscore.ru/match/{mid}/", impersonate="chrome110")
        
        url = f"https://www.flashscore.ru/x/feed/df_st_1_{mid}"
        headers = {
            "x-fsign": "SW9D1eZo", # Тот самый ключ, который открывает Livescore
            "referer": f"https://www.flashscore.ru/match/{mid}/"
        }
        r = await session.get(url, headers=headers, impersonate="chrome110")
        
        content = r.text
        # ВОТ ЭТО ПОКАЖЕТ ТЕБЕ, ЧТО МЫ ВНУТРИ Livescore
        print(f"🛠 [DEBUG] Данные Livescore по матчу {mid}: {content[:150]}...") 
        
        sh, pn = 0, 0
        parts = content.split('~')
        for p in parts:
            if any(x in p for x in ['Броски в створ', 'SOG', '158']):
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: sh = int(vals[-2]) + int(vals[-1])
            if any(x in p for x in ['Штрафное время', 'PEN', '2']):
                vals = re.findall(r'(\d+)', p)
                if len(vals) >= 2: pn = int(vals[-2]) + int(vals[-1])
        
        return sh, pn
    except Exception as e:
        print(f"⚠️ Ошибка связи с Livescore: {e}")
        return 0, 0
