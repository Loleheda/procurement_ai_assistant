import time
import logging
from contextlib import contextmanager
from typing import List, Tuple, Optional

import streamlit as st

from Config import Config


class BenchmarkLogger:
    """
    Класс для логирования и измерения времени выполнения операций.
    Поддерживает как вывод в интерфейс Streamlit, так и запись в файл (опционально).
    """
    def __init__(self, log_to_file: bool = False, log_file: str = "benchmark.log"):
        """
        Инициализация логгера.

        Args:
            log_to_file: Записывать логи в файл
            log_file: Путь к файлу логов
        """
        self.log_to_file = log_to_file
        self.benchmarks: List[Tuple[str, float]] = []  # (операция, время_в_сек)

        if log_to_file:
            logging.basicConfig(
                filename=log_file,
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self.logger = logging.getLogger(__name__)

    @contextmanager
    def measure(self, operation_name: str):
        """
        Контекстный менеджер для замера времени выполнения блока кода.

        Args:
            operation_name: Название операции
        """
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            self.benchmarks.append((operation_name, elapsed))
            if self.log_to_file:
                self.logger.info(f"{operation_name} took {elapsed:.3f}s")

    def clear(self):
        """Очистить сохранённые бенчмарки."""
        self.benchmarks.clear()

    def display(self):
        """Отобразить все накопленные бенчмарки в Streamlit."""
        if not self.benchmarks:
            st.info("Нет данных о производительности.")
            return

        st.subheader("⏱️ Производительность операций")
        total_time = sum(t for _, t in self.benchmarks)
        data = {
            "Операция": [op for op, _ in self.benchmarks],
            "Время (с)": [f"{t:.3f}" for _, t in self.benchmarks],
            "Доля (%)": [f"{t/total_time*100:.1f}" for _, t in self.benchmarks]
        }
        st.dataframe(data, use_container_width=True)
        st.caption(f"**Общее время:** {total_time:.3f} с")

        if st.button("🗑️ Очистить логи"):
            self.clear()
            st.rerun()