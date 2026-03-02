import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def ultra_scanner(days_range=7):
    # Улучшенные заголовки для обхода блокировок
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*", "Origin": "https://www.sofascore.com", "Referer": "https://www.sofascore.com/"
    }
    
    final_white_list = set()
    tested_leagues = set()

    async with AsyncSession() as session:
        print("🚀 ЗАПУСК УЛЬТРА-СКАНЕРА v75.0")
        
        for d in range(1, days_range + 1):
            date_offset = f"-{d}"
            print(f"📅 --- ПРОВЕРЯЮ ДЕНЬ {d} ---")
            
            f_url = f"https://www.flashscore.ru/x/feed/f_4_{date_offset}_3_ru-ru_1"
            try:
                r = await session.get(f_url, headers={"User-Agent": "Mozilla/5.0", "x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                if "AA÷" not in r.text: continue

                blocks = r.text.split('~')
                cur_league = "Unknown"
                
                for block in blocks:
                    if block.startswith('ZA÷'): cur_league = block.split('ZA÷')[1].split('¬')[0]
                    if cur_league in final_white_list or cur_league in tested_leagues: continue

                    if block.startswith('AA÷'):
                        h_team = block.split('AE÷')[1].split('¬')[0]
                        tested_leagues.add(cur_league)
                        
                        # Очистка названия для более точного поиска
                        search_name = h_team.split('(')[0].replace('U20', '').replace('U18', '').strip()
                        print(f"🔍 Ищу в SofaScore: {cur_league} -> {search_name}")
                        
                        try:
                            # 1. Поиск (пробуем 2 раза с паузой)
                            s_url = f"https://www.sofascore.com/api/v1/search/all?q={search_name}"
                            s_req = await session.get(s_url, headers=headers, impersonate="chrome110")
                            await asyncio.sleep(2)
                            
                            results = s_req.json().get('results', [])
                            event_id = None
                            for res in results:
                                if res.get('type') == 'event' and res['entity'].get('sport', {}).get('slug') == 'ice-hockey':
                                    event_id = res['entity']['id']
                                    break
                            
                            if not event_id:
                                print(f"❓ Не нашел матч для: {search_name}")
                                continue

                            # 2. Проверка статы
                            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
                            st_req = await session.get(stat_url, headers=headers, impersonate="chrome110")
                            
                            if st_req.status_code == 200:
                                data = st_req.json()
                                has_stats = False
                                for period in data.get('statistics', []):
                                    if period.get('period') in ['1ST', 'ALL']: # Проверяем и то, и то
                                        items = [i['name'] for g in period.get('groups', []) for i in g.get('statisticsItems', [])]
                                        if 'Shots' in items: # Хотя бы броски
                                            has_stats = True
                                            break
                                
                                if has_stats:
                                    final_white_list.add(cur_league)
                                    print(f"✅ НАШЕЛ: {cur_league}")
                                    await bot.send_message(CHANNEL_ID, f"💎 Лига добавлена: `{cur_league}`")
                                else:
                                    print(f"❌ В {cur_league} нет нужной статы")
                        except Exception as e:
                            print(f"⚠️ Ошибка на матче {h_team}: {e}")
                            continue
            except: continue

        # Итог
        if final_white_list:
            res_msg = "🏆 **ИТОГОВЫЙ СПИСОК:**\n\n`" + ",\n".join([f"'{l}'" for l in sorted(final_white_list)]) + "`"
            await bot.send_message(CHANNEL_ID, res_msg, parse_mode="Markdown")
        else:
            await bot.send_message(CHANNEL_ID, "⚠️ За 7 дней ничего не найдено. Проверь логи Railway!")

if __name__ == "__main__":
    asyncio.run(ultra_scanner(7))
