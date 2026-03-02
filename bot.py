import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def sniper_scanner(days_range=7):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    final_white_list = set()
    tested_leagues = set()

    async with AsyncSession() as session:
        print("🚀 ЗАПУСК v76.0: Ищем лиги...")
        
        for d in range(1, days_range + 1):
            date_offset = f"-{d}"
            f_url = f"https://www.flashscore.ru/x/feed/f_4_{date_offset}_3_ru-ru_1"
            
            try:
                r = await session.get(f_url, headers={"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                blocks = r.text.split('~')
                cur_league = "Unknown"
                
                for block in blocks:
                    if block.startswith('ZA÷'): cur_league = block.split('ZA÷')[1].split('¬')[0]
                    if cur_league in final_white_list or cur_league in tested_leagues: continue

                    if block.startswith('AA÷'):
                        h_team = block.split('AE÷')[1].split('¬')[0]
                        a_team = block.split('AF÷')[1].split('¬')[0]
                        tested_leagues.add(cur_league)
                        
                        # Поиск по паре команд для точности
                        search_query = f"{h_team} {a_team}".split('(')[0].strip()
                        print(f"🔎 Проверяю: {cur_league} -> {search_query}")
                        
                        try:
                            s_url = f"https://www.sofascore.com/api/v1/search/all?q={search_query}"
                            s_req = await session.get(s_url, headers=headers, impersonate="chrome110")
                            await asyncio.sleep(1.5)
                            
                            results = s_req.json().get('results', [])
                            event_id = next((res['entity']['id'] for res in results if res.get('type') == 'event'), None)
                            
                            if not event_id: continue

                            st_req = await session.get(f"https://www.sofascore.com/api/v1/event/{event_id}/statistics", headers=headers, impersonate="chrome110")
                            if st_req.status_code == 200:
                                data = st_req.json()
                                items = []
                                # Проверяем ВСЕ вкладки на наличие бросков и штрафов
                                for period in data.get('statistics', []):
                                    p_items = [i['name'] for g in period.get('groups', []) for i in g.get('statisticsItems', [])]
                                    items.extend(p_items)
                                
                                if 'Shots' in items and 'Penalty minutes' in items:
                                    final_white_list.add(cur_league)
                                    print(f"💎 НАЙДЕНА: {cur_league}")
                                    await bot.send_message(CHANNEL_ID, f"✅ Лига со статой: `{cur_league}`")
                        except: continue
            except: continue

        if final_white_list:
            report = "🏆 **ВАЛИДНЫЕ ЛИГИ:**\n\n`" + ",\n".join([f"'{l}'" for l in sorted(final_white_list)]) + "`"
            await bot.send_message(CHANNEL_ID, report, parse_mode="Markdown")
        else:
            await bot.send_message(CHANNEL_ID, "⚠️ Опять пусто. SofaScore скрывает данные.")

if __name__ == "__main__":
    asyncio.run(sniper_scanner(7))
