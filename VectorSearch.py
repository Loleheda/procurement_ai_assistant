import os
from typing import List, Dict
import pickle

# Для веб-интерфейса
import streamlit as st

# Для векторного поиска
from sentence_transformers import SentenceTransformer
import faiss


class VectorSearch:
    """Класс для семантического поиска по предложениям"""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Инициализация поиска

        Args:
            model_name: Название модели для эмбеддингов
        """
        self.model_name = model_name
        self.model = None
        self.index = None
        self.documents = []
        self.metadata = []

    def _load_model(self):
        """Ленивая загрузка модели"""
        if self.model is None:
            with st.spinner("Загрузка модели эмбеддингов..."):
                self.model = SentenceTransformer(self.model_name)

    def create_index(self, documents: List[str], metadata: List[Dict]):
        """Создание векторного индекса"""
        self._load_model()

        self.documents = documents
        self.metadata = metadata

        if not documents:
            return

        # Создаем эмбеддинги
        embeddings = self.model.encode(documents, show_progress_bar=True)

        # Создаем FAISS индекс
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Используем inner product для косинусной близости

        # Нормализуем для косинусной близости
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype('float32'))

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """Поиск похожих документов"""
        if self.index is None or not self.documents:
            return []

        self._load_model()

        # Создаем эмбеддинг запроса и нормализуем
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)

        # Поиск
        scores, indices = self.index.search(query_embedding.astype('float32'), min(k, len(self.documents)))

        # Формируем результаты
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):
                results.append({
                    'document': self.documents[idx][:300] + "...",
                    'metadata': self.metadata[idx],
                    'similarity': float(scores[0][i])
                })

        return results

    def save(self, path: str):
        """Сохранение индекса"""
        data = {
            'documents': self.documents,
            'metadata': self.metadata,
            'model_name': self.model_name
        }

        # Сохраняем индекс отдельно, если он есть
        if self.index:
            faiss.write_index(self.index, path + ".faiss")

        # Сохраняем метаданные
        with open(path + ".meta", 'wb') as f:
            pickle.dump(data, f)

    def load(self, path: str):
        """Загрузка индекса"""
        meta_path = path + ".meta"
        index_path = path + ".faiss"

        if os.path.exists(meta_path):
            with open(meta_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.metadata = data['metadata']
                self.model_name = data['model_name']

        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
