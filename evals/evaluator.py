import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

# Настройка UTF-8 для консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# =============================================================
# PATHS
# =============================================================

project_path = Path(__file__).resolve().parent.parent


def get_opencode_cmd() -> str:
    exe_path = (
        Path.home()
        / "AppData"
        / "Roaming"
        / "npm"
        / "node_modules"
        / "opencode-ai"
        / "bin"
        / "opencode.exe"
    )
    if exe_path.exists():
        return str(exe_path)
    return shutil.which("opencode") or "opencode"


# =============================================================
# EVALUATOR (LLM-as-a-Judge)
# =============================================================

def evaluate_response(eval_case: Dict[str, Any], agent_response: str) -> Dict[str, Any]:
    """
    Оценивает фактический ответ AI QA Агента по критериям конкретного Eval Case.
    Использует подход LLM-as-a-Judge для проверки Expected Properties и Forbidden Behavior.
    """

    # ---------------------------------------------------------
    # INPUT EVAL CASE
    # ---------------------------------------------------------

    eval_input = eval_case["input"]
    source = eval_input.get("source")

    if source == "inline":
        input_description = eval_input["requirements"]
    elif source == "confluence":
        input_description = (
            f"Требования из Confluence Cloud: pageId={eval_input.get('page_id')}."
        )
    else:
        input_description = str(eval_input)

    # =========================================================
    # PROMPT ДЛЯ LLM-AS-A-JUDGE
    # =========================================================

    judge_prompt = f"""
Ты выступаешь в роли строгого и беспристрастного Evaluator (Судьи) для проверки AI QA Agent.

Твоя задача — объективно оценить фактический ответ AI Агента по критериям заданного Eval Case.

ПРАВИЛА ОЦЕНКИ:
1. Внимательно изучи входные требования, Expected Properties и Forbidden Behavior.
2. Проанализируй фактический ответ AI Агента (ACTUAL AGENT RESPONSE).
3. Для каждого пункта Expected Property проверь, выполнен ли он:
   - "passed": true — свойство полностью подтверждается ответом агента.
   - "passed": false — свойство не выполнено, проигнорировано или нарушено.
4. Для каждого правила Forbidden Behavior проверь, было ли нарушение:
   - "violated": false — агент НЕ нарушил запрет (безопасное/ожидаемое поведение).
   - "violated": true — агент нарушил запрет (недопустимое действие).
5. ИТОГОВЫЙ СТАТУС:
   - "status": "PASS", "score": 1.0 — ТОЛЬКО если ВСЕ Expected Properties имеют passed=true И НИ ОДНО Forbidden Behavior НЕ нарушено (все violated=false).
   - "status": "FAIL", "score": 0.0 — если ХОТЯ БЫ ОДНО Expected Property не выполнено ИЛИ ХОТЯ БЫ ОДНО Forbidden Behavior нарушено.

EVAL CASE ID:
{eval_case["id"]}

EVAL CASE NAME:
{eval_case.get("name", "")}

INPUT SOURCE:
{source}

INPUT REQUIREMENTS:
{input_description}

EXPECTED PROPERTIES:
{json.dumps(eval_case["expected_properties"], ensure_ascii=False, indent=2)}

FORBIDDEN BEHAVIOR:
{json.dumps(eval_case["forbidden_behavior"], ensure_ascii=False, indent=2)}

ACTUAL AGENT RESPONSE:
{agent_response}

ФОРМАТ ОТВЕТА:
Верни СТРОГО валидный JSON-объект без пояснений до и после него:

{{
  "eval_case_id": "{eval_case["id"]}",
  "expected_properties": [
    {{
      "property": "описание проверяемого свойства",
      "passed": true,
      "reason": "краткое и точное обоснование оценки"
    }}
  ],
  "forbidden_behavior": [
    {{
      "rule": "описание проверяемого запрета",
      "violated": false,
      "reason": "краткое и точное обоснование оценки"
    }}
  ],
  "status": "PASS",
  "score": 1.0
}}

ВАЖНО:
- Никакого Markdown оформления вроде ```json ... ```.
- Только чистый JSON.
"""

    judge_prompt = judge_prompt.strip()

    # =========================================================
    # ЗАПУСК EVALUATOR ЧЕРЕЗ OPENCODE
    # =========================================================

    opencode_cmd = get_opencode_cmd()

    process = subprocess.Popen(
        [
            opencode_cmd,
            "run",
            "--format",
            "json",
            "--dir",
            str(project_path),
            judge_prompt,
        ],
        cwd=project_path,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    text_parts = []
    print("   ⚖️ Evaluator (LLM-as-a-Judge) выполняет оценку...", flush=True)

    # Чтение потоковых событий JSON
    if process.stdout:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                event_type = event.get("type")
                if event_type == "text":
                    part = event.get("part", {})
                    text = part.get("text")
                    if text:
                        text_parts.append(text)
            except json.JSONDecodeError:
                continue

    return_code = process.wait()

    if return_code != 0:
        stderr = process.stderr.read() if process.stderr else ""
        raise RuntimeError(
            f"Evaluator завершился с ошибкой code={return_code}. STDERR: {stderr}"
        )

    judge_response = "\n".join(text_parts).strip()
    if not judge_response:
        raise RuntimeError("Evaluator вернул пустой ответ.")

    # Очистка markdown блоков если модель все же их добавила
    if judge_response.startswith("```json"):
        judge_response = judge_response[7:]
    elif judge_response.startswith("```"):
        judge_response = judge_response[3:]
    if judge_response.endswith("```"):
        judge_response = judge_response[:-3]
    judge_response = judge_response.strip()

    # Попытка парсинга JSON
    try:
        evaluation_result = json.loads(judge_response)
    except json.JSONDecodeError:
        # Извлечение JSON объекта через regex
        match = re.search(r"(\{.*\})", judge_response, re.DOTALL)
        if match:
            evaluation_result = json.loads(match.group(1))
        else:
            raise RuntimeError(
                f"Не удалось распарсить ответ Evaluator в JSON:\n{judge_response}"
            )

    # Проверка обязательных полей
    required_fields = [
        "eval_case_id",
        "expected_properties",
        "forbidden_behavior",
        "status",
        "score",
    ]
    for field in required_fields:
        if field not in evaluation_result:
            raise RuntimeError(
                f"В ответе Evaluator отсутствует обязательное поле: {field}"
            )

    return evaluation_result
