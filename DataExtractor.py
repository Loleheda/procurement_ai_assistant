import openai
import re
import json
from typing import List, Dict, Any


class DataExtractor:
    """Класс для извлечения структурированных данных из текста с помощью AI"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key

    def extract_offer_data(self, text: str) -> Dict[str, Any]:
        """Извлечение ключевой информации из коммерческого предложения"""

        prompt = f"""
        Ты - AI ассистент для отдела закупок. Извлеки структурированную информацию из коммерческого предложения.
        
        Текст предложения:
        {text[:3000]}  # Ограничиваем длину для API
        
        Извлеки следующие данные в формате JSON:
        1. supplier_name - название компании-поставщика
        2. inn - ИНН поставщика (если есть)
        3. products - список товаров с полями: name, quantity, price_per_unit, total_price
        4. total_amount - общая сумма предложения
        5. delivery_terms - условия доставки
        6. payment_terms - условия оплаты
        7. validity_period - срок действия предложения
        8. contact_person - контактное лицо
        9. phone - телефон
        10. email - email
        11. key_advantages - ключевые преимущества (список)
        
        Верни ТОЛЬКО JSON без дополнительного текста.
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты - помощник для извлечения структурированных данных. Отвечай только JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            result = response.choices[0].message.content

            # Очистка ответа от возможных markdown-оберток
            result = re.sub(r'```json\n?', '', result)
            result = re.sub(r'\n?```', '', result)

            return json.loads(result)

        except Exception as e:
            print(f"Ошибка при извлечении данных: {e}")
            return {
                "supplier_name": "Ошибка распознавания",
                "products": [],
                "total_amount": 0,
                "error": str(e)
            }

    def compare_offers(self, offers: List[Dict]) -> Dict:
        """Сравнение нескольких предложений"""

        # Создаем промпт для сравнения
        offers_text = json.dumps(offers, ensure_ascii=False, indent=2)

        prompt = f"""
        Ты - аналитик отдела закупок. Сравни следующие коммерческие предложения:
        
        {offers_text}
        
        Предоставь анализ в формате JSON:
        1. best_offer - индекс лучшего предложения (0, 1, 2...)
        2. comparison_table - таблица сравнения по параметрам: цена, условия оплаты, сроки доставки
        3. recommendations - список рекомендаций
        4. risks - список рисков по каждому поставщику
        5. negotiation_points - на что обратить внимание при переговорах
        
        Верни ТОЛЬКО JSON.
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты - аналитик закупок. Отвечай только JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )

            result = response.choices[0].message.content
            result = re.sub(r'```json\n?', '', result)
            result = re.sub(r'\n?```', '', result)

            return json.loads(result)

        except Exception as e:
            print(f"Ошибка при сравнении: {e}")
            return {"error": str(e)}

    def generate_response(self, offer: Dict, negotiation_points: List[str]) -> str:
        """Генерация проекта ответа поставщику"""

        prompt = f"""
        Ты - менеджер отдела закупок. Составь профессиональный ответ на коммерческое предложение.
        
        Данные поставщика:
        {json.dumps(offer, ensure_ascii=False, indent=2)}
        
        Моменты для обсуждения:
        {', '.join(negotiation_points)}
        
        Напиши проект письма на русском языке с:
        1. Вежливым обращением
        2. Подтверждением получения предложения
        3. Вопросами по моментам для обсуждения
        4. Предложением дальнейших шагов
        
        Письмо должно быть деловым, но дружелюбным.
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты - профессиональный менеджер по закупкам."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Ошибка при генерации ответа: {e}"
