"""Автономный модуль маскирования чувствительной информации (PII) из Confluence.

Регламент описан в файле: PII.md

Запуск:
    python pii_sanitizer.py [путь_к_файлу]
"""

import sys
import re
from pathlib import Path
from typing import Tuple, Dict, Any


# 1. Токены, пароли, ключи доступа
SECRET_PATTERN = re.compile(
    r'(?:ATATT3x[a-zA-Z0-9_\-=]{20,}|ghp_[a-zA-Z0-9]{20,}|(?:Bearer|Token)\s+[a-zA-Z0-9_\-\.]{20,}|tstmt_[a-zA-Z0-9]{20,})',
    re.IGNORECASE
)

# 2. СНИЛС (XXX-XXX-XXX XX)
SNILS_PATTERN = re.compile(r'\b\d{3}-\d{3}-\d{3}\s\d{2}\b')

# 3. Серия и номер паспорта РФ (12 34 567890 или 1234 567890)
PASSPORT_PATTERN = re.compile(r'\b\d{2}\s?\d{2}\s?\d{6}\b')

# 4. Телефоны РФ и международные форматы
PHONE_PATTERN = re.compile(
    r'(?:\+?7|8)[\s\-]?(?:\(?\d{3}\)?[\s\-]?)?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}|\b\+?[1-9]\d{0,2}[\s\-]?(?:\(\d{2,4}\)|\d{2,4})[\s\-]?\d{3}[\s\-]?\d{2,4}\b'
)

# 5. Email адреса (с исключением example.com, test.com)
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    re.IGNORECASE
)

# 6. ФИО в контексте атрибутов Confluence (Автор, Владелец, Контакты)
NAME_METADATA_PATTERN = re.compile(
    r'(?P<prefix>(?:Автор|Владелец|Контакты|Ответственный|Approved by|Author|Owner|Created by|Reviewer):\s*)(?P<name>[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
    re.IGNORECASE
)


def sanitize_pii(text: str) -> Tuple[str, Dict[str, Any]]:
    """Маскирует чувствительную информацию в тексте согласно PII.md.

    Возвращает:
        (sanitized_text, audit_stats)
    """
    stats: Dict[str, Any] = {
        "status": "PASSED",
        "masked_items_count": 0,
        "rules_applied": [
            "SECRET_TOKEN_MASK",
            "SNILS_MASK",
            "PASSPORT_MASK",
            "PHONE_MASK",
            "EMAIL_MASK",
            "METADATA_NAME_MASK"
        ],
        "details": []
    }

    sanitized = text

    # 1. Маскирование секретов и токенов
    def _replace_secret(match):
        stats["masked_items_count"] += 1
        stats["details"].append({"type": "SECRET", "match": match.group(0)[:8] + "..."})
        return "[SECRET_REDACTED]"
    sanitized = SECRET_PATTERN.sub(_replace_secret, sanitized)

    # 2. Маскирование документов (СНИЛС, Паспорт)
    def _replace_snils(match):
        stats["masked_items_count"] += 1
        stats["details"].append({"type": "SNILS", "masked": "[DOC_REDACTED]"})
        return "[DOC_REDACTED]"
    sanitized = SNILS_PATTERN.sub(_replace_snils, sanitized)

    def _replace_passport(match):
        stats["masked_items_count"] += 1
        stats["details"].append({"type": "PASSPORT", "masked": "[DOC_REDACTED]"})
        return "[DOC_REDACTED]"
    sanitized = PASSPORT_PATTERN.sub(_replace_passport, sanitized)

    # 3. Маскирование телефонов
    def _replace_phone(match):
        stats["masked_items_count"] += 1
        stats["details"].append({"type": "PHONE", "masked": "[PHONE_REDACTED]"})
        return "[PHONE_REDACTED]"
    sanitized = PHONE_PATTERN.sub(_replace_phone, sanitized)

    # 4. Маскирование email (с whitelist для синтетических фикстур)
    def _replace_email(match):
        val = match.group(0)
        if any(domain in val.lower() for domain in ["example.com", "example.org", "test.com", "sample.net"]):
            return val
        stats["masked_items_count"] += 1
        stats["details"].append({"type": "EMAIL", "masked": "[EMAIL_REDACTED]"})
        return "[EMAIL_REDACTED]"
    sanitized = EMAIL_PATTERN.sub(_replace_email, sanitized)

    # 5. Маскирование ФИО в метаданных Confluence
    def _replace_name(match):
        prefix = match.group("prefix")
        name = match.group("name")
        generic_roles = {"Product Owner", "Business Analyst", "QA Lead", "Solution Architect", "Scrum Master"}
        if name in generic_roles:
            return match.group(0)
        stats["masked_items_count"] += 1
        stats["details"].append({"type": "NAME", "masked": f"{prefix}[NAME_REDACTED]"})
        return f"{prefix}[NAME_REDACTED]"
    sanitized = NAME_METADATA_PATTERN.sub(_replace_name, sanitized)

    return sanitized, stats


def sanitize_file(file_path: Path) -> Dict[str, Any]:
    """Считывает файл, маскирует PII и перезаписывает его с очищенными данными."""
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
        print(f"✅ Файл {target_file.name} обработан.")
        print(f"🔒 Замаскировано элементов PII: {res['masked_items_count']}")
    else:
        # Демонстрационный запуск
        test_content = (
            "Статус: Approved\n"
            "Владелец: Петров Алексей Сергеевич\n"
            "Автор: Смирнова Елена\n"
            "Контакты: a.petrov@company.corp, тел: +7 (916) 111-22-33\n"
            "Паспорт ответственного: 45 10 123456, СНИЛС: 123-456-789 01\n"
            "Служебный токен стенда: ATATT3xFfGF0wGMpIojRWt6FkiFUx0uy3hZjT5FwCswblgayU\n"
            "Критерий REQ-REG-002: пользователь вводит валидный email user@example.com\n"
        )
        cleaned_text, audit = sanitize_pii(test_content)
        print("=== Демонстрация работы PII Sanitizer ===")
        print("--- Исходный текст с PII ---")
        print(test_content)
        print("--- Очищенный текст ---")
        print(cleaned_text)
        print("--- Отчет аудита безопасности ---")
        print(f"Статус: {audit['status']}")
        print(f"Всего скрыто объектов: {audit['masked_items_count']}")
        for d in audit["details"]:
            print(f" - [{d['type']}] -> {d.get('masked', d.get('match'))}")
