import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

# Твои данные из Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def deep_scan_to_tg(days_range=7):
    headers = {"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo"}
    confirmed_leagues = set() 

    async with AsyncSession() as session:
        print(f"🚀 Начинаю глобальный сбор лиг за {days_range} дней...")
        
        for d in range(1, days_range + 1):
            date_offset = f"-{d}"
            print(f"📅 Проверяю день {d}...")
            
            flash_url = f"https://www.flashscore.ru/x/feed/f_4_{date_offset}_3_ru-ru_1"
            try:
                r = await session.get(flash_url, headers=headers, impersonate="chrome110")
                if r.status_code != 200: continue

                blocks = r.text.split('~')
                current_league = "Unknown"
                
                for block in blocks:
                    if block.startswith('ZA÷'): 
                        current_league = block.split('ZA÷')[1].split('¬')[0]
                    
                    if current_league in confirmed_leagues: continue

                    if block.startswith('AA÷'):
                        h_name = block.split('AE÷')[1].split('¬')[0]
                        clean_name = re.sub(r'\(.*?\)', '', h_name).strip()
                        
                        try:
                            search = await session.get(f"https://www.sofascore.com/api/v1/search/all?q={clean_name}", impersonate="chrome110")
                            results = search.json().get('results', [])
                            if not results: continue
                            
                            event_id = results[0]['entity']['id']
                            stat_res = await session.get(f"https://www.sofascore.com/api/v1/event/{event_id}/statistics", impersonate="chrome110")
                            
                            if stat_res.status_code == 200:
                                s_data = stat_res.json()
                                for period in s_data.get('statistics', []):
                                    if period.get('period') == '1ST':
                                        items = [i['name'] for g in period.get('groups', []) for i in g.get('statisticsItems', [])]
                                        # Если в 1-м периоде есть и Броски, и Штрафы
                                        if 'Shots' in items and 'Penalty minutes' in items:
                                            confirmed_leagues.add(current_league)
                                            print(f"✅ Нашел: {current_league}")
                                            break
                        except: continue
            except: continue

        # Формируем сообщение для Telegram
        if confirmed_leagues:
            leagues_list = sorted(list(confirmed_leagues))
            # Форматируем как список Python для удобства вставки в код
            formatted_list = ",\n".join([f"'{l}'" for l in leagues_list])
            
            report = (f"🏆 **СПИСОК ВАЛИДНЫХ ЛИГ**\n"
                      f"_(За последние {days_range} дней)_\n\n"
                      f"Эти лиги отдают броски и штрафы за 1-й период:\n\n"
                      f"`{formatted_list}`")
            
            # Отправляем кусками, если список очень длинный
            if len(report) > 4096:
                for x in range(0, len(report), 4096):
                    await bot.send_message(CHANNEL_ID, report[x:x+4096], parse_mode="Markdown")
            else:
                await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
            
            print("DONE! Список отправлен в Telegram.")
        else:
            await bot.send_message(CHANNEL_ID, "❌ Лиги со статистикой не найдены.")

if __name__ == "__main__":
    asyncio.run(deep_scan_to_tg(7))
