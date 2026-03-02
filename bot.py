import asyncio
import aiohttp
import os

# Данные из переменных окружения Railway
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

# Твой Белый Список лиг
WHITE_LIST = [
    "KHL", "National Hockey League", "SHL", "Liiga", 
    "DEL", "Extraliga", "Tipsport Liga", "ICE Hockey League", "1st Liga"
]

SENT_SIGNALS = set() # Чтобы не дублировать сигналы

async def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        await session.post(url, json=payload)

async def get_stats(session, mid):
    """Получение ударов и штрафов за 1-й период"""
    try:
        url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
        async with session.get(url, timeout=5) as r:
            if r.status != 200: return None
            data = await r.json()
            # Ищем статистику именно за 1-й период
            period_stats = next((p for p in data.get('statistics', []) if p.get('period') == '1ST'), None)
            if not period_stats: return None

            shots, penalties = 0, 0
            for group in period_stats.get('groups', []):
                for item in group.get('statisticsItems', []):
                    key = str(item.get('key', '')).lower()
                    h = int(item.get('homeValue', 0))
                    a = int(item.get('awayValue', 0))
                    
                    if key in ['shots', 'shotsongoal']: shots = h + a
                    if 'penalty' in key: penalties = h + a
            return shots, penalties
    except: return None

async def main():
    print("--- 🎯 СНАЙПЕР ЗАПУЩЕН (Логика 1-го периода) ---", flush=True)
    
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        while True:
            try:
                # 1. Получаем Live матчи
                async with session.get("https://api.sofascore.com/api/v1/sport/ice-hockey/events/live") as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])

                for ev in events:
                    mid = ev.get('id')
                    if mid in SENT_SIGNALS: continue

                    # 2. Фильтр по лиге
                    league_name = ev.get('tournament', {}).get('name', '')
                    if not any(target in league_name for target in WHITE_LIST): continue

                    # 3. Фильтр по времени (ждем перерыва после 1-го периода)
                    # 'status': {'code': 31} обычно означает перерыв (period 1 finished)
                    # Также проверяем description: 'HT' или 'Period 1'
                    status = ev.get('status', {}).get('type', '')
                    description = ev.get('status', {}).get('description', '')
                    
                    if description == "After 1st period" or (status == "finished" and ev.get('lastPeriod') == "period1"):
                        
                        # 4. Фильтр по счету (0:0, 1:0, 0:1)
                        h_score = ev.get('homeScore', {}).get('period1', 0)
                        a_score = ev.get('awayScore', {}).get('period1', 0)
                        
                        if (h_score + a_score) <= 1:
                            # 5. Проверка статистики
                            stats = await get_stats(session, mid)
                            if stats:
                                shots, penalties = stats
                                # УСЛОВИЕ: Удары от 13, Штраф от 2
                                if shots >= 13 and penalties >= 2:
                                    home = ev['homeTeam']['shortName']
                                    away = ev['awayTeam']['shortName']
                                    
                                    msg = (
                                        f"🏒 <b>СИГНАЛ: ХОККЕЙ</b>\n"
                                        f"🏆 Лига: {league_name}\n"
                                        f"🤝 Матч: {home} vs {away}\n"
                                        f"⏰ Статус: <b>Перерыв после 1-го периода</b>\n"
                                        f"-------------------\n"
                                        f"🥅 Счет 1-го периода: <b>{h_score}:{a_score}</b>\n"
                                        f"🎯 Удары в створ: <b>{shots}</b>\n"
                                        f"⏳ Штрафное время: <b>{penalties} мин</b>\n"
                                        f"-------------------\n"
                                        f"🔥 <i>Логика: Низкий счет при высокой активности!</i>"
                                    )
                                    await send_tg(msg)
                                    SENT_SIGNALS.add(mid)
                                    print(f"📢 Сигнал отправлен: {home}-{away}", flush=True)

            except Exception as e:
                print(f"⚠ Ошибка цикла: {e}", flush=True)
            
            await asyncio.sleep(60) # Проверка каждую минуту

if __name__ == "__main__":
    asyncio.run(main())
