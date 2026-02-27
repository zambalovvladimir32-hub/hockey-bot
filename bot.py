import os

import asyncio

import aiohttp

import logging

from aiogram import Bot

from apscheduler.schedulers.asyncio import AsyncIOScheduler



TOKEN = os.getenv("TELEGRAM_TOKEN")

CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=TOKEN)



async def parse_all_hockey_leagues():

    """ВСЕ хоккейные лиги live с Flashscore"""

    headers = {"x-fsign": "SW9D1eZo"}

    feeds = [

        "f_1_0_5_ru",  # Все лиги RU

        "f_1_0_5_en",  # Все лиги EN (НХЛ лучше видно)

    ]

    

    all_games = []

    for feed in feeds:

        url = f"https://d.flashscore.ru/x/feed/{feed}"

        async with aiohttp.ClientSession() as session:

            async with session.get(url, headers=headers) as resp:

                text = await resp.text()

        

        data = text.split('¬')

        for line in data:

            parts = line.split('|')

            if len(parts) > 10 and parts[2] == '1':  # LIVE

                league = parts[9] if len(parts) > 9 else "Хоккей"

                team1, team2 = parts[4], parts[5]

                score = f"{parts[7]}-{parts[8]}"

                minute = parts[1]

                

                all_games.append(f"🧊 {league}

{team1} {score} {team2} ({minute}')")

    

    return all_games[:15]  # Топ-15 со всех лиг



async def send_all_hockey():

    games = await parse_all_hockey_leagues()

    if games:

        msg = "🌍 LIVE ХОККЕЙ | ВСЕ ЛИГИ МИРА:



" + "



".join(games)

        await bot.send_message(CHANNEL_ID, msg)



async def main():

    scheduler = AsyncIOScheduler()

    scheduler.add_job(send_all_hockey, "interval", seconds=30)

    scheduler.start()

    print("🚀 Бот: ВСЕ хоккейные лиги каждые 30с")

    await asyncio.Event().wait()



asyncio.run(main())
