import asyncio
import aiohttp
import json

async def main():
    print("--- 🕵️‍♂️ ПОДБИРАЕМ КЛЮЧИ К LIVESCORE ---", flush=True)
    
    url_live = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/3"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print("1️⃣ Ищем матч...", flush=True)
        try:
            async with session.get(url_live, timeout=10) as r:
                data = await r.json()
                match_id = None
                
                for stage in data.get('Stages', []):
                    for ev in stage.get('Events', []):
                        match_id = ev.get('Eid')
                        h_name = ev.get('T1', [{}])[0].get('Nm', 'Home')
                        a_name = ev.get('T2', [{}])[0].get('Nm', 'Away')
                        break
                    if match_id: break
                
                if not match_id:
                    print("🤷‍♂️ Нет матчей в лайве.")
                    return
                
                print(f"✅ Взят матч: {h_name} - {a_name} (ID: {match_id})\n")
                
                # Список возможных дверей, за которыми прячут стату
                endpoints = [
                    f"https://prod-public-api.livescore.com/v1/api/app/detail/hockey/{match_id}/3",
                    f"https://prod-public-api.livescore.com/v1/api/app/match/hockey/{match_id}/3",
                    f"https://prod-public-api.livescore.com/v1/api/app/statistics/hockey/{match_id}/3",
                    f"https://prod-public-api.livescore.com/v1/api/app/scoreboard/hockey/{match_id}/3"
                ]

                for idx, url in enumerate(endpoints, 1):
                    print(f"🔑 Пробуем ключ #{idx}...")
                    async with session.get(url, timeout=10) as rd:
                        print(f"   📡 Статус: {rd.status}")
                        if rd.status == 200:
                            print("\n🔥🔥🔥 БИНГО! МЫ ВЗЛОМАЛИ ДВЕРЬ!")
                            print(f"Рабочая ссылка: {url}")
                            detail_data = await rd.json()
                            
                            # Просто распечатаем все главные ключи, чтобы понять структуру
                            print("\n📂 Доступные разделы внутри матча:")
                            for key in detail_data.keys():
                                print(f"  - {key}")
                            return # Выходим, мы нашли что искали!
                        
                print("\n❌ Ни один ключ не подошел. Видимо, у них еще более хитрая маршрутизация.")

        except Exception as e:
            print(f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
