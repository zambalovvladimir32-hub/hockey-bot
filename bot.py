import asyncio
import aiohttp
from datetime import datetime, timedelta

async def main():
    # Берем вчерашний день
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"--- 🔬 РЕНТГЕН ЗАПУЩЕН (Ищем матч за {yesterday}) ---")

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{yesterday}"
        async with session.get(url) as r:
            if r.status != 200:
                print("❌ Ошибка доступа к расписанию")
                return
            data = await r.json()
            
            for ev in data.get('events', []):
                # Ищем любой завершенный матч
                if ev.get('status', {}).get('code') == 100:
                    mid = ev.get('id')
                    h_name = ev.get('homeTeam', {}).get('name', 'Unknown')
                    a_name = ev.get('awayTeam', {}).get('name', 'Unknown')
                    
                    # Стучимся за статой
                    async with session.get(f"https://api.sofascore.com/api/v1/event/{mid}/statistics") as rs:
                        if rs.status == 200:
                            st_data = await rs.json()
                            if st_data.get('statistics'):
                                print(f"\n✅ НАШЕЛ МАТЧ СО СТАТИСТИКОЙ: {h_name} - {a_name}")
                                print("📂 ВОТ КАК SOFASCORE НАЗЫВАЕТ ПЕРИОДЫ В АРХИВЕ:")
                                
                                # Выводим названия всех блоков (ALL, 1ST, 2ND и т.д.)
                                for p in st_data.get('statistics', []):
                                    period_name = p.get('period', 'БЕЗ НАЗВАНИЯ')
                                    print(f" ➡️ {period_name}")
                                    
                                    # Распечатаем парочку ключей из 1-го периода, чтобы убедиться
                                    if '1' in str(period_name):
                                        print("    Ключи внутри этого периода:")
                                        for g in p.get('groups', [])[:1]: # Берем первую группу
                                            for i in g.get('statisticsItems', [])[:3]: # Берем 3 параметра
                                                print(f"      - {i.get('key')}")
                                
                                print("\n🛑 Рентген завершен. Кидай скриншот консоли сюда!")
                                return # Останавливаем после первого же успешного матча

            print("❌ Не нашел ни одного завершенного матча со статистикой за вчера.")

if __name__ == "__main__":
    asyncio.run(main())
