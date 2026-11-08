---
name: task-design
description: Парсинг задач Jira, проверка DoD, защита от дубликатов, создание подзадач и задач на уточнение требований
---

## Описание
Навык предназначен для разбора задач Jira (User Story, Task, Bug), проверки критериев приемки (Acceptance Criteria), валидации Definition of Done (DoD), **защиты от повторного создания дубликатов (Idempotency)**, загрузки QA-подзадач и **автоматического заведения тикетов на уточнение требований ([QUESTION])** при наличии предупреждений в ТЗ.

---

## 1. Входные данные (Inputs)
- Файл задачи Jira (`requirements/*.json` или `requirements/*.xml`, либо MCP `jira:get_issue`).
- Отчет анализа требований `artifacts/ReviewReport.json`.
- Параметры подключения к Jira Cloud (`JIRA_BASE_URL`, `JIRA_API_TOKEN`, проект `KAN`).

---

## 2. Алгоритм выполнения (Procedure)

### Шаг 1: Проверка на дубликаты (Idempotency Check)
1. **Родительская задача (Parent Story):**
   - Выполнить поиск в проекте `KAN` по меткам (например, `conf-page-2031617`) или по названию спецификации.
   - Если задача найдена (например, `KAN-17`) $\rightarrow$ использовать существующий ключ, **не создавать дубликат**.
2. **QA-подзадача тестирования:**
   - Запросить список подзадач `fields.subtasks` у родительской задачи.
   - Если подзадача с префиксом `[QA] Test Execution` уже существует (например, `KAN-18`) $\rightarrow$ использовать существующий ключ.
3. **Задачи на уточнение требований ([QUESTION]):**
   - Запросить список связанных задач `fields.issuelinks` у родительской задачи.
   - Проверить, какие из `warnings` уже заведены в Jira (например, `KAN-19` — `KAN-24`).
   - Исключить их из очереди на создание.

### Шаг 2: Валидация задачи и DoD
1. Сопоставить требования `REQ-xxx` из `ReviewReport.json` с задачей Jira.
2. Проверить критерии Definition of Done (`dod_passed: true` при отсутствии блокирующих дефектов).

### Шаг 3: Загрузка недостающих сущностей в Jira (Jira Upload & Sync)
1. **Создание Story-родителя:** если не найдена при Шаге 1 $\rightarrow$ создать через `jira:create_issue`.
2. **Создание QA-подзадачи:** если не найдена при Шаге 1 $\rightarrow$ создать через `jira:create_issue` с `parent_key`.
3. **Создание задач на уточнение требований:**
   - Для каждого нового `warning`:
     - Создать задачу типа `Задача` (id `10001`): `summary = "[QUESTION][{REQ_ID}] {Суть вопроса}"`.
     - Связать с родительской задачей через `jira:add_issue_link` (тип связи `Relates`).
4. **Публикация отчета верификации:**
   - Опубликовать комментарий к родительской задаче со сводкой готовности и ссылками на тикеты.

### Шаг 4: Сохранение артефактов
- Сохранить верификацию в `artifacts/JiraTasks.json`.
- Сохранить статус и ключи всех сущностей в `artifacts/JiraUploadResult.json`.

---

## 3. Выходные артефакты (Outputs)

### `artifacts/JiraTasks.json`
```json
{
  "task": {
    "key": "KAN-17",
    "project_key": "KAN",
    "issue_type": "Задача",
    "summary": "Реализация модуля оформления заказа (Checkout) — релиз 2.4",
    "status": "Idea",
    "labels": ["qa-parent", "mcp-synced", "checkout", "conf-page-2031617"],
    "source_requirements": ["REQ-AUTH-001", "REQ-REG-002", "REQ-CHECKOUT-003"]
  },
  "verification": {
    "task_key": "KAN-17",
    "is_ready_for_testing": true,
    "matched_requirements": ["REQ-AUTH-001", "REQ-REG-002", "REQ-CHECKOUT-003"],
    "dod_passed": true,
    "discrepancies": [],
    "quality_gate": { "passed": true, "score": 84, "warnings_count": 6 }
  },
  "clarification_tasks": [
    {
      "key": "KAN-19",
      "issue_type": "Задача",
      "summary": "[QUESTION][REQ-CHECKOUT-003] Уточнить перечень вариантов и источник данных для dropdown «Пункт выдачи»",
      "linked_story": "KAN-17",
      "link_type": "Relates",
      "status": "Idea"
    }
  ]
}
```

### `artifacts/JiraUploadResult.json`
```json
{
  "status": "success",
  "mode": "live_sync",
  "jira_instance": "https://kristapro.atlassian.net",
  "parent_story": "KAN-17",
  "parent_url": "https://kristapro.atlassian.net/browse/KAN-17",
  "created_subtask": {
    "key": "KAN-18",
    "url": "https://kristapro.atlassian.net/browse/KAN-18",
    "issue_type": "Subtask",
    "summary": "[QA] Test Execution: Реализация модуля оформления заказа (Checkout) — релиз 2.4"
  },
  "created_clarification_tasks": [
    {
      "key": "KAN-19",
      "url": "https://kristapro.atlassian.net/browse/KAN-19",
      "summary": "[QUESTION][REQ-CHECKOUT-003] Уточнить перечень вариантов и источник данных для dropdown «Пункт выдачи»",
      "issue_type": "Задача",
      "linked_to": "KAN-17"
    }
  ]
}
```
