import os
from typing import List, Dict

# Для веб-интерфейса
import streamlit as st

# Для работы с почтой
import imaplib
import email
from email.header import decode_header


class EmailProcessor:
    """Класс для обработки почты (Яндекс, Mail.ru, Gmail)"""

    def __init__(self, host: str, port: int, user: str, password: str):
        """
        Инициализация подключения к почте

        Args:
            host: Сервер IMAP (imap.yandex.ru, imap.mail.ru, imap.gmail.com)
            port: Порт (обычно 993 для SSL)
            user: Полный email адрес
            password: Пароль приложения (не основной пароль!)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.connection = None
        self.debug = False

    def connect(self):
        """Подключение к почтовому серверу с детальной диагностикой"""
        try:
            print(f"🔄 Подключение к {self.host}:{self.port}...")

            # Создаем SSL контекст
            import ssl
            context = ssl.create_default_context()

            # Подключаемся к серверу
            self.connection = imaplib.IMAP4_SSL(
                host=self.host,
                port=self.port,
                ssl_context=context
            )

            print(f"✅ Соединение установлено, выполняем вход для {self.user}...")

            # Выполняем вход
            result = self.connection.login(self.user, self.password)
            print(f"✅ Результат входа: {result}")

            # Выбираем папку INBOX
            self.connection.select('INBOX')
            print(f"✅ Папка INBOX выбрана успешно")

            return True

        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            print(f"❌ Ошибка IMAP: {error_msg}")

            if "AUTHENTICATIONFAILED" in error_msg:
                st.error("""
                ❌ **Ошибка аутентификации**
                
                Возможные причины:
                1. Неправильный логин или пароль приложения
                2. IMAP отключен в настройках почты
                3. Не включены пароли приложений
                
                Решение:
                - Проверьте настройки: https://mail.yandex.ru/?dpda
                - Создайте пароль приложения: https://id.yandex.ru/security/app-passwords
                """)
            elif "User is disabled" in error_msg:
                st.error("❌ Аккаунт отключен или заблокирован")
            else:
                st.error(f"❌ Ошибка IMAP: {error_msg}")
            return False

        except Exception as e:
            print(f"❌ Неожиданная ошибка: {type(e).__name__}: {e}")
            st.error(f"❌ Ошибка подключения: {type(e).__name__}: {e}")
            return False

    def disconnect(self):
        """Отключение от почтового сервера"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                print("✅ Отключение выполнено успешно")
            except Exception as e:
                print(f"⚠️ Ошибка при отключении: {e}")

    def decode_header(self, header: str) -> str:
        """Декодирование заголовка письма"""
        try:
            if header is None:
                return ""

            decoded_parts = decode_header(header)
            decoded_string = ''

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            decoded_string += part.decode(encoding)
                        except:
                            decoded_string += part.decode('utf-8', errors='ignore')
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += str(part)

            return decoded_string
        except Exception as e:
            print(f"⚠️ Ошибка декодирования заголовка: {e}")
            return str(header)

    def get_unread_emails(self, limit: int = 5) -> List[Dict]:
        """
        Получение непрочитанных писем с вложениями

        Args:
            limit: Максимальное количество писем

        Returns:
            Список писем с метаданными и вложениями
        """
        if not self.connect():
            return []

        emails = []

        try:
            # Поиск непрочитанных писем
            print("🔍 Поиск непрочитанных писем...")
            _, message_ids = self.connection.search(None, 'UNSEEN')

            # Получаем список ID писем
            msg_ids = message_ids[0].split()
            print(f"📨 Найдено непрочитанных писем: {len(msg_ids)}")

            # Ограничиваем количество
            for msg_id in msg_ids[:limit]:
                print(f"📧 Чтение письма ID: {msg_id}")

                # Получаем письмо
                _, msg_data = self.connection.fetch(msg_id, '(RFC822)')
                email_body = msg_data[0][1]

                # Парсим письмо
                message = email.message_from_bytes(email_body)

                # Извлекаем основные данные
                subject = self.decode_header(message.get('subject', ''))
                from_addr = self.decode_header(message.get('from', ''))
                date = message.get('date', '')

                print(f"   Тема: {subject}")
                print(f"   От: {from_addr}")

                # Извлекаем текст письма
                body = self._extract_body(message)

                # Извлекаем вложения
                attachments = self._extract_attachments(message)
                print(f"   Вложений: {len(attachments)}")

                emails.append({
                    'id': msg_id,
                    'subject': subject,
                    'from': from_addr,
                    'date': date,
                    'body': body,
                    'attachments': attachments
                })

                # Помечаем как прочитанное (опционально)
                # self.connection.store(msg_id, '+FLAGS', '\\Seen')

            print(f"✅ Успешно обработано писем: {len(emails)}")

        except Exception as e:
            print(f"❌ Ошибка при получении писем: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.disconnect()

        return emails

    def _extract_body(self, message) -> str:
        """Извлечение текстового тела письма"""
        body = ""

        try:
            if message.is_multipart():
                for part in message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Берем только текстовые части, не вложения
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                # Пробуем разные кодировки
                                for encoding in ['utf-8', 'cp1251', 'koi8-r', 'iso-8859-5']:
                                    try:
                                        body = payload.decode(encoding)
                                        break
                                    except:
                                        continue
                        except Exception as e:
                            print(f"⚠️ Ошибка извлечения части: {e}")
            else:
                # Простое письмо
                payload = message.get_payload(decode=True)
                if payload:
                    for encoding in ['utf-8', 'cp1251', 'koi8-r', 'iso-8859-5']:
                        try:
                            body = payload.decode(encoding)
                            break
                        except:
                            continue
        except Exception as e:
            print(f"⚠️ Ошибка извлечения тела письма: {e}")

        return body[:500]  # Возвращаем первые 500 символов

    def _extract_attachments(self, message) -> List[Dict]:
        """Извлечение вложений из письма"""
        attachments = []

        try:
            for part in message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue

                filename = part.get_filename()
                if not filename:
                    continue

                # Декодируем имя файла
                filename = self.decode_header(filename)

                # Проверяем расширение
                ext = os.path.splitext(filename)[1].lower()
                allowed_exts = ['.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls', '.csv']

                if ext in allowed_exts:
                    attachments.append({
                        'filename': filename,
                        'data': part.get_payload(decode=True)
                    })
                    print(f"   📎 Вложение: {filename}")

        except Exception as e:
            print(f"⚠️ Ошибка извлечения вложений: {e}")

        return attachments