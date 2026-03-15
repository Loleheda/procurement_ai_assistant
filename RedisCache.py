import json
import hashlib
import logging
from typing import Any, Optional

import redis
import streamlit as st

from Config import Config


class RedisCache:
    """
    Класс для работы с Redis как кэшем.
    Поддерживает установку/получение значений с TTL и логирование.
    """

    def __init__(self):
        """
        Инициализация подключения к Redis.
        """
        self.client = None

        # Настройка файлового логгера для текстовых записей
        self.file_logger = logging.getLogger(__name__)
        if not self.file_logger.handlers:
            handler = logging.FileHandler(filename=Config.REDIS_LOG_FILE)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.file_logger.addHandler(handler)
            self.file_logger.setLevel(logging.INFO)

        self._connect()

    def _connect(self):
        """Подключение к Redis с обработкой ошибок и логированием."""
        try:
            self.client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                password=Config.REDIS_PASSWORD,
                decode_responses=False
            )
            self.client.ping()

            st.sidebar.success("✅ Redis подключён")
            self.file_logger.info("Подключение к Redis успешно")
        except Exception as e:
            st.sidebar.error(f"❌ Ошибка подключения к Redis: {e}")
            self.file_logger.error(f"Ошибка подключения к Redis: {e}")
            self.client = None

    def _make_key(self, data: Any) -> str:
        """
        Создаёт хеш ключа из переданных данных.
        Используем SHA256 для уникальности.
        """
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def get(self, key_data: Any) -> Optional[bytes]:
        """
        Получить значение из кэша по данным ключа.
        Возвращает None если ключа нет или произошла ошибка.
        """
        if not self.client:
            self.file_logger.warning("Попытка чтения из кэша при отсутствии подключения")
            return None
        try:
            key = self._make_key(key_data)
            self.file_logger.info("Redis GET")
            value = self.client.get(key)

            if value is not None:
                self.file_logger.info(f"Кэш GET: ключ {key} найден")
            else:
                self.file_logger.info(f"Кэш GET: ключ {key} не найден")
            return value
        except Exception as e:
            self.file_logger.error(f"Ошибка при чтении из Redis: {e}")
            st.warning(f"⚠️ Ошибка при чтении из Redis: {e}")
            return None

    def set(self, key_data: Any, value: Any, ttl: int = Config.REDIS_TTL) -> bool:
        """
        Сохранить значение в кэш с TTL.
        Возвращает True при успехе.
        """
        if not self.client:
            self.file_logger.warning("Попытка записи в кэш при отсутствии подключения")
            return False
        try:
            key = self._make_key(key_data)

            # Сериализуем значение в JSON, если это не байты
            if isinstance(value, (dict, list, tuple, str, int, float, bool)):
                value_bytes = json.dumps(value, ensure_ascii=False).encode('utf-8')
            elif not isinstance(value, bytes):
                value_bytes = str(value).encode('utf-8')
            else:
                value_bytes = value

            self.file_logger.info("Redis SET")
            result = self.client.setex(key, ttl, value_bytes)

            if result:
                self.file_logger.info(f"Кэш SET: ключ {key} сохранён (TTL={ttl})")
            else:
                self.file_logger.warning(f"Кэш SET: не удалось сохранить ключ {key}")
            return result
        except Exception as e:
            self.file_logger.error(f"Ошибка при записи в Redis: {e}")
            st.warning(f"⚠️ Ошибка при записи в Redis: {e}")
            return False

    def clear(self):
        """Очистить весь кэш."""
        if not self.client:
            self.file_logger.warning("Попытка очистки кэша при отсутствии подключения")
            return
        try:
            self.file_logger.info("Redis FLUSHDB")
            self.client.flushdb()
            self.file_logger.info("Кэш Redis полностью очищен")
            st.success("✅ Кэш Redis очищен")
        except Exception as e:
            self.file_logger.error(f"Ошибка при очистке кэша: {e}")
            st.error(f"❌ Ошибка при очистке кэша: {e}")

    def is_connected(self) -> bool:
        """Проверка соединения с Redis."""
        return self.client is not None