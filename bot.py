import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

# Твои переменные
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def send_tg(session, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    await session.post(url, json=payload)

async def check_stats(session, mid):
    """Стучимся в матч и смотрим, есть ли там блок статистики"""
    url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
    try:
        async with session.get(url, timeout=5) as r:
            if r.status == 200:
                data = await r.json()
                # Если массив statistics не пустой, значит стата есть
                if data.get('statistics'):
                    return True
    except: pass
    return False

async def main():
    print("--- 🕵️‍♂️ ЗАПУСК СКАНЕРА ЛИГ (ЗА 4 ДНЯ) ---", flush=True)
    
    # Генерируем даты за последние 4 дня (формат YYYY-MM-DD)
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 5)]
    
    valid_leagues = set()
    checked_tournaments = set()

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        await send_tg(session, "⏳ <b>Начинаю сканирование SofaScore за 4 дня...</b>\nИщу лиги со статистикой бросков/штрафов. Жди...")
        
        for date in dates:
            print(f"📅 Чекаем матчи за {date}", flush=True)
            url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}"
            
            try:
                async with session.get(url) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])
                    
                    for ev in events:
                        t_name = ev.get('tournament', {}).get('name', 'Unknown')
                        mid = ev.get('id')
                        status = ev.get('status', {}).get('code', 0)
                        
                        # Проверяем только завершенные матчи (обычно статус 100)
                        if status == 100 and t_name not in checked_tournaments:
                            checked_tournaments.add(t_name) # Запоминаем, что эту лигу уже видели
                            
                            print(f"🔍 Проверяю лигу: {t_name}...", flush=True)
                            has_stats = await check_stats(session, mid)
                            
                            if has_stats:
                                valid_leagues.add(t_name)
                                print(f"✅ Стата есть: {t_name}", flush=True)
                            else:
                                print(f"❌ Пусто: {t_name}", flush=True)
                            
                            # Пауза, чтобы API не кинуло в бан за спам
                            await asyncio.sleep(0.5) 
            except Exception as e:
                print(f"Ошибка на дате {date}: {e}", flush=True)

        # Формируем итоговое сообщение
        if valid_leagues:
            leagues_text = "\n".join([f"🏒 {l}" for l in sorted(valid_leagues)])
            msg = (f"✅ <b>СКАНИРОВАНИЕ ЗАВЕРШЕНО</b>\n\n"
                   f"Найдено лиг со статистикой: <b>{len(valid_leagues)}</b>\n\n"
                   f"Вот полный список:\n"
                   f"<pre>{leagues_text}</pre>\n\n"
                   f"<i>Скопируй нужные в свой WHITE_LIST!</i>")
        else:
            msg = "❌ Ничего не нашел. Возможно, SofaScore временно заблокировал запросы."
            
        await send_tg(session, msg)
        print("--- ОТЧЕТ ОТПРАВЛЕН В TELEGRAM ---", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
