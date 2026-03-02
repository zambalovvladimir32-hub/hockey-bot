import asyncio, os, logging, re
from aiogram import Bot
from curl_cffi.requests import AsyncSession
from urllib.parse import quote

# Настройка логов для Railway
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("HockeyHybrid_v55.2")

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
bot = Bot(token=TOKEN)

class HockeyHybrid:
    def __init__(self):
        self.sent_cache = {}
        # Заголовки для обхода защиты Flashscore (401 error fix)
        self.flash_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "x-fsign": "SW9D1eZo", 
            "X-Referer": "https://www.flashscore.ru/",
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9"
        }
        self.sofa_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Origin": "https://www.sofascore.com",
            "Referer": "https://www.sofascore.com/"
        }

    async def fetch_flashscore(self, session):
        """Получаем список матчей с Flashscore напрямую"""
        url = "https://www.flashscore.ru/x/feed/f_4_0_3_ru-ru_1"
        try:
            r = await session.get(url, headers=self.flash_headers, impersonate="chrome110", timeout=25)
            if r.status_code == 200:
                return r.text
            logger.warning(f"⚠️ Flashscore статус: {r.status_code}")
            return None
        except Exception as e:
            logger.error(f"💥 Ошибка Flashscore: {e}")
            return None

    async def get_sofa_stats(self, session, h_name, a_name):
        """Ищем матч на SofaScore и забираем статику в JSON"""
        try:
            # 1. Поиск ID матча по названиям команд
            # Очищаем от (Rus), (W) и прочего мусора для точного поиска
            clean_h = re.sub(r'\(.*?\)', '', h_name).strip()
            clean_a = re.sub(r'\(.*?\)', '', a_name).strip()
            
            q = quote(f"{clean_h} {clean_a}")
            search_url = f"https://www.sofascore.com/api/v1/search/all?q={q}"
            
            r_search = await session.get(search_url, headers=self.sofa_headers, impersonate="chrome110")
            if r_search.status_code != 200: return None
            
            data = r_search.json()
            # Ищем именно хоккейное событие (event)
            event_id = None
            for res in data.get('results', []):
                if res.get('type') == 'event' and res.get('entity', {}).get('sport', {}).get('slug') == 'ice-hockey':
                    event_id = res['entity']['id']
                    break
            
            if not event_id:
                logger.warning(f"❓ Матч {clean_h} не найден на SofaScore")
                return None

            # 2. Получение статистики по найденному ID
            stat_url = f"https://www.sofascore.com/api/v1/event/{event_id}/statistics"
            r_stat = await session.get(stat_url, headers=self.sofa_headers, impersonate="chrome110")
            
            if r_stat.status_code == 200:
                s_data = r_stat.json()
                res = {"shots": 0, "pen": 0}
                # Ищем блок 'ALL' (статистика за все периоды)
                for period_data in s_data.get('statistics', []):
                    if period_data.get('period') == 'ALL':
                        for group in period_data.get('groups', []):
                            for item in group.get('statisticsItems', []):
                                if 'Shots on goal' in item['name']:
                                    res['shots'] = int(item['homeValue']) + int(item['awayValue'])
                                if 'Penalty minutes' in item['name']:
                                    res['pen'] = int(item['homeValue']) + int(item['awayValue'])
                return res
            return None
        except Exception as e:
            logger.debug(f"Sofa error: {e}")
            return None

    async def run(self):
        logger.info("🚀 ГИБРИД v55.2 ЗАПУЩЕН: Flashscore + SofaScore")
        async with AsyncSession() as session:
            while True:
                try:
                    data = await self.fetch_flashscore(session)
                    if data and "¬" in data:
                        # Фильтруем матчи со статусом 'Перерыв' (AC÷46)
                        matches = [m for m in data.split('~AA÷')[1:] if "AC÷46" in m]
                        logger.info(f"🔎 Нашел {len(matches)} игр в перерыве на Flashscore")

                        for m_block in matches:
                            m_id = m_block.split('¬')[0]
                            if m_id in self.sent_cache: continue

                            try:
                                h_score = int(m_block.split('AG÷')[1].split('¬')[0])
                                a_score = int(m_block.split('AH÷')[1].split('¬')[0])
                                
                                # Условие: не более 1 гола в сумме
                                if (h_score + a_score) <= 1:
                                    h_team = m_block.split('AE÷')[1].split('¬')[0]
                                    a_team = m_block.split('AF÷')[1].split('¬')[0]
                                    
                                    logger.info(f"📊 Запрос статистики для {h_team}...")
                                    stats = await self.get_sofa_stats(session, h_team, a_team)
                                    
                                    if stats:
                                        logger.info(f"📈 Данные: Броски {stats['shots']}, Штраф {stats['pen']}")
                                        # Твои условия: 11+ бросков или 4+ мин штрафа
                                        if stats['shots'] >= 11 or stats['pen'] >= 4:
                                            msg = (f"🏒 **{h_team} {h_score}:{a_score} {a_team}**\n"
                                                   f"🎯 Броски в створ: `{stats['shots']}`\n"
                                                   f"⚖️ Штрафное время: `{stats['pen']} мин`")
                                            await bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
                                            self.sent_cache[m_id] = True
                                            logger.info(f"✅ СИГНАЛ ОТПРАВЛЕН: {h_team}")
                            except: continue
                    
                    # Интервал проверки (180 секунд = 3 минуты)
                    await asyncio.sleep(180)
                except Exception as e:
                    logger.error(f"Ошибка цикла: {e}")
                    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(HockeyHybrid().run())
