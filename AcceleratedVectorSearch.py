from __future__ import annotations

import os
import pickle
from typing import Any

import streamlit as st
import torch
import faiss
from sentence_transformers import SentenceTransformer

from Config import Config


class AcceleratedVectorSearch:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.use_gpu = Config.USE_GPU and torch.cuda.is_available()
        self.model: SentenceTransformer | None = None
        self.index: faiss.Index | None = None
        self.documents: list[str] = []
        self.metadata: list[dict[str, Any]] = []
        self.embeddings_cache: dict[str, Any] = {}

    def _load_model(self):
        if self.model is None:
            with st.spinner("Загрузка модели эмбеддингов..."):
                self.model = SentenceTransformer(self.model_name)
                if self.use_gpu:
                    self.model = self.model.to('cuda')
                    st.info("✅ Модель эмбеддингов загружена на GPU")
                else:
                    st.info("✅ Модель эмбеддингов загружена на CPU")

    def create_index(self, documents: list[str], metadata: list[dict[str, Any]]):
        self._load_model()
        self.documents = documents
        self.metadata = metadata

        if not documents:
            return

        embeddings = self.model.encode(documents, show_progress_bar=True)
        faiss.normalize_L2(embeddings)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings.astype('float32'))

        for doc, emb in zip(documents, embeddings):
            self.embeddings_cache[doc] = emb

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        if self.index is None or not self.documents:
            return []

        self._load_model()
        query_emb = self.model.encode([query])
        faiss.normalize_L2(query_emb)
        scores, indices = self.index.search(query_emb.astype('float32'), min(k, len(self.documents)))

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
        data = {
            'documents': self.documents,
            'metadata': self.metadata,
            'model_name': self.model_name,
            'embeddings_cache': self.embeddings_cache
        }
        if self.index:
            faiss.write_index(self.index, path + ".faiss")
        with open(path + ".meta", 'wb') as f:
            pickle.dump(data, f)

    def load(self, path: str):
        meta_path = path + ".meta"
        index_path = path + ".faiss"
        if os.path.exists(meta_path):
            with open(meta_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.metadata = data['metadata']
                self.model_name = data['model_name']
                self.embeddings_cache = data.get('embeddings_cache', {})
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)