import os



class Config:
    """Конфигурация приложения"""
    # Настройки GigaChat
    GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")
    GIGACHAT_SCOPE = ""
    GIGACHAT_MODEL = "GigaChat"  # Можно также использовать "GigaChat", "GigaChat-Max"
    GIGACHAT_TIMEOUT = 60

    # Настройки почты (замените на свои)
    EMAIL_HOST = "imap.yandex.ru"
    EMAIL_PORT = 993
    EMAIL_USER = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

    # Пути к файлам
    UPLOAD_FOLDER = "uploads"
    VECTOR_DB_PATH = "vector\\vector_db_gigachat.pkl"
    OFFERS_DB_PATH = "offers\\offers_db_gigachat.json"

    VERIFY_SSL_CERTS = False

    # Настройки GPU
    USE_GPU = True
    GPU_DEVICE = 0

    # Настройки логирования
    ENABLE_BENCHMARK = True
    BENCHMARK_LOG_FILE = "logs\\benchmark.log"

    # Настройки Redis (для него отдельное логирование, так как его лог необходим всегда при работе программы)
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    REDIS_TTL = 3600  # Время жизни кэша в секундах (1 час)
    REDIS_LOG_FILE="logs\\redis_log.txt"