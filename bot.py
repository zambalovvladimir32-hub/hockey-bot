import asyncio
import aiohttp

async def main():
    print("--- 🕵️‍♂️ ВЗЛОМ LIVESCORE: ПРОВЕРКА СВЯЗИ ---", flush=True)
    
    # Секретный эндпоинт мобильного API LiveScore (Хоккей, Лайв)
    # Цифра 3 в конце — это часовой пояс, может быть любой
    url = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/3"
    
    # Маскируемся под мобильное приложение / обычный браузер
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://www.livescore.com",
        "Referer": "https://www.livescore.com/"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        print("⏳ Стучимся в закрытые двери LiveScore...", flush=True)
        try:
            async with session.get(url, timeout=10) as r:
                print(f"📡 Статус ответа: {r.status}")
                
                if r.status == 200:
                    data = await r.json()
                    stages = data.get('Stages', [])
                    print(f"✅ УСПЕХ! Сервер пропустил нас. Найдено турниров в лайве: {len(stages)}")
                    
                    if stages:
                        print("\n🏒 Вот что сейчас идет:")
                        for stage in stages[:3]: # Выведем первые 3 лиги для примера
                            league_name = stage.get('Snm', 'Неизвестная лига')
                            events = stage.get('Events', [])
                            for ev in events:
                                h_name = ev.get('T1', [{}])[0].get('Nm', 'Home')
                                a_name = ev.get('T2', [{}])[0].get('Nm', 'Away')
                                print(f"  🔸 {league_name}: {h_name} - {a_name}")
                        
                        print("\n🔥 Отлично! Дальше я раскопаю, где внутри этих матчей лежат броски и штрафы.")
                else:
                    print("❌ БЛОКИРОВКА. Cloudflare или защита сервера не пускает.")
                    text = await r.text()
                    print(f"Ответ сервера: {text[:200]}")
        except Exception as e:
            print(f"⚠️ Ошибка соединения: {e}")

if __name__ == "__main__":
    asyncio.run(main())
