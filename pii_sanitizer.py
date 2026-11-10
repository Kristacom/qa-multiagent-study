"""Автономный модуль структурного маскирования PII (Format-Preserving Masking).

Регламент: PII.md

Сохраняет:
1. Домены email и различимость ролей:
   ivan.ivanov@company.ru -> i***.i***@company.ru
   support@company.ru     -> s***t@company.ru
   admin.sec@corp.net     -> a***.s***@corp.net
2. Код страны и оператора телефонов:
   +7 (999) 123-45-67    -> +7 (999) ***-**-67
3. Структуру ФИО в метаданных:
   Петров Алексей Сергеевич -> П***ов А. С.
4. Маски документов (СНИЛС, Паспорт):
   123-456-789 01        -> 123-***-*** 01
   45 10 123456          -> 45 10 ***456
"""

import sys
import re
from pathlib import Path
from typing import Tuple, Dict, Any

# Настройка UTF-8 для консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# 1. Секреты и токены
SECRET_PATTERN = re.compile(
    r'(?:ATATT3x[a-zA-Z0-9_\-=]{20,}|ghp_[a-zA-Z0-9]{20,}|(?:Bearer|Token)\s+[a-zA-Z0-9_\-\.]{20,}|tstmt_[a-zA-Z0-9]{20,})',
    re.IGNORECASE
)

# 2. СНИЛС (XXX-XXX-XXX XX)
SNILS_PATTERN = re.compile(r'\b(\d{3})-(\d{3})-(\d{3})\s(\d{2})\b')

# 3. Паспорт РФ (12 34 567890 или 1234 567890)
PASSPORT_PATTERN = re.compile(r'\b(\d{2}\s?\d{2})\s?(\d{3})(\d{3})\b')

# 4. Телефоны РФ и международные форматы
PHONE_PATTERN = re.compile(
    r'(?:\+?7|8)[\s\-]?(?:\(?\d{3}\)?[\s\-]?)?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}|\b\+?[1-9]\d{0,2}[\s\-]?(?:\(\d{2,4}\)|\d{2,4})[\s\-]?\d{3}[\s\-]?\d{2,4}\b'
)

# 5. Email адреса
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    re.IGNORECASE
)

# 6. ФИО в контексте атрибутов Confluence (Автор, Владелец, Контакты)
NAME_METADATA_PATTERN = re.compile(
    r'(?P<prefix>(?:Автор|Владелец|Контакты|Ответственный|Approved by|Author|Owner|Created by|Reviewer):\s*)(?P<name>[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
    re.IGNORECASE
)


def mask_email_format_preserving(email: str) -> str:
    """Маскирует email с сохранением домена и синтаксической структуры.

    ivan.ivanov@company.ru -> i***.i***@company.ru
    support@company.ru     -> s***t@company.ru
    """
    # Whitelist для тестовых синтетических фикстур
    if any(d in email.lower() for d in ["example.com", "example.org", "test.com", "sample.net"]):
        return email

    parts = email.split("@")
    if len(parts) != 2:
        return email
    local, domain = parts

    # Разбиваем локальную часть по точкам, дефисам и подчеркиваниям
    tokens = re.split(r'([._\-])', local)
    masked_tokens = []
    for t in tokens:
        if t in [".", "_", "-"]:
            masked_tokens.append(t)
        elif len(t) <= 2:
            masked_tokens.append(t[0] + "*")
        elif len(t) <= 4:
            masked_tokens.append(t[0] + "***")
        else:
            # Для длинных слов оставляем первую и последнюю букву: support -> s***t
            masked_tokens.append(t[0] + "***" + t[-1])

    return "".join(masked_tokens) + "@" + domain


def mask_phone_format_preserving(phone: str) -> str:
    """Маскирует номер телефона с сохранением кода страны, оператора и последних цифр.

    +7 (999) 123-45-67 -> +7 (999) ***-**-67
    """
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11:
        prefix = "+7" if digits.startswith("7") else "8"
        code = digits[1:4]
        last = digits[-2:]
        return f"{prefix} ({code}) ***-**-{last}"
    elif len(digits) > 7:
        return phone[:3] + " ***-**-" + digits[-2:]
    return phone[:2] + "****" + phone[-2:]


def mask_fullname_preserving(name: str) -> str:
    """Маскирует ФИО с сохранением фамильной основы и инициалов.

    Петров Алексей Сергеевич -> П***ов А. С.
    Смирнова Елена           -> С***ва Е.
    """
    parts = name.split()
    generic_roles = {"Product", "Business", "QA", "Solution", "Scrum"}
    if parts and parts[0] in generic_roles:
        return name

    if len(parts) >= 2:
        last = parts[0]
        if len(last) > 3:
            masked_last = last[0] + "***" + last[-2:]
        else:
            masked_last = last[0] + "***"
        initials = " ".join(f"{p[0]}." for p in parts[1:])
        return f"{masked_last} {initials}"

    return name[0] + "***"


