import asyncio
import aiohttp
import json

async def main():
    print("--- 🕵️‍♂️ БУРИМ LIVESCORE В ПОИСКАХ СТАТЫ ---", flush=True)
    
    url_live = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/3"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print("1️⃣ Ищем любой матч в лайве...", flush=True)
        try:
            async with session.get(url_live, timeout=10) as r:
                if r.status != 200:
                    print("❌ Ошибка получения лайва.")
                    return
                data = await r.json()
                
                # Вытаскиваем ID первого матча (Eid)
                match_id = None
                h_name, a_name = "Home", "Away"
                
                for stage in data.get('Stages', []):
                    for ev in stage.get('Events', []):
                        match_id = ev.get('Eid')
                        h_name = ev.get('T1', [{}])[0].get('Nm', 'Home')
                        a_name = ev.get('T2', [{}])[0].get('Nm', 'Away')
                        break # Берем самый первый
                    if match_id: break
                
                if not match_id:
                    print("🤷‍♂️ Сейчас нет ни одного хоккейного матча в лайве для проверки.")
                    return
                
                print(f"✅ Взят матч: {h_name} - {a_name} (ID: {match_id})")
                print("2️⃣ Стучимся за детальной статистикой этого матча...", flush=True)
                
                # Эндпоинт детальной инфы матча
                url_detail = f"https://prod-public-api.livescore.com/v1/api/detail/hockey/{match_id}"
                async with session.get(url_detail, timeout=10) as rd:
                    if rd.status != 200:
                        print(f"❌ Сервер не отдал детали. Статус: {rd.status}")
                        return
                    
                    detail_data = await rd.json()
                    
                    # Ищем блок со статистикой. У LiveScore он обычно называется 'Stat'
                    stat_block = detail_data.get('Stat', [])
                    
                    if not stat_block:
                        print("❌ В этом матче пусто. Блока 'Stat' нет. (Либо матч вялый, либо ключи другие).")
                        # Распечатаем все ключи, чтобы понять, где они прячут стату
                        print("Доступные ключи в JSON:", list(detail_data.keys()))
                    else:
                        print("\n🔥🔥🔥 БИНГО! СТАТИСТИКА НАЙДЕНА:")
                        # Красиво выводим кусок JSON со статой
                        print(json.dumps(stat_block, indent=2, ensure_ascii=False))
                        print("\n🛑 Жду скриншот или копию этого текста! Будем расшифровывать их ключи.")

        except Exception as e:
            print(f"⚠️ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
