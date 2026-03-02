import asyncio
import aiohttp
import os
from datetime import datetime, timedelta

# --- БЕЗОПАСНЫЙ ДОСТУП ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_tg(text):
    if not TOKEN or not CHAT_ID:
        print("⚠ ПЕРЕМЕННЫЕ НЕ НАЙДЕНЫ! Проверь Variables в Railway.", flush=True)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        async with session.post(url, json=payload) as r:
            return await r.json()

async def check_league_stats(session, ids):
    """Проверка наличия ударов в створ и штрафов в лиге"""
    for mid in ids[:3]:
        try:
            url = f"https://api.sofascore.com/api/v1/event/{mid}/statistics"
            async with session.get(url, timeout=5) as r:
                if r.status != 200: continue
                data = await r.json()
                periods = data.get('statistics', [])
                target = next((p for p in periods if p.get('period') == 'ALL'), None)
                if not target: continue

                has_shots, has_pen = False, False
                for group in target.get('groups', []):
                    for item in group.get('statisticsItems', []):
                        key = str(item.get('key', '')).lower()
                        name = str(item.get('name', '')).lower()
                        # Те самые маркеры, которые мы выцепили
                        if key in ['shots', 'shotsongoal'] or 'створ' in name:
                            has_shots = True
                        if 'penalty' in key or 'штраф' in name:
                            has_pen = True
                if has_shots and has_pen: return True
        except: continue
    return False

async def main():
    print("--- 🚀 v154.0 ЗАПУЩЕНА ЧЕРЕЗ ENV ---", flush=True)
    await send_tg("✅ <b>Бот на связи!</b> Начинаю фильтрацию лиг по броскам и штрафам...")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    white_list = set()
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # Проверяем последние 3 дня (включая сегодня)
        days = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(3)]
        
        for date in days:
            print(f"📅 Чекаю дату: {date}", flush=True)
            url = f"https://api.sofascore.com/api/v1/sport/ice-hockey/scheduled-events/{date}"
            async with session.get(url) as r:
                if r.status != 200: continue
                events = (await r.json()).get('events', [])
                
                # Группировка
                leagues = {}
                for ev in events:
                    name = ev.get('tournament', {}).get('name', 'Unknown')
                    if name not in leagues: leagues[name] = []
                    leagues[name].append(ev.get('id'))
                
                for l_name, ids in leagues.items():
                    if l_name in white_list: continue
                    if await check_league_stats(session, ids):
                        white_list.add(l_name)
                        print(f"🏁 Лига подтверждена: {l_name}", flush=True)
                    await asyncio.sleep(0.2)

        # Финальная отправка
        if white_list:
            msg = "<b>📊 БЕЛЫЙ СПИСОК ЛИГ:</b>\n\n"
            msg += "\n".join([f"• <code>{l}</code>" for l in sorted(white_list)])
            msg += f"\n\n<i>Всего: {len(white_list)}</i>"
        else:
            msg = "⚠️ Лиг с полной статистикой за 3 дня не обнаружено."
        
        await send_tg(msg)

if __name__ == "__main__":
    asyncio.run(main())
