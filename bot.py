import asyncio, re, os, sys
from curl_cffi.requests import AsyncSession

def log(msg):
    print(msg, flush=True)

async def get_stats_final(session, mid):
    # Пытаемся забрать ОБЩУЮ статистику (она надежнее всего)
    try:
        url = f"https://www.flashscore.ru/x/feed/df_st_0_{mid}"
        headers = {"x-fsign": "SW9D1eZo", "referer": f"https://www.flashscore.ru/match/{mid}/"}
        
        r = await session.get(url, headers=headers, impersonate="chrome110", timeout=10)
        content = r.text
        
        # Если в ответе пусто - значит Livescore реально закрылся
        if '158' not in content: return 0, 0
        
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

async def main():
    log("--- ⚡️ v122.0: СТАБИЛЬНЫЙ ПОТОК (АНТИ-ЛОМ) ---")
    async with AsyncSession() as session:
        while True:
            try:
                # Берем фид хоккея
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                
                # Ищем матчи НХЛ/АХЛ (они сейчас в лайве)
                matches = re.findall(r'AA÷(.*?)(?=¬)', r.text)
                
                for mid in matches[:15]: # Проверяем первые 15 матчей
                    sh, pn = await get_stats_final(session, mid)
                    # Выводим в лог только если есть хоть какая-то статистика
                    if sh > 0 or pn > 0:
                        log(f"✅ ДАННЫЕ ЕСТЬ! Матч {mid} | Броски: {sh} | Штраф: {pn}")
                    else:
                        log(f"🥚 Матч {mid} | Статы пока нет (0)")
                
                log("--- Сон 40 сек ---")
            except Exception as e: log(f"🛑 Ошибка: {e}")
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
