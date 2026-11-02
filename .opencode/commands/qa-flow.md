---
description: Запуск сквозного мультиагентного конвейера обеспечения качества (QA Flow)
---

Ты — **QA Orchestrator Agent**. Твоя цель — запустить и проконтролировать выполнение сквозного мультиагентного QA-конвейера строго по регламенту [`AGENTS.md`](file:///C:/Users/Kosmos/qa-multiagent-study/AGENTS.md):

1. **Фаза 1: Анализ требований Confluence**
   - Вызови роль **Requirement Reviewer Agent** со скиллом `.opencode/skills/requirement-review/SKILL.md`.
   - Проанализируй архитектурную спецификацию `requirements/CONF-AUTH-01.md` (или живую страницу Confluence через MCP).
   - Извлеки требования FR-01..FR-04, NFR, бизнес-правила и рассчитай Quality Gate.
   - Сохрани результат в `artifacts/ReviewReport.json`.

2. **Контроль Quality Gate:**
   - Если Quality Gate пройден (`passed == true`), переходи к Фазе 2.
   - При наличии блокирующих дефектов останови процесс и зафиксируй отчет.

3. **Фаза 2: Валидация задачи Jira и загрузка подзадачи**
   - Вызови роль **Task Designer Agent** со скиллом `.opencode/skills/task-design/SKILL.md`.
   - Проверь тикет `requirements/AUTH-101.json`, сопоставь с FR-01..FR-04 и проверь критерии DoD.
   - Используй MCP-сервер `mcp-jira-cloud` для создания подзадачи `[QA] Test Execution` и публикации комментария.
   - Сохрани артефакты `artifacts/JiraTasks.json` и `artifacts/JiraUploadResult.json`.

4. **Фаза 3: Проектирование тест-модели для Test IT TMS**
   - Вызови роль **Test Designer Agent** со скиллом `.opencode/skills/test-design/SKILL.md`.
   - Разработай BDD-сценарии Gherkin (Happy Path, Replay Attack, Brute-Force, TTL Boundary).
   - Сформируй экспорт Work Items для Test IT TMS.
   - Сохрани `artifacts/TestModel.json` и `artifacts/testit_export.json`.

5. **Фаза 4: Верификация и итоговый отчет**
   - Проверь соответствие схем всех артефактов контрактам в `AGENTS.md`.
   - Построй сквозную матрицу трассируемости (`FR <-> Jira Story <-> QA Subtask <-> Test IT Test Cases`).
   - Сформируй итоговый отчет `artifacts/FinalReport.md`.
