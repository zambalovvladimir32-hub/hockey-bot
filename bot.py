import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

# ТЕПЕРЬ ИМЕНА ТОЧНО КАК НА СКРИНШОТЕ
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def send_tg(text):
    if not TOKEN or not CHAT_ID:
        print("❌ ОШИБКА: Переменные не найдены в Railway!", flush=True)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        async with session.post(url, json=payload) as r:
            return await r.json()

async def check_league(session, ids):
    for mid in ids[:5]: # Проверяем до 5 матчей для надежности
        try:
            url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
            async with session.get(url, timeout=7) as r:
                if r.status != 200: continue
                data = await r.json()
                target = next((p for p in data.get('statistics', []) if p.get('period') == 'ALL'), None)
                if not target: continue
                
                has_s, has_p = False, False
                for group in target.get('groups', []):
                    for item in group.get('statisticsItems', []):
                        key = str(item.get('key', '')).lower()
                        # Наша "собака": Shots или ShotsOnGoal
                        if key in ['shots', 'shotsongoal']: has_s = True
                        # Штрафные минуты
                        if 'penalty' in key: has_p = True
                
                if has_s and has_p: return True
        except: continue
    return False

async def main():
    print("--- 🛰 ЗАПУСК v156.0 (ПОД ТВОИ ПЕРЕМЕННЫЕ) ---", flush=True)
    
    # Сразу проверяем связь
    print(f"DEBUG: Использую TOKEN: {TOKEN[:5]}*** и ID: {CHAT_ID}", flush=True)
    await send_tg("🚀 <b>Связь установлена!</b> Начинаю фильтрацию лиг...")

    headers = {"User-Agent": "Mozilla/5.0"}
    white_list = set()
    days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]

    async with aiohttp.ClientSession(headers=headers) as session:
        for date in days:
            print(f"📅 Проверка: {date}", flush=True)
            try:
                url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}"
                async with session.get(url, timeout=15) as r:
                    if r.status != 200: continue
                    events = (await r.json()).get('events', [])
                    leagues = {}
                    for ev in events:
                        n = ev.get('tournament', {}).get('name', 'Unknown')
                        if n not in leagues: leagues[n] = []
                        leagues[n].append(ev.get('id'))
                    
                    for l_name, ids in leagues.items():
                        if l_name in white_list: continue
                        if await check_league(session, ids):
                            white_list.add(l_name)
                            print(f"✅ Найдена: {l_name}", flush=True)
                        await asyncio.sleep(0.1)
            except: continue

    if white_list:
        res_text = "<b>📊 БЕЛЫЙ СПИСОК ЛИГ:</b>\n\n" + "\n".join([f"• <code>{l}</code>" for l in sorted(white_list)])
    else:
        res_text = "⚠️ За 3 дня лиг со статистикой не найдено."
    
    await send_tg(res_text)
    print("🏁 Готово!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