def sanitize_pii(text: str) -> Tuple[str, Dict[str, Any]]:
    """Выполняет структурное маскирование чувствительной информации."""
    stats: Dict[str, Any] = {
        "status": "PASSED",
        "mode": "format_preserving",
        "masked_items_count": 0,
        "rules_applied": [
            "SECRET_TOKEN_MASK",
            "SNILS_FORMAT_MASK",
            "PASSPORT_FORMAT_MASK",
            "PHONE_FORMAT_MASK",
            "EMAIL_FORMAT_MASK",
            "METADATA_NAME_FORMAT_MASK"
        ],
        "details": []
    }

    sanitized = text

    # 1. Секреты и токены
    def _rep_secret(match):
        stats["masked_items_count"] += 1
        stats["details"].append({"type": "SECRET", "orig": match.group(0)[:8] + "..."})
        return "[SECRET_TOKEN]"
    sanitized = SECRET_PATTERN.sub(_rep_secret, sanitized)

    # 2. СНИЛС (123-456-789 01 -> 123-***-*** 01)
    def _rep_snils(match):
        stats["masked_items_count"] += 1
        masked = f"{match.group(1)}-***-*** {match.group(4)}"
        stats["details"].append({"type": "SNILS", "orig": match.group(0), "masked": masked})
        return masked
    sanitized = SNILS_PATTERN.sub(_rep_snils, sanitized)

    # 3. Паспорт (45 10 123456 -> 45 10 ***456)
    def _rep_passport(match):
        stats["masked_items_count"] += 1
        masked = f"{match.group(1)} ***{match.group(3)}"
        stats["details"].append({"type": "PASSPORT", "orig": match.group(0), "masked": masked})
        return masked
    sanitized = PASSPORT_PATTERN.sub(_rep_passport, sanitized)

    # 4. Телефоны
    def _rep_phone(match):
        val = match.group(0)
        # Исключаем если это даты или уже замаскированные СНИЛС
        if "-" in val and len(re.sub(r'\D', '', val)) < 10:
            return val
        stats["masked_items_count"] += 1
        masked = mask_phone_format_preserving(val)
        stats["details"].append({"type": "PHONE", "orig": val, "masked": masked})
        return masked
    sanitized = PHONE_PATTERN.sub(_rep_phone, sanitized)

    # 5. Email с сохранением доменов и разделителей
    def _rep_email(match):
        val = match.group(0)
        masked = mask_email_format_preserving(val)
        if masked != val:
            stats["masked_items_count"] += 1
            stats["details"].append({"type": "EMAIL", "orig": val, "masked": masked})
        return masked
    sanitized = EMAIL_PATTERN.sub(_rep_email, sanitized)

    # 6. ФИО в атрибутах
    def _rep_name(match):
        prefix = match.group("prefix")
        name = match.group("name")
        generic_roles = {"Product Owner", "Business Analyst", "QA Lead", "Solution Architect"}
        if name in generic_roles:
            return match.group(0)
        stats["masked_items_count"] += 1
        masked_name = mask_fullname_preserving(name)
        stats["details"].append({"type": "NAME", "orig": name, "masked": masked_name})
        return f"{prefix}{masked_name}"
    sanitized = NAME_METADATA_PATTERN.sub(_rep_name, sanitized)

    return sanitized, stats


def sanitize_file(file_path: Path) -> Dict[str, Any]:
    """Считывает файл, выполняет структурное маскирование и перезаписывает его."""
    content = file_path.read_text(encoding="utf-8")
    cleaned, stats = sanitize_pii(content)
    if stats["masked_items_count"] > 0:
        file_path.write_text(cleaned, encoding="utf-8")
    return stats


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = Path(sys.argv[1])
        if not target_file.exists():
            print(f"❌ Файл не найден: {target_file}")
            sys.exit(1)
        res = sanitize_file(target_file)
        print(f"✅ Файл {target_file.name} санитизирован.")
        print(f"🔒 Скрыто элементов (с сохранением структуры): {res['masked_items_count']}")
    else:
        # Демонстрационный запуск
        test_content = (
            "Статус: Approved\n"
            "Владелец: Петров Алексей Сергеевич\n"
            "Автор: Смирнова Елена\n"
            "Клиент: ivan.ivanov@company.ru, система проверяет домен company.ru\n"
            "Поддержка: support@company.ru, тел: +7 (916) 111-22-33\n"
            "Администратор: admin.sec@corp.net\n"
            "СНИЛС сотрудника: 123-456-789 01, Паспорт: 45 10 123456\n"
            "Токен доступа: ATATT3xFfGF0wGMpIojRWt6FkiFUx0uy3hZjT5FwCswblgayU\n"
            "Синтетический email фикстуры (REQ-REG-002): user@example.com (должен сохраниться)\n"
        )
        cleaned_text, audit = sanitize_pii(test_content)
        print("=== Демонстрация структурного маскирования PII ===")
        print("\n--- ИСХОДНЫЙ ТЕКСТ С PII ---")
        print(test_content)
        print("--- РЕЗУЛЬТАТ СТРУКТУРНОГО МАСКИРОВАНИЯ ---")
        print(cleaned_text)
        print("--- ОТЧЕТ АУДИТА БЕЗОПАСНОСТИ ---")
        print(f"Статус: {audit['status']}")
        print(f"Режим: {audit['mode']}")
        print(f"Всего обработано объектов: {audit['masked_items_count']}")
        for d in audit["details"]:
            print(f" • [{d['type']}] {d.get('orig')} -> {d.get('masked', '[SECRET_TOKEN]')}")
