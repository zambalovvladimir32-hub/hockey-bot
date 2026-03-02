import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def auto_filter_leagues(days_range=7):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    final_white_list = set() 

    async with AsyncSession() as session:
        print("🚀 ЗАПУСК АВТО-ФИЛЬТРАЦИИ...")
        
        for d in range(1, days_range + 1):
            date_offset = f"-{d}"
            flash_url = f"https://www.flashscore.ru/x/feed/f_4_{date_offset}_3_ru-ru_1"
            
            try:
                r = await session.get(flash_url, headers={"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                blocks = r.text.split('~')
                current_league = "Unknown"
                
                for block in blocks:
                    if block.startswith('ZA÷'): 
                        current_league = block.split('ZA÷')[1].split('¬')[0]
                    
                    if current_league in final_white_list: continue

                    if block.startswith('AA÷'):
                        h_name = block.split('AE÷')[1].split('¬')[0]
                        clean_name = re.sub(r'\(.*?\)', '', h_name).strip()
                        
                        try:
                            # 1. Поиск на SofaScore
                            search = await session.get(f"https://www.sofascore.com/api/v1/search/all?q={clean_name}", headers=headers, impersonate="chrome110")
                            await asyncio.sleep(0.5) # Мини-пауза
                            
                            res = search.json().get('results', [])
                            if not res: continue
                            
                            event_id = res[0]['entity']['id']
                            
                            # 2. Проверка детальной статистики
                            stat_res = await session.get(f"https://www.sofascore.com/api/v1/event/{event_id}/statistics", headers=headers, impersonate="chrome110")
                            if stat_res.status_code == 200:
                                s_data = stat_res.json()
                                for period in s_data.get('statistics', []):
                                    # Проверяем строго первый период
                                    if period.get('period') == '1ST':
                                        items = [i['name'] for g in period.get('groups', []) for i in g.get('statisticsItems', [])]
                                        
                                        # 🔥 ЖЕСТКИЙ ФИЛЬТР: Должны быть и броски, и штрафы
                                        if 'Shots' in items and 'Penalty minutes' in items:
                                            final_white_list.add(current_league)
                                            print(f"💎 ПОДХОДИТ: {current_league}")
                                            break
                        except: continue
            except: continue

        # Финальный отчет
        if final_white_list:
            formatted = ",\n".join([f"'{l}'" for l in sorted(final_white_list)])
            msg = (f"✅ **БЕЛЫЙ СПИСОК СФОРМИРОВАН**\n"
                   f"_(Лиги со статистикой за 1-й период)_\n\n"
                   f"`{formatted}`")
            await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
        else:
            await bot.send_message(CHANNEL_ID, "❌ Ни одна лига не прошла фильтрацию за 7 дней.")

if __name__ == "__main__":
    asyncio.run(auto_filter_leagues(7))
