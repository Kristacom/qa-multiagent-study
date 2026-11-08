# 🤖 QA Multi-Agent System (OpenCode Project)

> **Автономная мультиагентная система обеспечения качества в среде OpenCode.**  
> Система построена на базе декомпозиции монолитных инструкций на 4 специализированных AI-агентов (`.opencode/agents/`), использующих выделенные `Skills` (`.opencode/skills/`), MCP-интеграции (Jira Cloud, Confluence Cloud) и формирующих живую BDD тестовую модель для **[Testomat.io TMS](https://app.testomat.io)**.

---

## 📋 Выполненные требования преподавателя и методички

1. **Отказ от скриптового воспроизведения (No hardcoded scripts):**  
   Логика анализа требований, синтеза тестов, контроля Quality Gate и синхронизации с Jira выполняется **исключительно автономными AI-агентами в OpenCode**, а не через Python-скрипт с заранее подготовленными ответами.
2. **Глубокие самодостаточные инструкции субагентов:**  
   Каждый агент в `.opencode/agents/*.md` снабжен подробной инструкцией: зона ответственности (In/Out of Scope), входные данные, пошаговый алгоритм, используемые инструменты и контракты артефактов.
3. **Защита от повторного создания сущностей (Idempotency / Anti-Duplication):**  
   Перед созданием задач в Jira (`Story`, `QA Subtask`, `Questions`) и тест-кейсов в TMS агенты проверяют существующие записи по ключам, меткам и связям, предотвращая появление дубликатов при повторных запусках.
4. **Автоматическое создание задач на уточнение требований ([QUESTION]):**  
   При обнаружении «белых пятен» или предупреждений (warnings) в ТЗ агент `task-designer` автоматически создает в Jira тикеты типа `Задача` на Product Owner / Business Analyst и связывает их с родительской Story связью `Relates`.
5. **Интеграция с реальной облачной TMS Testomat.io:**  
   Все 16 BDD сценариев выгружены в нативные спецификации `features/*.feature`, а также подготовлены `artifacts/testomat_export.csv` и `artifacts/testomat_export.json` для прямой синхронизации с проектом в [Testomat.io](https://app.testomat.io).
6. **Маскирование чувствительной информации (PII Masking & Security Policy):**  
   Внедрен отдельный регламент [`PII.md`](file:///C:/Users/Kosmos/qa-multiagent-study/PII.md) и модуль [`pii_sanitizer.py`](file:///C:/Users/Kosmos/qa-multiagent-study/pii_sanitizer.py) для автоматического маскирования персональных данных (ФИО, email, телефоны, документы, токены) при импорте спецификаций из Confluence, исключая их утечку в логи и открытые артефакты.

---

## 🏗 Архитектура конвейера агентов

```mermaid
flowchart TD
    User["👤 Пользователь / Команда /qa-flow"] --> Orch["👑 QA Orchestrator Agent\n(.opencode/agents/qa-orchestrator.md)"]

    subgraph Phase1 ["Фаза 1: Анализ требований Confluence"]
        Orch --> RRA["📋 Requirement Reviewer Agent\n(.opencode/agents/requirement-reviewer.md)"]
        RRA --> RR["artifacts/ReviewReport.json\n(Динамический анализ ТЗ, Quality Gate)"]
    end

    subgraph Gate ["Контроль качества (Quality Gate)"]
        RR --> QG{"Quality Gate?\n(score >= 80, 0 блокеров)"}
        QG -- "❌ Блокеры" --> Stop["🛑 Остановка флоу и эскалация"]
        QG -- "✅ Passed" --> Phase2
    end

    subgraph Phase2 ["Фаза 2: Проектирование задач в Jira"]
        TD["🎯 Task Designer Agent\n(.opencode/agents/task-designer.md)"]
        TD --> TD_Check{"Проверка дубликатов?\n(Jira Idempotency)"}
        TD_Check -- "Уже есть" --> TD_Reuse["Использование KAN-17 / KAN-18"]
        TD_Check -- "Новые" --> TD_Create["Создание Story + QA Subtask"]
        TD --> TD_Quest["Авто-создание тикетов [QUESTION] для warnings\n(KAN-19..KAN-24)"]
        TD --> JT["artifacts/JiraTasks.json\nartifacts/JiraUploadResult.json"]
    end

    subgraph Phase3 ["Фаза 3: BDD Тест-модель для Testomat.io"]
        TeD["🧪 Test Designer Agent\n(.opencode/agents/test-designer.md)"]
        TeD --> TM["features/*.feature\nartifacts/testomat_export.csv\nartifacts/testomat_export.json\n(100% покрытие AC, Gherkin BDD)"]
    end

    subgraph Phase4 ["Фаза 4: Верификация и Отчетность"]
        FR["artifacts/FinalReport.md\n(Сквозная трассируемость Confluence ↔ Jira ↔ Testomat.io)"]
    end

    Phase2 --> TD
    JT --> TeD
    Phase3 --> TeD
    TM --> Orch
    Orch --> FR
```

---

## 👥 Специализированные агенты

| Агент | Манифест | Подключенный Skill | Роль и ответственность |
| :--- | :--- | :--- | :--- |
| **`QA Orchestrator Agent`** | [qa-orchestrator.md](file:///.opencode/agents/qa-orchestrator.md) | — | Управление конвейером, контроль Quality Gate на каждом этапе, финальный аудит и формирование `FinalReport.md`. |
| **`Requirement Reviewer Agent`** | [requirement-reviewer.md](file:///.opencode/agents/requirement-reviewer.md) | `requirement-review` | Динамический анализ спецификаций Confluence, выделение FR/NFR, бизнес-правил, аудит белых пятен и расчет Quality Gate. |
| **`Task Designer Agent`** | [task-designer.md](file:///.opencode/agents/task-designer.md) | `task-design` | Защита от дубликатов в Jira, создание родительской Story, QA-подзадачи, авто-создание тикетов `[QUESTION]` по warnings. |
| **`Test Designer Agent`** | [test-designer.md](file:///.opencode/agents/test-designer.md) | `test-design` | Разработка BDD Gherkin тест-кейсов, нативных `.feature` файлов и экспорта для Testomat.io TMS. |

---

## 📁 Структура проекта

```text
qa-multiagent-study/
├── .opencode/
│   ├── agents/                    # Полноценные системные инструкции 4-х агентов
│   │   ├── qa-orchestrator.md     # Primary Orchestrator
│   │   ├── requirement-reviewer.md # Анализ требований и Quality Gate
│   │   ├── task-designer.md       # Управление Jira и анти-дубликация
│   │   └── test-designer.md       # BDD тест-дизайн для Testomat.io
│   ├── skills/                    # Регламенты навыков (Skills)
│   │   ├── requirement-review/    # Скилл аудита требований Confluence
│   │   ├── task-design/           # Скилл работы с Jira и защиты от дубликатов
│   │   └── test-design/           # Скилл проектирования BDD тестов для Testomat.io
│   └── commands/
│       └── qa-flow.md             # Сквозная команда OpenCode (/qa-flow)
│
├── features/                      # Нативные BDD Gherkin спецификации (Cucumber)
│   ├── auth.feature               # Сценарии для REQ-AUTH-001 (кнопка «Войти»)
│   ├── registration.feature       # Сценарии для REQ-REG-002 (валидация email)
│   └── checkout.feature           # Сценарии для REQ-CHECKOUT-003 (доставка)
│
├── opencode.jsonc                 # Конфигурация среды (MCP Jira, Confluence, Gemini, Cloud.ru)
├── AGENTS.md                      # Базовый регламент, контракты артефактов и роли
├── PII.md                         # Регламент маскирования персональных данных (PII Policy)
├── pii_sanitizer.py               # Автономный модуль санитизации PII (Email, Phone, ФИО, секреты)
│
├── requirements/                  # Синхронизированные спецификации
│   ├── CONF-PAGE-2031617.md       # ТЗ: Модуль оформления заказа (релиз 2.4)
│   └── ...
│
└── artifacts/                     # Результаты автономной работы агентов
    ├── ReviewReport.json          # Отчет анализа требований (Quality Gate: 84/100, 6 warnings)
    ├── JiraTasks.json             # Валидированная задача Jira с привязанными вопросами
    ├── JiraUploadResult.json      # Результат выгрузки KAN-17, KAN-18 и KAN-19..KAN-24
    ├── TestModel.json             # 16 BDD тест-кейсов (100% покрытие AC)
    ├── testomat_export.csv        # Экспорт для мгновенного Drag & Drop импорта в Testomat.io
    ├── testomat_export.json       # Экспорт для Testomat Load API
    └── FinalReport.md             # Итоговый отчет и матрица трассируемости
```

---

## ⚡️ Инструкция по запуску в OpenCode

### Шаг 1: Открытие проекта в OpenCode
Откройте терминал в папке проекта:
```bash
cd C:\Users\Kosmos\qa-multiagent-study
opencode
```

### Шаг 2: Запуск конвейера
В чате OpenCode выполните команду:
```text
/qa-flow
```
Или отправьте текстовый запрос агенту:
> *«Проанализируй требования по странице Confluence 2031617, проверь Quality Gate, синхронизируй задачи с Jira с защитой от дубликатов и подготовь тесты для Testomat.io TMS.»*

### Что произойдет автономно:
1. **Requirement Reviewer:** Считает спецификацию из Confluence, выделит 3 требования (`REQ-AUTH-001`, `REQ-REG-002`, `REQ-CHECKOUT-003`), 6 бизнес-правил, выявит 6 предупреждений и рассчитает Quality Gate (84/100, PASSED).
2. **Task Designer:** Проверит Jira на наличие существующих задач:
   - Обнаружит существующую Story `KAN-17` и QA-подзадачу `KAN-18` (не создавая дубликатов).
   - Обнаружит связанные тикеты вопросов `[QUESTION]` (`KAN-19` — `KAN-24`) и зафиксирует их связь.
3. **Test Designer:** Сформирует 16 BDD тест-кейсов со 100% покрытием критериев приемки в виде файлов `features/*.feature`, `artifacts/testomat_export.csv` и `artifacts/testomat_export.json`.
4. **QA Orchestrator:** Соберет сквозную матрицу трассируемости и опубликует `FinalReport.md`.

---

## 🚀 Синхронизация с Testomat.io TMS

Все 16 тест-кейсов готовы к отображению в твоем проекте [app.testomat.io](https://app.testomat.io):

### Вариант 1 (Мгновенный Drag & Drop через интерфейс — 15 секунд):
1. Открой свой проект в [app.testomat.io](https://app.testomat.io).
2. Перейди во вкладку **Tests** $\rightarrow$ нажми меню **«...»** (или кнопку «Import»).
3. Выбери **«Import from CSV»** и перетащи файл:
   [`artifacts/testomat_export.csv`](file:///C:/Users/Kosmos/qa-multiagent-study/artifacts/testomat_export.csv).
4. Все 16 тест-кейсов со сьютами, шагами `Given/When/Then`, тегами и приоритетами сразу появятся в интерфейсе!

### Вариант 2 (Автоматический через CLI синхронизатор):
В настройках проекта Testomat.io (Settings $\rightarrow$ API) скопируй токен проекта (`tstmt_...`) и выполни:
```bash
TESTOMATIO=tstmt_ТВОЙ_ТОКЕН npx @testomatio/check-cucumber -d features --sync
```

---

## 📊 Результаты и статус сущностей в Jira

| Сущность | Ключ | Назначение | Статус |
| :--- | :--- | :--- | :--- |
| **Story-родитель** | [KAN-17](https://kristapro.atlassian.net/browse/KAN-17) | Реализация модуля оформления заказа (Checkout) | ✅ Заведена |
| **QA-подзадача** | [KAN-18](https://kristapro.atlassian.net/browse/KAN-18) | `[QA] Test Execution` с комментарием DoD | ✅ Заведена |
| **Вопрос 1 (Dropdown ПВЗ)** | [KAN-19](https://kristapro.atlassian.net/browse/KAN-19) | `[QUESTION][REQ-CHECKOUT-003] Варианты и источник данных ПВЗ` | 🔗 Связан с KAN-17 |
| **Вопрос 2 (Пустой email)** | [KAN-20](https://kristapro.atlassian.net/browse/KAN-20) | `[QUESTION][REQ-REG-002] Поведение при пустом поле Email` | 🔗 Связан с KAN-17 |
| **Вопрос 3 (Валидация адреса/даты)** | [KAN-21](https://kristapro.atlassian.net/browse/KAN-21) | `[QUESTION][REQ-CHECKOUT-003] Маска и правила валидации полей` | 🔗 Связан с KAN-17 |
| **Вопрос 4 (Обязательные поля)** | [KAN-22](https://kristapro.atlassian.net/browse/KAN-22) | `[QUESTION][REQ-CHECKOUT-003] Список обязательных полей доставки` | 🔗 Связан с KAN-17 |
| **Вопрос 5 (Кнопка Войти)** | [KAN-23](https://kristapro.atlassian.net/browse/KAN-23) | `[QUESTION][REQ-AUTH-001] Состояние для авторизованного юзера` | 🔗 Связан с KAN-17 |
| **Вопрос 6 (Формат ошибки)** | [KAN-24](https://kristapro.atlassian.net/browse/KAN-24) | `[QUESTION][REQ-REG-002] Место и формат ошибки email` | 🔗 Связан с KAN-17 |
