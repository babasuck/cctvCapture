import logging

# Создаем логгер
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Устанавливаем общий уровень логгера

# Handler для DEBUG
debug_handler = logging.FileHandler("logs_debug.log", mode="a")
debug_handler.setLevel(logging.DEBUG)  # Уровень для debug-handler

# Handler для ERROR
error_handler = logging.FileHandler("logs_error.log", mode="a")
error_handler.setLevel(logging.ERROR)  # Уровень для error-handler

# Форматтер
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

# Добавляем форматтеры в handlers
debug_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)

# Добавляем handlers в логгер
logger.addHandler(debug_handler)
logger.addHandler(error_handler)

# Пример логов
logger.debug("This is a debug message.")
logger.error("This is an error message.")
