---
name: task-design
description: Парсинг задач Jira, проверка DoD, сопоставление с архитектурой и загрузка данных в Jira (создание QA-подзадачи и комментариев)
---

## Описание
Навык предназначен для разбора задач Jira (User Story, Task, Bug) в формате JSON или XML-экспорта, проверки критериев приемки (Acceptance Criteria), валидации Definition of Done (DoD), сопоставления с архитектурой и **активной загрузки данных в Jira** (создание QA-подзадачи и добавление комментариев через Jira MCP или REST API).

---

## 1. Входные данные (Inputs)
- Файл задачи Jira (`requirements/*.json` или `requirements/*.xml`, либо MCP `jira:get_issue`).
- Отчет анализа требований `artifacts/ReviewReport.json`.

---

## 2. Алгоритм выполнения (Procedure)
1. **Парсинг задачи Jira:**
   - Извлечь ключ (`key`), тип задачи (`issue_type`), название (`summary`), статус (`status`), приоритет (`priority`).
   - Извлечь критерии приемки (`acceptance_criteria`, AC) и правила готовности (`definition_of_done`, DoD).
2. **Сопоставление с архитектурой (Mapping):**
   - Найти, какие требования `FR-xx` из `ReviewReport.json` реализуются в рамках данной задачи Jira (`matched_requirements`).
   - Проверить готовность к тестированию (`is_ready_for_testing`, `dod_passed`).
3. **Загрузка данных в Jira (Jira Upload & Sync via MCP):**
   - **Создание подзадачи тестирования (QA Sub-Task):**
     - Вызов инструмента MCP: `jira:create_issue`.
     - Параметры: `parent_key = "AUTH-101"`, `issue_type = "Sub-task"`, `summary = "[QA] Test Execution: {summary}"`.
   - **Публикация отчета верификации в комментарии:**
     - Вызов `jira:add_comment` для публикации чек-листа DoD и статуса Quality Gate.
4. **Сохранение артефактов:**
   - Сохранить результат парсинга в `artifacts/JiraTasks.json`.
   - Сохранить статус выгрузки в Jira в `artifacts/JiraUploadResult.json`.

---

## 3. Выходные артефакты (Outputs)

### `artifacts/JiraTasks.json`
```json
{
  "task": {
    "key": "AUTH-101",
    "project_key": "AUTH",
    "issue_type": "Story",
    "summary": "Реализация верификации OTP-кода и выдачи JWT токенов",
    "status": "Ready for Testing",
    "priority": "High"
  },
  "verification": {
    "task_key": "AUTH-101",
    "is_ready_for_testing": true,
    "matched_requirements": ["FR-01", "FR-02", "FR-03", "FR-04"],
    "dod_passed": true,
    "discrepancies": []
  }
}
```

### `artifacts/JiraUploadResult.json`
```json
{
  "status": "uploaded",
  "jira_key": "AUTH-101",
  "created_subtask": {
    "key": "AUTH-102",
    "issue_type": "Sub-task",
    "summary": "[QA] Test Execution: Реализация верификации OTP-кода и выдачи JWT токенов",
    "status": "Open"
  },
  "comment_added": {
    "author": "task-designer-agent",
    "body": "✅ DoD верифицирован. Требования FR-01..FR-04 согласованы. Подготовлена тестовая модель."
  }
}
```
