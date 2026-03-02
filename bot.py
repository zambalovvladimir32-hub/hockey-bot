import asyncio, re, os
from curl_cffi.requests import AsyncSession
from aiogram import Bot

# Инициализация бота
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

async def live_monitor():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    processed_matches = set() 

    async with AsyncSession() as session:
        print("✅ БОТ ЗАПУЩЕН. Режим: ПЕРЕРЫВ | 0:0 | Броски >= 5 | Штраф >= 2")
        
        while True:
            try:
                # 1. Запрос лайв-фида Flashscore
                r = await session.get("https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1", 
                                      headers={"x-fsign": "SW9D1eZo"}, impersonate="chrome110")
                
                blocks = r.text.split('~')
                current_league = "Unknown"
                
                for block in blocks:
                    if block.startswith('ZA÷'): 
                        current_league = block.split('ZA÷')[1].split('¬')[0]
                    
                    if block.startswith('AA÷'):
                        mid = block.split('AA÷')[1].split('¬')[0]
                        if mid in processed_matches: continue

                        # Проверка: Перерыв (3 или 46) + Счет (0:0)
                        is_break = 'AB÷3' in block or 'NS÷46' in block
                        is_zero = 'AG÷0' in block and 'AH÷0' in block

                        if is_break and is_zero:
                            h_team = block.split('AE÷')[1].split('¬')[0]
                            a_team = block.split('AF÷')[1].split('¬')[0]
                            
                            # Поиск ID на SofaScore
                            q = f"{h_team} {a_team}".split('(')[0].strip()
                            s_search = await session.get(f"https://www.sofascore.com/api/v1/search/all?q={q}", headers=headers)
                            await asyncio.sleep(1.2) # Анти-бан пауза
                            
                            results = s_search.json().get('results', [])
                            eid = next((i['entity']['id'] for i in results if i.get('type') == 'event'), None)
                            
                            if eid:
                                # Запрос статики
                                st_req = await session.get(f"https://www.sofascore.com/api/v1/event/{eid}/statistics", headers=headers)
                                if st_req.status_code == 200:
                                    data = st_req.json()
                                    shots, pens = 0, 0
                                    
                                    # Парсим статику: приоритет 1ST, запасной вариант ALL
                                    for p in data.get('statistics', []):
                                        if p.get('period') in ['1ST', 'ALL']:
                                            for g in p.get('groups', []):
                                                for item in g.get('statisticsItems', []):
                                                    if item['name'] == 'Shots':
                                                        val = int(item['homeValue']) + int(item['awayValue'])
                                                        shots = max(shots, val)
                                                    if item['name'] == 'Penalty minutes':
                                                        val = int(item['homeValue']) + int(item['awayValue'])
                                                        pens = max(pens, val)

                                    # Проверка условий
                                    if shots >= 5 and pens >= 2:
                                        msg = (f"🏟 **ПЕРЕРЫВ (Счёт 0:0)**\n"
                                               f"🏆 {current_league}\n"
                                               f"🏒 {h_team} — {a_team}\n\n"
                                               f"🎯 Броски в створ: **{shots}**\n"
                                               f"⚖️ Штрафное время: **{pens} мин.**")
                                        await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                        processed_matches.add(mid)
                                        print(f"🎯 Сигнал отправлен: {h_team} - {a_team}")

            except Exception as e:
                pass # Игнорируем ошибки сети
            
            await asyncio.sleep(45)

if __name__ == "__main__":
    asyncio.run(live_monitor())
