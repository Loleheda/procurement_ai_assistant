import os

# Для веб-интерфейса
import streamlit as st

# Для работы с PDF и Excel
import PyPDF2
from docx import Document


class DocumentParser:
    """Класс для парсинга различных типов документов"""

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """Извлечение текста из PDF"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            st.error(f"Ошибка при парсинге PDF: {e}")
        return text

    @staticmethod
    def parse_docx(file_path: str) -> str:
        """Извлечение текста из DOCX"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text += paragraph.text + "\n"
        except Exception as e:
            st.error(f"Ошибка при парсинге DOCX: {e}")
        return text

    @staticmethod
    def parse_txt(file_path: str) -> str:
        """Извлечение текста из TXT"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='cp1251') as file:
                    return file.read()
            except Exception as e:
                st.error(f"Ошибка при парсинге TXT: {e}")
                return ""

    def parse_document(self, file_path: str) -> str:
        """Универсальный метод парсинга"""
        ext = os.path.splitext(file_path)[1].lower()

        parsers = {
            '.pdf': self.parse_pdf,
            '.docx': self.parse_docx,
            '.doc': self.parse_docx,
            '.txt': self.parse_txt,
            '.csv': self.parse_txt
        }

        if ext in parsers:
            return parsers[ext](file_path)
        else:
            return f"Неподдерживаемый формат файла: {ext}"
