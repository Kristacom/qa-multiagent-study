---
name: test-design
description: Создание тестовой модели в формате BDD Gherkin, генерация .feature файлов и экспорт для Testomat.io TMS
---

## Описание
Навык предназначен для синтеза требований архитектуры Confluence и задачи Jira в исчерпывающую тестовую модель, совместимую со спецификацией **Testomat.io TMS** (`https://app.testomat.io`). Тест-кейсы формулируются по стандарту BDD Gherkin (`Given / When / Then`) со 100% покрытием критериев приёмки (AC), формированием `.feature` файлов и дедупликацией сущностей.

---

## 1. Входные данные (Inputs)
- `artifacts/ReviewReport.json` — структурированные требования Confluence.
- `artifacts/JiraTasks.json` — разобранная задача Jira с критериями приемки.
- Параметры проекта Testomat.io: `SHOP-QA`, тип `Manual / BDD`, язык `ru`.

---

## 2. Алгоритм выполнения (Procedure)

### Шаг 1: Дедупликация и стабильная нумерация (Anti-duplication)
1. Проверить существующий файл `artifacts/TestModel.json`.
2. Если требования `REQ-xxx` уже покрыты тест-кейсами, сохранить стабильные идентификаторы (`TC-SHOP-001`, `TC-SHOP-002`...) и не дублировать проверки.
3. Новые тест-кейсы добавлять только для ранее не покрытых критериев приёмки.

### Шаг 2: Формирование классов тест-кейсов
- **Happy Path (Позитивные функциональные):** проверка штатного успешного сценария.
- **Negative (Негативные):** проверка обработки невалидных символов, пробелов, пустых значений, некорректных форматов.
- **Boundary (Граничные значения):** граничные проверки полей ввода, очистка данных при смене доставки.
- **Security / UI State:** проверка видимости элементов интерфейса для авторизованного vs неавторизованного пользователя.

### Шаг 3: Оформление сценариев в нотации BDD Gherkin
- `Given`: предусловие (состояние системы, авторизация, корзина).
- `When`: действие пользователя (ввод данных, клик по кнопке, переключение радио-кнопки).
- `Then`: ожидаемый результат (активность кнопки, переход на URL, появление сообщения об ошибке).

### Шаг 4: Генерация файлов спецификаций и экспорта для Testomat.io
1. Сохранить `.feature` файлы в каталоге `features/`:
   - `features/auth.feature` (для `REQ-AUTH-001`)
   - `features/registration.feature` (для `REQ-REG-002`)
   - `features/checkout.feature` (для `REQ-CHECKOUT-003`)
2. Сформировать `artifacts/testomat_export.json` (формат для Testomat Load API).
3. Сформировать `artifacts/testomat_export.csv` (для прямого импорта через Web UI Testomat.io).
4. Сохранить общую модель в `artifacts/TestModel.json`.

### Шаг 5: Синхронизация с Testomat.io TMS через официальный MCP-сервер (и CLI)
1. **Основной способ — MCP Server (@testomatio/mcp):**
   - В `opencode.jsonc` подключен официальный MCP-сервер `@testomatio/mcp`.
   - Агент использует MCP-инструменты `testomat.tests` (команда `bulk_upsert` для загрузки BDD-тестов, `list`, `create`) и `testomat.suites` для управления структурой сьютов.
2. **Скриптовый авто-синхронизатор (CLI fallback):**
   - Команда `python sync_testomat.py` или `npx check-cucumber features/*.feature --create -U --sync` считывает токен из `.env` и выгружает сценарии в облачный проект `shop-qa` в [Testomat.io](https://app.testomat.io).
   - Сценарии автоматически размечаются `@T...` и `@S...` идентификаторами, а статус фиксируется в `artifacts/testomat_sync_result.json`.

---

## 3. Выходной артефакт (Output)
Файл `artifacts/TestModel.json`:
```json
{
  "project": "SHOP-QA",
  "version": "2.4",
  "total_cases": 16,
  "coverage_percentage": 100,
  "test_cases": [
    {
      "id": "TC-SHOP-001",
      "title": "Отображение кнопки «Войти» для неавторизованного пользователя на главной странице",
      "priority": "P0",
      "severity": "Critical",
      "type": "Positive",
      "linked_requirement_id": "REQ-AUTH-001",
      "linked_jira_key": "KAN-17",
      "preconditions": ["Пользователь не авторизован в системе"],
      "bdd_steps": [
        { "keyword": "GIVEN", "action": "Пользователь открывает главную страницу интернет-магазина", "expected_result": "Главная страница успешно загружена" },
        { "keyword": "WHEN", "action": "Пользователь просматривает область шапки сайта (header)", "expected_result": "Кнопка «Войти» видна и доступна для взаимодействия" },
        { "keyword": "THEN", "action": "Пользователь проверяет текст кнопки", "expected_result": "Текст кнопки строго соответствует «Войти»" }
      ],
      "tags": ["ui", "auth", "p0", "smoke"]
    }
  ]
}
```
