import asyncio, re, os, sys
from curl_cffi.requests import AsyncSession

def log(msg):
    print(msg, flush=True)

# Упростили список для максимального охвата
WHITE_LIST = ['КХЛ', 'ВХЛ', 'МХЛ', 'НХЛ', 'АХЛ', 'ICE', 'Tipsport', 'Экстралига', 'Maxa', 'Элитсериен', 'ЖХЛ', 'НМХЛ']

async def get_stats_with_curl(session, mid):
    try:
        url = f"https://www.flashscore.ru/x/feed/df_st_1_{mid}"
        headers = {"x-fsign": "SW9D1eZo", "referer": "https://www.flashscore.ru/"}
        r = await session.get(url, headers=headers, impersonate="chrome110", timeout=15)
        
        sh, pn = 0, 0
        # Ищем коды статы: 158 - броски, 2 - штраф
        for s in r.text.split('~'):
            if '158' in s:
                res = re.findall(r'(\d+)', s)
                if len(res) >= 2: sh = int(res[-2]) + int(res[-1])
            if '2' in s and 'PN' in s:
                res = re.findall(r'(\d+)', s)
                if len(res) >= 2: pn = int(res[-2]) + int(res[-1])
        return sh, pn
    except: return 0, 0

async def main():
    log("--- 🦾 ЗАПУСК v118.0 (УЛУЧШЕННЫЙ ПОИСК) ---")
    async with AsyncSession() as session:
        while True:
            try:
                # Берем все матчи (код f_4_0_3 - это хоккейный лайв)
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                
                blocks = r.text.split('~')
                found = False
                cur_league = ""

                for b in blocks:
                    if b.startswith('ZA÷'): cur_league = b.split('ZA÷')[1].split('¬')[0]
                    if b.startswith('AA÷'):
                        mid = b.split('AA÷')[1].split('¬')[0]
                        
                        # Проверка: есть ли хоть одно слово из нашего списка в названии лиги
                        if any(word.upper() in cur_league.upper() for word in WHITE_LIST):
                            found = True
                            h_t = b.split('AE÷')[1].split('¬')[0] if 'AE÷' in b else "Home"
                            a_t = b.split('AF÷')[1].split('¬')[0] if 'AF÷' in b else "Away"
                            
                            # Тянем статистику немедленно для теста
                            sh, pn = await get_stats_with_curl(session, mid)
                            log(f"📊 [DATA] {h_t} - {a_t} | Броски: {sh} | Штраф: {pn} | Лига: {cur_league}")

                if not found:
                    log("📭 Совпадений по лигам всё еще нет. Проверь список.")
                
            except Exception as e: log(f"🛑 Ошибка: {e}")
            await asyncio.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())
