# ВРЕМЕННЫЙ ТЕСТ: присылать всё из наших лиг
if l_id in ALLOWED_LEAGUES:
    teams = f"{game['teams']['home']['name']} — {game['teams']['away']['name']}"
    logger.info(f"ТЕСТ: Вижу матч {teams}")
    # ... тут отправка сообщения
