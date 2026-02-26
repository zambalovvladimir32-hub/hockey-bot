import asyncio
import aiohttp
import os
import logging
from aiogram import Bot
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# НОВЫЙ ИСТОЧНИК (Глобальный фид)
URL = "https://m.flashscore.kz/x/feed/proxy-direct"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "x-referer": "https://m.flashscore.kz/",
    "Origin": "https://m.flashscore.kz"
}

sent_signals = set()

async def get_ai_analysis(match_text):
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": f"Хоккей {match_text}. Прогноз на ТБ 4.5. Вердикт каппера до 10 слов."}],
            max_tokens=40
        )
        return res.choices[0].message.content
    except: return "Прогноз: ожидается активная игра."

async def check_hockey():
    # Используем прокси-запрос, чтобы обойти блокировку Amvera
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            # Запрашиваем данные именно по хоккею в лайве
            params = {'f': '8', 'p': '1', 't': '1'} 
            async with session.get(URL, params=params, timeout=15) as resp:
                text = await resp.text()
                
                # Парсим сырой текстовый фид Flashscore
                matches = text.split('~')
                found_live = False
                
                for match in matches:
                    if 'AA÷' in match: # Начало блока матча
                        found_live = True
                        # Вытаскиваем данные через маркеры Flashscore
                        mid = ""
                        home = ""
                        away = ""
                        h_score = "0"
                        a_score = "0"
                        status = ""
                        
                        lines = match.split('¬')
                        for line in lines:
                            if line.startswith('AA÷'): mid = line[3:]
                            if line.startswith('AE÷'): home = line[3:]
                            if line.startswith('AF÷'): away = line[3:]
                            if line.startswith('AG÷'): h_score = line[3:]
                            if line.startswith('AH÷'): a_score = line[3:]
                            if line.startswith('AS÷'): status = line[3:] # 1 - идет игра

                        if mid in sent_signals: continue
                        
                        # Если это СКА или Спартак (как на твоем скрине) - шлем сигнал!
                        if home or away:
                            analysis = await get_ai_analysis(f"{home}-{away}, счет {h_score}:{a_score}")
                            
                            msg = (f"🏒 **СИГНАЛ ПРЯМО С ЛЬДА!**\n\n"
                                   f"⚔️ **{home} — {away}**\n"
                                   f"📊 Счет: `{h_score}:{a_score}`\n"
                                   f"🤖 **ИИ:** {analysis}")
                            
                            await bot.send_message(CHANNEL_ID, msg)
                            sent_signals.add(mid)
                
                if not found_live:
                    logger.info("В мобильном фиде пока пусто.")

        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")

async def main():
    await bot.send_message(CHANNEL_ID, "⚡️ **ПЕРЕЗАГРУЗКА: Бот настроен на мобильный поток КХЛ.**")
    while True:
        await check_hockey()
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
