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
    EMAIL_USER = ""
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

    # Пути к файлам
    UPLOAD_FOLDER = "uploads"
    VECTOR_DB_PATH = "vector\\vector_db_gigachat.pkl"
    OFFERS_DB_PATH = "offers\\offers_db_gigachat.json"

    VERIFY_SSL_CERTS = False

    # Настройки GPU
    USE_GPU = True
    GPU_DEVICE = 0