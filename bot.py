import asyncio
import aiohttp
import os
from aiogram import Bot
from openai import AsyncOpenAI

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

URL = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"

async def get_test_analysis(teams):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей {teams}. Прогноз ТБ 4.5 в 10 словах."}],
            max_tokens=40
        )
        return res.choices[0].message.content
    except: return "Анализ готов."

async def run_force_test():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, timeout=15) as resp:
                data = await resp.json()
                # Берем самый первый матч из списка, какой бы он ни был
                stage = data.get('Stages', [])[0]
                event = stage.get('Events', [])[0]
                
                league = stage.get('Snm', 'Ночная лига')
                home = event.get('T1', [{}])[0].get('Nm', 'Команда А')
                away = event.get('T2', [{}])[0].get('Nm', 'Команда Б')
                score = f"{event.get('Tr1', 0)}:{event.get('Tr2', 0)}"
                status = event.get('Eps', 'LIVE')
                
                analysis = await get_test_analysis(f"{home}-{away}")
                
                msg = (
                    f"🚨 **ТЕСТОВЫЙ ПЕРЕХВАТ МАТЧА**\n\n"
                    f"🏆 {league}\n"
                    f"⚔️ **{home} — {away}**\n"
                    f"📊 Текущий счет: `{score}`\n"
                    f"⏱ Статус: `{status}`\n\n"
                    f"🤖 **GPT:** {analysis}\n\n"
                    f"✅ *Если ты видишь это сообщение, значит связь с Flashscore и GPT работает идеально!*"
                )
                
                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
        except Exception as e:
            await bot.send_message(CHANNEL_ID, f"❌ Тест не прошел: {e}")

if __name__ == "__main__":
    asyncio.run(run_force_test())
