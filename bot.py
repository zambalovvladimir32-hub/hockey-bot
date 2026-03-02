import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHANNEL_ID")

async def send_tg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        await session.post(url, json=payload)

async def check_league_detailed(session, ids):
    has_shots = False
    has_any_penalty = False
    
    for mid in ids[:8]: # Проверяем больше матчей для верности
        try:
            url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
            async with session.get(url, timeout=7) as r:
                if r.status != 200: continue
                data = await r.json()
                stats = data.get('statistics', [])
                target = next((p for p in stats if p.get('period') == 'ALL'), None)
                if not target: continue
                
                for group in target.get('groups', []):
                    for item in group.get('statisticsItems', []):
                        key = str(item.get('key', '')).lower()
                        # Расширенный поиск бросков
                        if 'shot' in key: has_shots = True
                        # Расширенный поиск любых штрафов
                        if 'penalt' in key or 'suspended' in key: has_any_penalty = True
                
                if has_shots: break # Если нашли хоть броски, уже интересно
        except: continue
    return has_shots, has_any_penalty

async def main():
    print("--- 🛰 ЗАПУСК v157.0 (ГИБКИЙ ПОИСК) ---", flush=True)
    await send_tg("🔍 <b>Начинаю поиск...</b> Проверяю расширенную статистику за 3 дня.")

    headers = {"User-Agent": "Mozilla/5.0"}
    found_leagues = {} # Имя: статус
    days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]

    async with aiohttp.ClientSession(headers=headers) as session:
        for date in days:
            print(f"📅 Дата: {date}", flush=True)
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
                        if l_name in found_leagues: continue
                        s, p = await check_league_detailed(session, ids)
                        if s: # Если есть хотя бы броски
                            status = "🎯 Броски + ⏳ Штрафы" if p else "🎯 Только броски"
                            found_leagues[l_name] = status
                            print(f"✅ Найдена: {l_name} ({status})", flush=True)
                        await asyncio.sleep(0.1)
            except: continue

    if found_leagues:
        msg = "<b>✅ НАЙДЕНЫ ЛИГИ СО СТАТОЙ:</b>\n\n"
        for l, stat in sorted(found_leagues.items()):
            msg += f"• <code>{l}</code>\n  └ {stat}\n\n"
    else:
        msg = "⚠️ Даже с гибким поиском ничего не найдено. Возможно, API SofaScore временно не отдает статистику в архив."
    
    await send_tg(msg)
    print("🏁 Готово!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
