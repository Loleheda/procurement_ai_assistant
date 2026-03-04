import os
import json
import uuid

import pandas as pd
from datetime import datetime
from typing import List, Dict

# Для веб-интерфейса
import streamlit as st

from Config import Config
from DocumentParser import DocumentParser
from EmailProcessor import EmailProcessor
from GigaChatClient import GigaChatClient
from VectorSearch import VectorSearch


def init_session_state():
    """Инициализация состояния сессии"""
    if 'gigachat_client' not in st.session_state:
        st.session_state.gigachat_client = None
    if 'offers' not in st.session_state:
        st.session_state.offers = load_offers()
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Главная"
    if 'comparison_result' not in st.session_state:
        st.session_state.comparison_result = None


def load_offers() -> List[Dict]:
    """Загрузка предложений из файла"""
    if os.path.exists(Config.OFFERS_DB_PATH):
        try:
            with open(Config.OFFERS_DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_offers(offers: List[Dict]):
    """Сохранение предложений в файл"""
    # Загружаем существующие
    existing = load_offers()
    existing.extend(offers)

    # Сохраняем
    with open(Config.OFFERS_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    # Обновляем состояние
    st.session_state.offers = existing


def create_search_index():
    """Создание поискового индекса"""
    offers = st.session_state.offers

    if not offers:
        st.warning("Нет предложений для индексации")
        return

    documents = []
    metadata = []

    for offer in offers:
        # Создаем текст для индексации
        products_text = ""
        if offer.get('products'):
            products_text = "Товары: " + ", ".join([
                f"{p.get('name', '')}"
                for p in offer.get('products', [])[:5]
            ])

        advantages_text = ""
        if offer.get('key_advantages'):
            advantages_text = "Преимущества: " + ", ".join(offer.get('key_advantages', []))

        doc_text = f"""
        Поставщик: {offer.get('supplier_name', '')}
        {products_text}
        Сумма: {offer.get('total_amount', '')} руб.
        Условия доставки: {offer.get('delivery_terms', '')}
        Условия оплаты: {offer.get('payment_terms', '')}
        {advantages_text}
        Контакты: {offer.get('contact_person', '')} {offer.get('phone', '')} {offer.get('email', '')}
        """.strip()

        documents.append(doc_text)
        metadata.append(offer)

    # Создаем индекс
    searcher = VectorSearch()
    with st.spinner("Создание поискового индекса..."):
        searcher.create_index(documents, metadata)
        searcher.save(Config.VECTOR_DB_PATH)

    st.success(f"✅ Индекс создан для {len(documents)} документов")


def show_email_instructions():
    """Показывает инструкцию по настройке почты"""
    with st.expander("📧 Как настроить Яндекс Почту", expanded=False):
        st.markdown("""
        ### 🔧 Настройка Яндекс Почты для приложения
        
        #### Шаг 1: Включите IMAP
        1. Зайдите в [Яндекс Почту](https://mail.yandex.ru)
        2. Нажмите на шестеренку ⚙️ → **Все настройки**
        3. Перейдите в раздел **"Почтовые программы"**
        4. Включите опцию:  
           ✅ **"С сервера imap.yandex.ru по протоколу IMAP"**
        5. Нажмите **"Сохранить изменения"**
        
        #### Шаг 2: Создайте пароль приложения
        1. Перейдите на страницу [Пароли приложений](https://id.yandex.ru/security/app-passwords)
        2. Нажмите **"Создать новый пароль"**
        3. Выберите тип: **"Почта"**
        4. Название: **"Procurement AI Assistant"**
        5. Нажмите **"Далее"**
        6. **Скопируйте 16-значный пароль** (он показывается только один раз!)
        
        #### Шаг 3: Используйте в приложении
        - **Сервер:** `imap.yandex.ru`
        - **Порт:** `993`
        - **Email:** ваш полный email (example@yandex.ru)
        - **Пароль:** скопированный 16-значный пароль приложения
        
        > ⚠️ **Важно**: Используйте именно пароль приложения, а не пароль от почты!
        """)


def main():
    """Главная функция приложения"""

    # Настройка страницы
    st.set_page_config(
        page_title="Procurement AI Assistant (GigaChat)",
        page_icon="🤖",
        layout="wide"
    )

    # Инициализация состояния
    init_session_state()

    # Заголовок
    st.title("🤖 Procurement AI Assistant")
    st.markdown("### Интеллектуальный помощник отдела закупок на базе GigaChat")

    # Боковая панель с настройками
    with st.sidebar:
        st.header("⚙️ Настройки")

        # Ввод ключа GigaChat
        st.subheader("🔑 Авторизация GigaChat")

        auth_method = st.radio(
            "Способ авторизации",
            ["Ключ авторизации", "Токен доступа (опционально)"]
        )

        gigachat_key = st.text_input(
            "Ключ авторизации GigaChat",
            type="password",
            help="Получите ключ в личном кабинете Studio (developers.sber.ru)"
        )

        scope = st.selectbox(
            "Версия API",
            ["GIGACHAT_API_PERS", "GIGACHAT_API_B2B", "GIGACHAT_API_CORP"],
            index=0,
            help="B2B - для юрлиц с предоплатой, CORP - постоплата, PERS - для физлиц"
        )

        if st.button("🔌 Подключиться", type="primary"):
            if gigachat_key:
                try:
                    st.session_state.gigachat_client = GigaChatClient(
                        credentials=gigachat_key,
                        scope=scope,
                        verify_ssl=Config.VERIFY_SSL_CERTS
                    )
                    st.success("✅ Подключено к GigaChat!")
                except Exception as e:
                    st.error(f"Ошибка подключения: {e}")
            else:
                st.warning("Введите ключ авторизации")

        st.divider()

        # Загрузка файлов
        st.header("📎 Загрузка предложений")
        uploaded_files = st.file_uploader(
            "Загрузите коммерческие предложения",
            type=['pdf', 'docx', 'txt', 'csv'],
            accept_multiple_files=True
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Обработать", use_container_width=True):
                if not st.session_state.gigachat_client:
                    st.error("Сначала подключитесь к GigaChat")
                elif not uploaded_files:
                    st.warning("Нет файлов для обработки")
                else:
                    process_uploaded_files(uploaded_files)

        with col2:
            if st.button("🔍 Создать индекс", use_container_width=True):
                create_search_index()

        st.divider()

        # Проверка почты
        st.header("📧 Почта")
        if st.button("📨 Проверить новые письма", use_container_width=True):
            if not st.session_state.gigachat_client:
                st.error("Сначала подключитесь к GigaChat")
            else:
                check_email()

        # Добавляем инструкцию
        show_email_instructions()

        st.divider()

        # Статистика
        st.header("📊 Статистика")
        st.metric("Всего предложений", len(st.session_state.offers))

        if st.session_state.offers:
            total_sum = sum(o.get('total_amount', 0) or 0 for o in st.session_state.offers)
            suppliers = set(o.get('supplier_name', 'Неизвестно') for o in st.session_state.offers)
            st.metric("Общая сумма", f"{total_sum:,.0f} ₽")
            st.metric("Поставщиков", len(suppliers))

    # Основной контент
    if not st.session_state.gigachat_client:
        st.info("👈 Начните с подключения к GigaChat в боковой панели")

        with st.expander("📖 Как получить ключ GigaChat"):
            st.markdown("""
            1. Перейдите на [developers.sber.ru](https://developers.sber.ru)
            2. Создайте проект **GigaChat API**
            3. В разделе **Настройки API** нажмите **Получить ключ**
            4. Скопируйте ключ авторизации
            5. Вставьте ключ в поле выше
            
            **Важно:** Ключ отображается только один раз!
            """)

        return

    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Все предложения",
        "🤝 Сравнение",
        "✍️ Генерация ответов",
        "🔍 Поиск"
    ])

    with tab1:
        show_offers_tab()

    with tab2:
        show_comparison_tab()

    with tab3:
        show_response_tab()

    with tab4:
        show_search_tab()


def process_uploaded_files(files):
    """Обработка загруженных файлов"""
    parser = DocumentParser()
    client = st.session_state.gigachat_client

    progress_bar = st.progress(0)
    status_text = st.empty()

    processed_offers = []

    for i, file in enumerate(files):
        status_text.text(f"Обработка {file.name}...")

        # Сохраняем временный файл
        temp_path = f"temp_{file.name}"
        with open(temp_path, 'wb') as f:
            f.write(file.getvalue())

        # Парсим документ
        text = parser.parse_document(temp_path)

        if text and len(text.strip()) > 50:
            # Извлекаем данные через GigaChat
            offer_data = client.extract_offer_data(text)
            offer_data['filename'] = file.name
            offer_data['date'] = datetime.now().strftime("%Y-%m-%d %H:%M")
            offer_data['source'] = 'upload'
            processed_offers.append(offer_data)

        # Удаляем временный файл
        os.remove(temp_path)

        # Обновляем прогресс
        progress_bar.progress((i + 1) / len(files))

    status_text.text("Сохранение результатов...")

    if processed_offers:
        save_offers(processed_offers)
        st.success(f"✅ Успешно обработано {len(processed_offers)} файлов!")

        # Показываем результаты
        for offer in processed_offers:
            with st.expander(f"📄 {offer.get('filename', '')} - {offer.get('supplier_name', 'Неизвестно')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Поставщик:**", offer.get('supplier_name'))
                    st.write("**Сумма:**", f"{offer.get('total_amount', 0):,} ₽")
                    st.write("**Контакт:**", offer.get('contact_person'))
                with col2:
                    st.write("**Телефон:**", offer.get('phone'))
                    st.write("**Email:**", offer.get('email'))

                if offer.get('products'):
                    st.write("**Товары:**")
                    df = pd.DataFrame(offer['products'])
                    st.dataframe(df, use_container_width=True)
    else:
        st.warning("Не удалось извлечь данные из файлов")


def check_email():
    """Проверка почты с обработкой вложений"""

    # Получаем настройки из Config или из пользовательского ввода
    with st.expander("📧 Настройки почты", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            email_host = st.text_input(
                "IMAP сервер",
                value=Config.EMAIL_HOST,
                help="imap.yandex.ru для Яндекс, imap.mail.ru для Mail.ru",
                key="email_host_input"
            )
            email_user = st.text_input(
                "Email",
                value=Config.EMAIL_USER,
                help="Полный адрес электронной почты",
                key="email_user_input"
            )

        with col2:
            email_port = st.number_input(
                "Порт",
                value=Config.EMAIL_PORT,
                help="Обычно 993 для SSL",
                key="email_port_input",
                min_value=1,
                max_value=65535
            )
            email_password = st.text_input(
                "Пароль приложения",
                type="password",
                value=Config.EMAIL_PASSWORD,
                help="Не основной пароль, а пароль приложения!",
                key="email_password_input"
            )

        st.info("""
        **Как получить пароль приложения для Яндекс:**
        1. Включите IMAP в настройках почты: https://mail.yandex.ru/?dpda
        2. Перейдите на https://id.yandex.ru/security/app-passwords
        3. Создайте новый пароль для приложения "Почта"
        4. Скопируйте 16-значный пароль
        """)

    if not email_password:
        st.warning("Введите пароль приложения")
        return

    # Проверяем подключение
    if st.button("📨 Проверить почту", key="check_email_btn"):
        with st.spinner("Подключение к почтовому серверу..."):

            # Создаем обработчик почты
            processor = EmailProcessor(
                host=email_host,
                port=int(email_port),
                user=email_user,
                password=email_password
            )

            # Получаем письма
            emails = processor.get_unread_emails(5)

            if not emails:
                st.info("📭 Новых писем с вложениями не найдено")
                return

            st.success(f"✅ Найдено писем: {len(emails)}")

            # Обрабатываем каждое письмо
            parser = DocumentParser()
            client = st.session_state.gigachat_client

            for email_data in emails:
                with st.expander(f"📧 {email_data['subject']}"):
                    st.write(f"**От:** {email_data['from']}")
                    st.write(f"**Дата:** {email_data['date']}")

                    if email_data['body']:
                        st.write("**Текст письма:**")
                        st.text(email_data['body'][:200] + "..." if len(email_data['body']) > 200 else email_data['body'])

                    if email_data['attachments']:
                        st.write("**Вложения:**")

                        for attachment in email_data['attachments']:
                            col1, col2 = st.columns([3, 1])

                            with col1:
                                st.write(f"📎 {attachment['filename']}")

                            with col2:
                                if st.button(f"Обработать", key=f"process_{attachment['filename']}"):
                                    with st.spinner(f"Обработка {attachment['filename']}..."):
                                        # Сохраняем временный файл
                                        temp_path = f"temp_{uuid.uuid4()}_{attachment['filename']}"
                                        with open(temp_path, 'wb') as f:
                                            f.write(attachment['data'])

                                        # Парсим документ
                                        text = parser.parse_document(temp_path)

                                        if text and len(text.strip()) > 50:
                                            # Анализируем через GigaChat
                                            offer_data = client.extract_offer_data(text)
                                            offer_data['filename'] = attachment['filename']
                                            offer_data['source'] = 'email'
                                            offer_data['from'] = email_data['from']
                                            offer_data['date'] = datetime.now().strftime("%Y-%m-%d %H:%M")

                                            st.json(offer_data)

                                            # Сохраняем в базу
                                            save_offers([offer_data])
                                            st.success(f"✅ Предложение сохранено")

                                        # Удаляем временный файл
                                        os.remove(temp_path)
                    else:
                        st.info("Нет вложений для обработки")

def show_offers_tab():
    """Отображение всех предложений"""
    offers = st.session_state.offers

    if not offers:
        st.info("📭 Нет загруженных предложений")
        return

    # Поиск
    search = st.text_input(
        "🔍 Поиск по названию поставщика",
        key="offers_tab_search_input"
    )

    # Фильтрация
    filtered_offers = offers
    if search:
        filtered_offers = [
            o for o in offers
            if search.lower() in o.get('supplier_name', '').lower()
        ]

    # Таблица
    df_data = []
    for o in filtered_offers:
        total_amount = o.get('total_amount', 0)
        if total_amount is None:
            total_amount = 0

        df_data.append({
            'Поставщик': o.get('supplier_name', 'Неизвестно'),
            'Сумма': f"{total_amount:,.0f} ₽" if total_amount else '0 ₽',
            'Дата': o.get('date', ''),
            'Файл': o.get('filename', '')
        })

    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)

    # Детальный просмотр - ИСПРАВЛЕНО!
    if filtered_offers:
        st.subheader("🔍 Детальный просмотр")

        # СОЗДАЕМ СЛОВАРЬ ДЛЯ SELECTBOX
        offer_options = {}
        for i, offer in enumerate(filtered_offers):
            # Создаем понятное название для каждого предложения
            supplier = offer.get('supplier_name', 'Неизвестно')
            filename = offer.get('filename', 'без файла')
            total = offer.get('total_amount', 0)
            if total is None:
                total = 0
            display_name = f"{supplier} - {filename} ({total:,.0f} ₽)"
            offer_options[display_name] = i

        # Отображаем selectbox с понятными названиями
        selected_display = st.selectbox(
            "Выберите предложение для просмотра",
            options=list(offer_options.keys()),
            key="offers_tab_selectbox"
        )

        # Получаем индекс выбранного предложения
        if selected_display:
            selected_idx = offer_options[selected_display]
            selected_offer = filtered_offers[selected_idx]

            # Показываем детали
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Поставщик:**", selected_offer.get('supplier_name', 'Не указан'))
                st.write("**ИНН:**", selected_offer.get('inn', 'Не указан'))
                st.write("**Сумма:**", f"{selected_offer.get('total_amount', 0):,.0f} ₽")
                st.write("**Контакт:**", selected_offer.get('contact_person', 'Не указан'))

            with col2:
                st.write("**Телефон:**", selected_offer.get('phone', 'Не указан'))
                st.write("**Email:**", selected_offer.get('email', 'Не указан'))
                st.write("**Дата:**", selected_offer.get('date', 'Не указана'))
                st.write("**Файл:**", selected_offer.get('filename', 'Не указан'))

            if selected_offer.get('products'):
                st.write("**Товары:**")
                products_df = pd.DataFrame(selected_offer['products'])
                st.dataframe(products_df, use_container_width=True)

            if selected_offer.get('key_advantages'):
                st.write("**Преимущества:**")
                for adv in selected_offer['key_advantages']:
                    st.write(f"• {adv}")

def show_comparison_tab():
    """Сравнение предложений"""
    offers = st.session_state.offers

    if len(offers) < 2:
        st.info("📭 Для сравнения нужно минимум 2 предложения")
        return

    st.subheader("🤝 Сравнение предложений")

    # Выбор предложений
    selected_indices = st.multiselect(
        "Выберите предложения для сравнения (2-4 шт)",
        options=range(len(offers)),
        format_func=lambda i: f"{offers[i].get('supplier_name', 'Неизвестно')} - {offers[i].get('total_amount', 0):,} ₽",
        default=list(range(min(3, len(offers))))
    )

    if len(selected_indices) < 2:
        st.warning("Выберите минимум 2 предложения")
        return

    if st.button("🚀 Сравнить", type="primary"):
        with st.spinner("Анализ предложений..."):
            selected_offers = [offers[i] for i in selected_indices]

            comparison = st.session_state.gigachat_client.compare_offers(selected_offers)
            st.session_state.comparison_result = comparison

            if "error" in comparison:
                st.error(comparison["error"])
                return

            # Результаты
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🏆 Лучшее предложение")
                if 'best_offer' in comparison:
                    best_idx = comparison['best_offer']
                    if isinstance(best_idx, int) and best_idx < len(selected_offers):
                        best = selected_offers[best_idx]
                        st.success(f"**{best.get('supplier_name', 'Неизвестно')}**")
                        st.write(f"Сумма: {best.get('total_amount', 0):,} ₽")

                        if 'best_offer_reason' in comparison:
                            st.info(comparison['best_offer_reason'])

            with col2:
                st.subheader("💰 Возможная экономия")
                if 'estimated_savings' in comparison:
                    st.metric("Экономия", comparison['estimated_savings'])

            # Таблица сравнения
            st.subheader("📊 Детальное сравнение")
            if 'comparison_table' in comparison:
                st.json(comparison['comparison_table'])

            # Рекомендации
            if 'recommendations' in comparison:
                st.subheader("📋 Рекомендации")
                for rec in comparison['recommendations']:
                    st.info(rec)

            # Риски
            if 'risks' in comparison:
                st.subheader("⚠️ Риски")
                risks = comparison['risks']
                if isinstance(risks, list):
                    for risk in risks:
                        st.warning(risk)
                else:
                    st.json(risks)

            # Моменты для переговоров
            if 'negotiation_points' in comparison:
                st.subheader("💬 Моменты для переговоров")
                points = comparison['negotiation_points']
                if isinstance(points, list):
                    for point in points:
                        st.write(f"• {point}")
                else:
                    st.write(points)


def show_response_tab():
    """Генерация ответов"""
    offers = st.session_state.offers

    if not offers:
        st.info("📭 Нет предложений для ответа")
        return

    st.subheader("✍️ Генерация ответа поставщику")

    # СОЗДАЕМ СЛОВАРЬ ДЛЯ SELECTBOX
    offer_options = {}
    for i, offer in enumerate(offers):
        # Создаем понятное название для каждого предложения
        supplier = offer.get('supplier_name', 'Неизвестно')
        filename = offer.get('filename', 'без файла')
        total = offer.get('total_amount', 0)
        if total is None:
            total = 0
        display_name = f"{supplier} - {filename} ({total:,.0f} ₽)"
        offer_options[display_name] = i

    # Отображаем selectbox с понятными названиями
    selected_display = st.selectbox(
        "Выберите предложение для ответа",
        options=list(offer_options.keys()),
        key="response_tab_selectbox"
    )

    if selected_display:
        selected_idx = offer_options[selected_display]
        offer = offers[selected_idx]

        with st.expander("📄 Детали предложения"):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Поставщик:**", offer.get('supplier_name', 'Не указан'))
                st.write("**Сумма:**", f"{offer.get('total_amount', 0):,.0f} ₽")
                st.write("**Контакт:**", offer.get('contact_person', 'Не указан'))

            with col2:
                st.write("**Телефон:**", offer.get('phone', 'Не указан'))
                st.write("**Email:**", offer.get('email', 'Не указан'))

            if offer.get('products'):
                st.write("**Товары:**")
                for p in offer['products'][:5]:  # Показываем первые 5 товаров
                    st.write(f"  • {p.get('name', '')}: {p.get('quantity', 0)} шт. x {p.get('price_per_unit', 0):,.0f} ₽ = {p.get('total_price', 0):,.0f} ₽")

        # Моменты для обсуждения
        st.subheader("💬 Моменты для обсуждения")

        # Получаем точки для переговоров из результатов сравнения, если они есть
        default_points = []
        if st.session_state.comparison_result:
            comparison = st.session_state.comparison_result
            if 'negotiation_points' in comparison:
                points = comparison['negotiation_points']
                if isinstance(points, list):
                    default_points = points

        # Поле для ввода моментов
        negotiation_text = st.text_area(
            "Введите моменты для обсуждения (каждый с новой строки)",
            value="\n".join(default_points) if default_points else "Сроки поставки\nУсловия оплаты\nСкидка за объем\nГарантийные обязательства",
            height=120,
            key="response_tab_textarea",
            help="Укажите вопросы, которые нужно обсудить с поставщиком"
        )

        # Кнопка генерации
        if st.session_state.get('response_generated', False) and st.session_state.get('response_text', ''):
            st.subheader("📨 Проект ответа")

            st.text_area(
                "Текст письма (скопируйте и отправьте поставщику):",
                st.session_state.response_text,
                height=300,
                key="response_tab_display"
            )

            # Кнопки для копирования и отправки
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Копировать в буфер", key="response_tab_copy_btn"):
                    st.info("Выделите текст и нажмите Ctrl+C для копирования")

            with col2:
                if st.button("✉️ Открыть в почте", key="response_tab_email_btn"):
                    email_subject = f"Ответ на коммерческое предложение от {offer.get('supplier_name', 'поставщика')}"
                    email_body = st.session_state.response_text.replace('\n', '%0D%0A')
                    mailto_link = f"mailto:{offer.get('email', '')}?subject={email_subject}&body={email_body}"
                    st.markdown(f"[Открыть в почтовой программе]({mailto_link})")



def show_search_tab():
    """Семантический поиск"""
    st.subheader("🔍 Семантический поиск по предложениям")

    # Проверяем наличие индекса
    meta_path = Config.VECTOR_DB_PATH + ".meta"
    index_path = Config.VECTOR_DB_PATH + ".faiss"

    if os.path.exists(meta_path) and os.path.exists(index_path):
        searcher = VectorSearch()
        searcher.load(Config.VECTOR_DB_PATH)

        query = st.text_input("Поисковый запрос", placeholder="Например: ноутбуки с доставкой по Москве")

        if query:
            with st.spinner("Поиск..."):
                results = searcher.search(query, k=5)

                if results:
                    for i, result in enumerate(results):
                        with st.expander(f"Результат {i+1} (схожесть: {result['similarity']:.2f})"):
                            st.write(f"**Поставщик:** {result['metadata'].get('supplier_name', 'Неизвестно')}")
                            st.write(f"**Сумма:** {result['metadata'].get('total_amount', 0):,} ₽")
                            st.write(f"**Фрагмент:** {result['document']}")

                            if result['metadata'].get('products'):
                                st.write("**Товары:**")
                                for p in result['metadata']['products'][:3]:
                                    st.write(f"  • {p.get('name', '')}")
                else:
                    st.info("Ничего не найдено")
    else:
        st.info("📭 База поиска не создана. Нажмите 'Создать индекс' в боковой панели.")


if __name__ == "__main__":
    # Создаем папку для загрузок
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Запускаем приложение
    main()
