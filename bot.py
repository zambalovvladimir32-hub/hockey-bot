import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

# ЭТИ ЛИГИ МЫ УЖЕ ЗНАЕМ - ИХ ПРОПУСКАЕМ
ALREADY_KNOWN = [
    'АВСТРИЯ: Лига ICE', 'РОССИЯ: OLIMPBET - МХЛ', 'РОССИЯ: ЖХЛ', 
    'СЛОВАКИЯ: Tipsport liga', 'ЧЕХИЯ: Maxa liga', 'ЧЕХИЯ: Экстралига', 
    'ШВЕЦИЯ: Элитсериен'
]

async def second_pass_scanner(days_range=7):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    new_leagues = set()
    tested_in_this_run = set()

    async with AsyncSession() as session:
        print(f"🚀 ЗАПУСК ВТОРОГО ПРОХОДА (Исключаем {len(ALREADY_KNOWN)} лиг)")
        
        for d in range(1, days_range + 1):
            date_offset = f"-{d}"
            print(f"📅 Сканирую архив за {d} дн. назад...")
            
            f_url = f"https://www.flashscore.ru/x/feed/f_4_{date_offset}_3_ru-ru_1"
            try:
                r = await session.get(f_url, headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                blocks = r.text.split('~')
                cur_l = "Unknown"
                
                for block in blocks:
                    if block.startswith('ZA÷'): 
                        cur_l = block.split('ZA÷')[1].split('¬')[0]
                    
                    # ПРОПУСКАЕМ ИЗВЕСТНЫЕ И УЖЕ ПРОВЕРЕННЫЕ
                    if cur_l in ALREADY_KNOWN or cur_l in new_leagues or cur_l in tested_in_this_run:
                        continue

                    if block.startswith('AA÷'):
                        h_team = block.split('AE÷')[1].split('¬')[0]
                        a_team = block.split('AF÷')[1].split('¬')[0]
                        tested_in_this_run.add(cur_l)
                        
                        search_q = f"{h_team} {a_team}".split('(')[0].strip()
                        print(f"🔎 Новая лига? Проверяю: {cur_l}")
                        
                        try:
                            s_url = f"https://www.sofascore.com/api/v1/search/all?q={search_q}"
                            s_req = await session.get(s_url, headers=headers, impersonate="chrome110")
                            await asyncio.sleep(2) # Пауза для стабильности
                            
                            results = s_req.json().get('results', [])
                            eid = next((res['entity']['id'] for res in results if res.get('type') == 'event'), None)
                            
                            if not eid: continue

                            st_req = await session.get(f"https://www.sofascore.com/api/v1/event/{eid}/statistics", headers=headers)
                            if st_req.status_code == 200:
                                data = st_req.json()
                                # Ищем любые признаки бросков и штрафов в любой вкладке
                                all_names = []
                                for p in data.get('statistics', []):
                                    all_names.extend([i['name'] for g in p.get('groups', []) for i in g.get('statisticsItems', [])])
                                
                                if 'Shots' in all_names and 'Penalty minutes' in all_names:
                                    new_leagues.add(cur_l)
                                    print(f"✨ НАЙДЕНА НОВАЯ: {cur_l}")
                                    await bot.send_message(CHANNEL_ID, f"🆕 Новая лига в копилку: `{cur_l}`")
                        except: continue
            except: continue

        if new_leagues:
            formatted = ",\n".join([f"'{l}'" for l in sorted(new_leagues)])
            await bot.send_message(CHANNEL_ID, f"🏁 **ВТОРОЙ ПРОХОД ЗАВЕРШЕН**\n\nДополнительные лиги:\n`{formatted}`")
        else:
            await bot.send_message(CHANNEL_ID, "⚠️ Новых лиг с полной статой не обнаружено.")

if __name__ == "__main__":
    asyncio.run(second_pass_scanner(7))
