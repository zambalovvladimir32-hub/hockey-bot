import asyncio
import aiohttp
import os
import logging
from aiogram import Bot
from openai import AsyncOpenAI

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=TOKEN)
gpt_client = AsyncOpenAI(api_key=OPENAI_KEY)

# Прямой технический адрес Flashscore (Livescore Core)
# Этот адрес Amvera пропускает без ошибок DNS
HOCKEY_SOURCE = "https://prod-public-api.livescore.com/v1/api/app/live/hockey/8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Origin": "https://www.flashscorekz.com",
    "Referer": "https://www.flashscorekz.com/"
}

# Чтобы не слать дубли
sent_signals = set()

async def get_ai_analysis(teams, score, status):
    prompt = f"Хоккей. {status}. {teams}. Счет {score}. Оцени вероятность ТБ 4.5. Вердикт до 15 слов."
    try:
        res = await gpt_client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": prompt}], max_tokens=80
        )
        return res.choices[0].message.content
    except: return "Анализирую статистику матча..."

async def check_live():
    # Создаем сессию внутри функции, чтобы избежать ошибки "Unclosed client session"
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        try:
            async with session.get(HOCKEY_SOURCE, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"Источник Flashscore ответил: {resp.status}")
                    return
                
                data = await resp.json()
                stages = data.get('Stages', [])
                
                for stage in stages:
                    league = stage.get('Snm', '').upper()
                    
                    # Фильтр лиг (те самые из скриншота: КХЛ, ВХЛ, Казахстан и т.д.)
                    target_keywords = ['RUSSIA', 'KHL', 'VHL', 'MHL', 'KAZAKHSTAN', 'CHAMPIONSHIP', 'BELARUS']
                    
                    if any(key in league for key in target_keywords):
                        for event in stage.get('Events', []):
                            eid = event.get('Eid')
                            if eid in sent_signals: continue

                            home = event.get('T1', [{}])[0].get('Nm', 'Home')
                            away = event.get('T2', [{}])[0].get('Nm', 'Away')
                            
                            # Счет и время
                            h_score = int(event.get('Tr1', 0))
                            a_score = int(event.get('Tr2', 0))
                            total = h_score + a_score
                            status = event.get('Eps', '').upper() # Период (1st, 2nd, Перерыв)

                            # УСЛОВИЯ СИГНАЛА
                            # 1. Первый период (1ST) и до 3 шайб
                            is_p1 = '1ST' in status or '1-Й' in status
                            # 2. Второй период (2ND) и счет 0:0
                            is_p2_zero = ('2ND' in status or '2-Й' in status) and total == 0

                            if (is_p1 and total <= 3) or is_p2_zero:
                                teams = f"{home} — {away}"
                                analysis = await get_ai_analysis(teams, f"{h_score}:{a_score}", status)
                                
                                msg = (
                                    f"🏒 **СИГНАЛ: FLASHSCORE KZ**\n\n"
                                    f"🏆 {league}\n"
                                    f"⚔️ **{teams}**\n"
                                    f"📊 Счет: `{h_score}:{a_score}`\n"
                                    f"⏱ Статус: `{status}`\n\n"
                                    f"🤖 **ИИ Анализ:** {analysis}"
                                )
                                await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                sent_signals.add(eid)
                                logger.info(f"Сигнал отправлен: {teams}")

        except Exception as e:
            logger.error(f"Ошибка в цикле: {e}")

async def main():
    logger.info("Бот запущен. Синхронизация с Flashscore KZ...")
    # Разовое приветствие в канал
    try:
        await bot.send_message(CHANNEL_ID, "🚀 **Бот в эфире!** Мониторинг Flashscore KZ (КХЛ, ВХЛ, Казахстан) запущен.")
    except: pass

    while True:
        await check_live()
        # Проверка каждые 2 минуты
        await asyncio.sleep(120)

if __name__ == "__main__":
    asyncio.run(main())
