import asyncio
from curl_cffi.requests import AsyncSession

async def main():
    print("--- 🥷 ЗАПУСКАЕМ НИНДЗЯ-ПАРСЕР (CURL_CFFI) ---", flush=True)
    
    # Стучимся в React API LiveScore
    url_live = "https://prod-public-api.livescore.com/v1/api/react/live/hockey/3.00"
    
    try:
        # МАГИЯ ЗДЕСЬ: impersonate="chrome120" заставляет скрипт притворяться реальным браузером
        async with AsyncSession(impersonate="chrome120") as session:
            print("⏳ Стучимся в LiveScore под видом Google Chrome 120...", flush=True)
            r = await session.get(url_live, timeout=15)
            
            print(f"📡 Статус ответа: {r.status_code}", flush=True)
            
            if r.status_code == 200:
                data = r.json()
                print("✅ УСПЕХ! Cloudflare нас пропустил как родных!")
                
                # Ищем первый попавшийся матч
                match_id = None
                for stage in data.get('Stages', []):
                    for ev in stage.get('Events', []):
                        match_id = ev.get('Eid')
                        h_name = ev.get('T1', [{}])[0].get('Nm', 'Home')
                        a_name = ev.get('T2', [{}])[0].get('Nm', 'Away')
                        break
                    if match_id: break
                    
                if match_id:
                    print(f"\n🏒 Найден матч в лайве: {h_name} - {a_name} (ID: {match_id})")
                    print("🔑 Стучимся в закрытую дверь за детальной статистикой...", flush=True)
                    
                    # Проверяем детальную инфу (где могут быть броски)
                    detail_url = f"https://prod-public-api.livescore.com/v1/api/react/match/hockey/{match_id}/3.00"
                    r_detail = await session.get(detail_url)
                    
                    print(f"   📡 Статус деталей: {r_detail.status_code}")
                    if r_detail.status_code == 200:
                        print("\n🔥🔥🔥 БИНГО! МЫ ВНУТРИ!")
                        print("📂 Разделы внутри этого матча:", list(r_detail.json().keys()))
            else:
                print("❌ Не пробило. Cloudflare спалил подмену.")
                print(r.text[:200])
                
    except Exception as e:
        print(f"⚠️ Ошибка соединения: {e}")

if __name__ == "__main__":
    asyncio.run(main())
