---
name: test-design
description: Создание тестовой модели в формате BDD Gherkin и экспорт сценариев для Test IT TMS
---

## Описание
Навык предназначен для синтеза требований архитектуры Confluence и задачи Jira в исчерпывающую тестовую модель, совместимую со спецификацией API и интерфейсом **Test IT TMS** (Work Items). Тест-кейсы формулируются по стандарту BDD Gherkin (`Given / When / Then`).

---

## 1. Входные данные (Inputs)
- `artifacts/ReviewReport.json` — структурированные требования Confluence.
- `artifacts/JiraTasks.json` — разобранная задача Jira с критериями приемки.

---

## 2. Алгоритм выполнения (Procedure)
1. **Проектирование секции / тест-сьюта Test IT:**
   - Определить название тестового набора (`suite_title` / `section_name`), соответствующее тестируемому сервису и фиче.
   - Задать описание и привязку к задаче Jira (`jira_task_key`).
2. **Формирование классов тест-кейсов:**
   - **Happy Path (Позитивные функциональные):** проверка штатного успешного сценария с ожидаемым HTTP 200/201.
   - **Negative (Негативные):** проверка обработки неверных кодов, невалидных форматов, отсутствующих обязательных полей.
   - **Boundary (Граничные значения):** проверка граничных условий TTL (179 сек vs 181 сек), граничных сумм.
   - **Security (Безопасность):** защита от повторного использования токенов/кодов (Replay Attack), защита от подбора (Brute-Force), проверка блокировки аккаунта.
3. **Оформление сценариев в нотации BDD Gherkin:**
   - `Given`: предусловие (состояние системы, наличие данных в БД/кэше).
   - `When`: совершенное действие (отправка HTTP-запроса, клик, событие).
   - `Then`: ожидаемый результат на уровне системы и API.
   - `And`: дополнительное утверждение (запись в аудит, очистка Redis, отправка события).
4. **Маппинг на атрибуты Test IT TMS:**
   - `entityTypeName`: `TestCases`.
   - `severity`: Blocker (Critical), Critical (High), Major (Medium), Normal (Low).
   - `priority`: High, Medium, Low.
   - `preconditions` / `postconditions`.
   - `test_data`: конкретный JSON с тестовыми номерами, кодами, телами запросов.
   - `tags`: метки `#smoke`, `#auth`, `#security`, `#negative`, привязка к задаче Jira.
5. **Сохранение артефактов и подготовка экспорта в Test IT:**
   - Сохранить общую тестовую модель в `artifacts/TestModel.json`.
   - Сформировать готовый экспорт для Test IT WorkItem API в `artifacts/testit_export.json`.

---

## 3. Выходной артефакт (Output)
Файл `artifacts/TestModel.json`:
```json
{
  "suite_id": "SUITE-AUTH-01",
  "title": "Тестирование верификации OTP-кода и выпуска токенов",
  "description": "Сценарии проверки аутентификации для Test IT TMS",
  "jira_task_key": "AUTH-101",
  "test_cases": [
    {
      "id": "TC-AUTH-001",
      "title": "Успешная верификация корректного OTP-кода (Happy Path)",
      "description": "Проверка генерации JWT токенов и очистки кода из кэша при вводе верного OTP.",
      "type": "Functional",
      "priority": "Critical",
      "severity": "Blocker",
      "preconditions": [
        "Пользователь с номером +79991234567 зарегистрирован",
        "Сгенерирован и отправлен OTP код '482910' (TTL 180с)"
      ],
      "bdd_steps": [
        {"keyword": "Given", "action": "Пользователь находится на экране ввода СМС-кода", "expected_result": "Поле ввода активно"},
        {"keyword": "When", "action": "Отправляет POST /api/v1/auth/otp/verify с кодом '482910'", "expected_result": "Запрос доставлен"},
        {"keyword": "Then", "action": "Сервер возвращает HTTP 200 OK с access_token и refresh_token", "expected_result": "В теле ответа валидный JWT access_token со сроком 15 мин"},
        {"keyword": "And", "action": "Код '482910' удаляется из Redis кэша", "expected_result": "Ключ в Redis отсутствует"}
      ],
      "postconditions": [
        "Сессия пользователя создана",
        "В audit-log записано событие успешного входа"
      ],
      "test_data": {
        "phone": "+79991234567",
        "code": "482910"
      },
      "linked_jira_key": "AUTH-101",
      "linked_requirement_id": "FR-02",
      "tags": ["smoke", "positive", "auth", "testit"]
    }
  ]
}
```
