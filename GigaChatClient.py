import re
import json
from typing import List, Dict, Any

# Для GigaChat API
from gigachat import GigaChat
import ssl
import certifi

# Для веб-интерфейса
import streamlit as st

from Config import Config


class GigaChatClient:
    """Клиент для работы с GigaChat API"""

    def __init__(self, credentials: str, scope: str = "GIGACHAT_API_PERS",
                 model: str = "GigaChat", verify_ssl: bool = False):
        """
        Инициализация клиента GigaChat

        Args:
            credentials: Ключ авторизации (Authorization Key)
            scope: Версия API
            model: Модель для использования
            verify_ssl: Проверять SSL сертификаты
        """
        self.credentials = credentials
        self.scope = scope
        self.model = model
        self.verify_ssl = verify_ssl
        self.client = None
        self._init_client()

    def _init_client(self):
        """Инициализация клиента с правильными SSL настройками"""
        try:
            # Настройка SSL контекста
            ssl_context = ssl.create_default_context()
            ssl_context.load_verify_locations(certifi.where())

            # Инициализация клиента GigaChat
            self.client = GigaChat(
                credentials=self.credentials,
                scope=self.scope,
                model=self.model,
                verify_ssl_certs=self.verify_ssl,
                timeout=Config.GIGACHAT_TIMEOUT
            )
        except Exception as e:
            st.error(f"❌ Ошибка инициализации GigaChat: {e}")
            raise

    def chat(self, messages: List[Dict], temperature: float = 0.1,
             functions: List[Dict] = None) -> Dict:
        """
        Отправка запроса к GigaChat

        Args:
            messages: Список сообщений [{"role": "user", "content": "текст"}]
            temperature: Температура генерации (0-1)
            functions: Описания функций для function calling

        Returns:
            Ответ от модели
        """
        try:
            # Формируем запрос
            chat_payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1000
            }

            # Отправляем запрос
            response = self.client.chat(chat_payload)

            # Преобразуем в удобный формат
            result = {
                "choices": [
                    {
                        "message": {
                            "content": response.choices[0].message.content,
                            "role": response.choices[0].message.role
                        },
                        "finish_reason": response.choices[0].finish_reason
                    }
                ]
            }

            return result

        except Exception as e:
            st.error(f"Ошибка при запросе к GigaChat: {e}")
            return {
                "choices": [
                    {
                        "message": {
                            "content": f"Ошибка: {str(e)}",
                            "role": "assistant"
                        }
                    }
                ]
            }

    def extract_offer_data(self, text: str) -> Dict[str, Any]:
        """
        Извлечение структурированных данных из коммерческого предложения

        Args:
            text: Текст документа

        Returns:
            Структурированные данные
        """
        # Формируем системный промпт
        system_message = """
        Ты - профессиональный ассистент отдела закупок. Извлеки структурированную информацию 
        из коммерческого предложения в формате JSON. Будь внимателен к деталям.
        """

        user_message = f"""
        Извлеки следующие данные из текста коммерческого предложения:

        Текст предложения:
        {text[:3000]}

        Необходимо извлечь в формате JSON:
        1. supplier_name - название компании-поставщика
        2. inn - ИНН поставщика (если есть)
        3. products - список товаров с полями: name, quantity, price_per_unit, total_price
        4. total_amount - общая сумма предложения (числом)
        5. delivery_terms - условия доставки
        6. payment_terms - условия оплаты
        7. validity_period - срок действия предложения
        8. contact_person - контактное лицо
        9. phone - телефон
        10. email - email
        11. key_advantages - ключевые преимущества (список строк)

        Верни ТОЛЬКО JSON без дополнительных пояснений.
        """

        try:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]

            response = self.chat(messages, temperature=0.1)
            content = response["choices"][0]["message"]["content"]

            # Очистка ответа
            content = re.sub(r'```json\n?', '', content)
            content = re.sub(r'\n?```', '', content)
            content = content.strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            st.error(f"Ошибка парсинга JSON: {e}")
            return {
                "supplier_name": "Ошибка распознавания",
                "products": [],
                "total_amount": 0,
                "error": f"JSON parse error: {e}"
            }
        except Exception as e:
            st.error(f"Ошибка извлечения данных: {e}")
            return {
                "supplier_name": "Ошибка",
                "products": [],
                "total_amount": 0,
                "error": str(e)
            }

    def compare_offers(self, offers: List[Dict]) -> Dict:
        """
        Сравнение нескольких коммерческих предложений

        Args:
            offers: Список предложений

        Returns:
            Результаты сравнения
        """
        if len(offers) < 2:
            return {"error": "Недостаточно предложений для сравнения"}

        # Подготавливаем данные для анализа
        offers_text = json.dumps(offers, ensure_ascii=False, indent=2)

        system_message = """
        Ты - аналитик отдела закупок с многолетним опытом. 
        Проанализируй коммерческие предложения и дай рекомендации.
        """

        user_message = f"""
        Сравни следующие коммерческие предложения:

        {offers_text}

        Предоставь подробный анализ в формате JSON со следующими полями:
        1. best_offer - индекс лучшего предложения (0, 1, 2...)
        2. best_offer_reason - причина, почему это предложение лучшее
        3. comparison_table - объект для сравнения по параметрам:
           - price_comparison (сравнение цен)
           - payment_terms_comparison (сравнение условий оплаты)
           - delivery_comparison (сравнение сроков доставки)
        4. recommendations - список рекомендаций для принятия решения
        5. risks - список рисков по каждому поставщику
        6. negotiation_points - на что обратить внимание при переговорах (список)
        7. estimated_savings - возможная экономия при выборе лучшего предложения

        Верни ТОЛЬКО JSON.
        """

        try:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]

            response = self.chat(messages, temperature=0.2)
            content = response["choices"][0]["message"]["content"]

            # Очистка ответа
            content = re.sub(r'```json\n?', '', content)
            content = re.sub(r'\n?```', '', content)

            return json.loads(content)

        except Exception as e:
            st.error(f"Ошибка при сравнении: {e}")
            return {"error": str(e)}

    def generate_response(self, offer: Dict, negotiation_points: List[str]) -> str:
        """
        Генерация проекта ответа поставщику

        Args:
            offer: Данные предложения
            negotiation_points: Моменты для обсуждения

        Returns:
            Текст письма
        """
        system_message = """
        Ты - профессиональный менеджер отдела закупок крупной компании.
        Составляй деловые письма вежливо, четко и по существу.
        """

        user_message = f"""
        Составь проект ответа на коммерческое предложение.

        Данные поставщика:
        {json.dumps(offer, ensure_ascii=False, indent=2)}

        Моменты для обсуждения:
        {', '.join(negotiation_points)}

        Напиши письмо на русском языке, включив:
        1. Вежливое обращение к поставщику
        2. Благодарность за предоставленное предложение
        3. Конкретные вопросы по моментам для обсуждения
        4. Предложение по дальнейшим шагам (встреча, звонок, уточнение)

        Письмо должно быть деловым, но дружелюбным, с уважением к партнеру.
        """

        try:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]

            response = self.chat(messages, temperature=0.7)
            return response["choices"][0]["message"]["content"]

        except Exception as e:
            return f"Ошибка при генерации ответа: {e}"