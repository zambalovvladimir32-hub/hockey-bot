import asyncio
import aiohttp
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ---
TOKEN = "ТВОЙ_ТОКЕН"
CHAT_ID = "ТВОЙ_CHAT_ID"

async def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        try:
            await session.post(url, json=payload, timeout=10)
        except: pass

async def check_league(session, event_ids):
    # Проверяем первые 3 игры лиги. Если хотя бы в одной есть стата — лига годна.
    for mid in event_ids[:3]:
        try:
            url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
            async with session.get(url, timeout=5) as r:
                if r.status != 200: continue
                data = await r.json()
                # Ищем блок 'ALL' (итог матча)
                target = next((p for p in data.get('statistics', []) if p.get('period') == 'ALL'), None)
                if not target: continue
                
                has_shots = False
                has_penalty = False
                
                for group in target.get('groups', []):
                    for item in group.get('statisticsItems', []):
                        key = str(item.get('key', '')).lower()
                        name = str(item.get('name', '')).lower()
                        
                        # Наша "собака": Shots, shotsongoal или "створ"
                        if key in ['shots', 'shotsongoal'] or 'створ' in name:
                            has_shots = True
                        # Штрафы
                        if 'penalty' in key or 'штраф' in name:
                            has_penalty = True
                
                if has_shots and has_penalty: return True
        except: continue
    return False

async def main():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    white_list = set()
    # Берем 3 дня для анализа
    days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]

    async with aiohttp.ClientSession(headers=headers) as session:
        print("🚀 Начинаю фильтрацию лиг...", flush=True)
        
        for date in days:
            try:
                url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}"
                async with session.get(url, timeout=10) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])
                    
                    # Группируем по лигам
                    leagues = {}
                    for ev in events:
                        name = ev.get('tournament', {}).get('name', 'Unknown')
                        if name not in leagues: leagues[name] = []
                        leagues[name].append(ev.get('id'))
                    
                    for l_name, ids in leagues.items():
                        if l_name in white_list: continue
                        # Бот сам проверяет и фильтрует
                        if await check_league(session, ids):
                            white_list.add(l_name)
                            print(f"✅ Найдена живая лига: {l_name}", flush=True)
                        await asyncio.sleep(0.2) # Анти-спам
            except: continue

        # Финальный аккорд: отправка только чистого списка
        if white_list:
            sorted_list = sorted(list(white_list))
            msg = "<b>🏆 АВТО-ФИЛЬТР: БЕЛЫЙ СПИСОК</b>\n<i>(Лиги с ударами и штрафами за 72ч)</i>\n\n"
            msg += "\n".join([f"• <code>{l}</code>" for l in sorted_list])
            msg += f"\n\n<b>Всего: {len(sorted_list)}</b>"
        else:
            msg = "❌ Лиг со статистикой не найдено."
        
        await send_tg(msg)
        print("🏁 Работа завершена, отчет отправлен.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
