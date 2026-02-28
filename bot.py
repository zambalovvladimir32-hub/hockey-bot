import asyncio
import os
import logging
import sys
import time
from aiogram import Bot
from curl_cffi.requests import AsyncSession

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyGuard")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class UltimateParser:
    def __init__(self):
        self.url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-fsign": "SW9D1eZo",
            "x-requested-with": "XMLHttpRequest",
        }
        self.sent_matches = {}

    def extract_tag(self, block, tag):
        try: return block.split(tag)[1].split('¬')[0]
        except: return ""

    def validate_and_parse(self, block, league):
        # 1. Сбор сырых данных
        m_id = block.split('¬')[0]
        tt = self.extract_tag(block, 'TT÷').upper()   # Текст времени (P3, 15', Pause)
        ac = self.extract_tag(block, 'AC÷')           # Статус-код
        cr = self.extract_tag(block, 'CR÷')           # Текущий период (номер)
        
        # Счета
        full_h = self.extract_tag(block, 'AG÷') or "0"
        full_a = self.extract_tag(block, 'AH÷') or "0"
        s1 = self.extract_tag(block, 'XA÷') # Счет 1-го периода
        s2 = self.extract_tag(block, 'XB÷') # Счет 2-го периода
        s3 = self.extract_tag(block, 'XC÷') # Счет 3-го периода (ГЛАВНЫЙ ВРАГ)

        # --- МЕГА-ФИЛЬТР (БАН 3-ГО ПЕРИОДА И ОШИБОК) ---
        
        # Если есть намек на 3-й период — СРАЗУ УДАЛЯЕМ
        if s3 or "P3" in tt or "3-Й" in tt or ac in ['3', '46', '6'] or cr == '3':
            return None

        # Если 1-й период еще не закончился (нет счета XA) — ПРОПУСКАЕМ
        if not s1:
            return None

        # ПРОВЕРКА НА ПРАВИЛЬНОСТЬ СЧЕТА (Анти-Тохоку)
        # Суммируем голы из периодов и сравниваем с общим счетом
        try:
            h1, a1 = map(int, s1.split(':'))
            h2, a2 = map(int, s2.split(':')) if s2 else (0, 0)
            
            # Если сумма голов в периодах НЕ РАВНА общему счету — данные еще не обновились
            if (h1 + h2 != int(full_h)) or (a1 + a2 != int(full_a)):
                logger.info(f"⚠️ Рассинхрон счета в матче {m_id}. Ждем обновления...")
                return None
        except:
            return None # Битые данные

        # ОПРЕДЕЛЯЕМ СТАТУС (Перерыв или Игра)
        is_break = (ac == '45' or "ПЕРЕРЫВ" in tt or "PAUSE" in tt)
        
        home_name = self.extract_tag(block, 'AE÷')
        away_name = self.extract_tag(block, 'AF÷')

        status_text = "☕️ ПЕРЕРЫВ (1-2)" if is_break else f"⏱ 2-Й ПЕРИОД [{tt}]"
        
        return {
            'id': m_id,
            'key': f"{full_h}:{full_a}_{is_break}",
            'text': (
                f"🏒 **{home_name} {full_h}:{full_away} {away_name}**\n"
                f"🏆 {league}\n"
                f"{status_text}\n\n"
                f"📊 Счет по периодам:\n"
                f"└ 1-й: `{s1}`\n"
                f"└ 2-й: `{s2 if s2 else '0:0'}`"
            )
        }

    async def start(self):
        async with AsyncSession(impersonate="chrome110") as session:
            while True:
                try:
                    res = await session.get(f"{self.url}?t={int(time.time())}", headers=self.headers)
                    if res.status_code != 200: continue
                    
                    sections = res.text.split('~ZA÷')
                    for section in sections[1:]:
                        league = section.split('¬')[0]
                        blocks = section.split('~AA÷')
                        for b in blocks[1:]:
                            match = self.validate_and_parse(b, league)
                            if match:
                                m_id, key = match['id'], match['key']
                                if self.sent_matches.get(m_id) != key:
                                    await bot.send_message(CHANNEL_ID, match['text'], parse_mode="Markdown")
                                    self.sent_matches[m_id] = key
                                    logger.info(f"✅ Отправлено: {match['id']}")

                    if len(self.sent_matches) > 300: self.sent_matches.clear()
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                
                await asyncio.sleep(30)

if __name__ == "__main__":
    parser = UltimateParser()
    asyncio.run(parser.start())
