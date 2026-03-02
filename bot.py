import asyncio
import aiohttp

# ВСТАВЬ ТОЧНО ОТСЮДА
TOKEN = "ТВОЙ_ТОКЕН" 
CHAT_ID = "ТВОЙ_ID"

async def test_link():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {
            "chat_id": CHAT_ID, 
            "text": "✅ СВЯЗЬ УСТАНОВЛЕНА! Токен и ID верны.",
            "parse_mode": "HTML"
        }
        print(f"📡 Отправляю запрос на: {url}", flush=True)
        async with session.post(url, json=payload) as r:
            res = await r.json()
            if res.get('ok'):
                print("🎉 СООБЩЕНИЕ УШЛО!", flush=True)
            else:
                print(f"❌ ОШИБКА: {res}", flush=True)

if __name__ == "__main__":
    asyncio.run(test_link())
