import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from evaluator import evaluate_response


# =============================================================
# PATHS
# =============================================================

project_path = Path(__file__).resolve().parent.parent
dataset_path = Path(__file__).parent / "dataset" / "golden_dataset.json"
results_dir = Path(__file__).parent / "results"
results_dir.mkdir(parents=True, exist_ok=True)
results_file = results_dir / "eval_results.json"
report_md_file = results_dir / "report.md"


# =============================================================
# QUALITY GATE THRESHOLDS (Из лекции преподавателя)
# =============================================================

# Минимальная доля успешно пройденных Eval Cases (PASS)
MIN_PASS_RATE = 100.0

# Минимальная доля подтвержденных Expected Properties
MIN_EXPECTED_PROPERTIES_PASS_RATE = 95.0

# Максимально допустимая доля нарушений Forbidden Behavior
MAX_FORBIDDEN_BEHAVIOR_VIOLATION_RATE = 0.0

# Максимальное количество фатальных ошибок выполнения
MAX_ERRORS = 0


# =============================================================
# RUNNER
# =============================================================

def run_agent(prompt: str) -> str:
    """Запускает AI QA Агента в OpenCode и возвращает итоговый текстовый ответ."""
    opencode_cmd = shutil.which("opencode") or "opencode"

    process = subprocess.Popen(
        [
            opencode_cmd,
            "run",
            "--format",
            "json",
            "--dir",
            str(project_path),
            prompt,
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

    text_parts: List[str] = []

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
            f"QA Agent завершился с кодом ошибки {return_code}. STDERR: {stderr}"
        )

    return "\n".join(text_parts).strip()


def run_eval_pipeline(target_case_id: str = None, limit: int = None) -> Dict[str, Any]:
    print("=" * 80)
    print("🚀 ЗАПУСК AI EVAL PIPELINE (LLM-AS-A-JUDGE)")
    print("=" * 80)

    if not dataset_path.exists():
        raise FileNotFoundError(f"Файл датасета не найден: {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as file:
        eval_cases: List[Dict[str, Any]] = json.load(file)

    if target_case_id:
        eval_cases = [c for c in eval_cases if c["id"].lower() == target_case_id.lower()]
        if not eval_cases:
            raise ValueError(f"Кейс с ID '{target_case_id}' не найден в датасете.")

    if limit and limit > 0:
        eval_cases = eval_cases[:limit]

    print(f"📊 Всего Eval Cases для проверки: {len(eval_cases)}")

    eval_results: List[Dict[str, Any]] = []
    errors = 0

    for idx, eval_case in enumerate(eval_cases, 1):
        case_id = eval_case["id"]
        case_name = eval_case.get("name", "")
        category = eval_case.get("category", "")
        eval_input = eval_case["input"]
        source = eval_input.get("source")

        print("\n" + "-" * 80)
        print(f"[{idx}/{len(eval_cases)}] Тестирование: {case_id} — {case_name} ({category})")
        print("-" * 80)

        # Формирование промпта для агента
        if source == "confluence":
            page_id = eval_input.get("page_id")
            prompt = (
                f"Получи требования из Confluence для страницы pageId={page_id} "
                f"и выполни полный QA анализ по регламенту."
            )
        else:
            req_text = eval_input.get("requirements", "")
            prompt = (
                f"Проанализируй требования по регламенту QA Workflow:\n\n"
                f"{req_text}\n\n"
                f"Выполни этапы: проверка PII и безопасности, анализ требований, "
                f"расчет Quality Gate, формирование тестовой модели и задач."
            )

        try:
            print("🤖 1/2. Запуск QA Агента...", flush=True)
            agent_response = run_agent(prompt)

            print("⚖️ 2/2. Запуск Evaluator (LLM-as-a-Judge)...", flush=True)
            evaluation = evaluate_response(eval_case, agent_response)

            status = evaluation.get("status", "FAIL")
            score = evaluation.get("score", 0.0)

            print(f"   Результат: {status} (score: {score})")

            eval_results.append({
                "eval_case_id": case_id,
                "name": case_name,
                "category": category,
                "agent_response": agent_response,
                "evaluation": evaluation,
                "error": None,
            })

        except Exception as exc:
            print(f"❌ Ошибка при выполнении кейса {case_id}: {exc}")
            errors += 1
            eval_results.append({
                "eval_case_id": case_id,
                "name": case_name,
                "category": category,
                "agent_response": None,
                "evaluation": {
                    "eval_case_id": case_id,
                    "expected_properties": [],
                    "forbidden_behavior": [],
                    "status": "FAIL",
                    "score": 0.0,
                },
                "error": str(exc),
            })

    # =============================================================
    # РАСЧЕТ ИТОГОВЫХ МЕТРИК
    # =============================================================

    total = len(eval_results)
    passed = sum(1 for r in eval_results if r["evaluation"].get("status") == "PASS")
    failed = total - passed
    pass_rate = (passed / total * 100.0) if total > 0 else 0.0
    average_score = (sum(r["evaluation"].get("score", 0.0) for r in eval_results) / total) if total > 0 else 0.0

    total_expected_properties = 0
    passed_expected_properties = 0
    total_forbidden_behaviors = 0
    violated_forbidden_behaviors = 0

    for r in eval_results:
        ev = r["evaluation"]
        ep_list = ev.get("expected_properties", [])
        total_expected_properties += len(ep_list)
        passed_expected_properties += sum(1 for ep in ep_list if ep.get("passed"))

        fb_list = ev.get("forbidden_behavior", [])
        total_forbidden_behaviors += len(fb_list)
        violated_forbidden_behaviors += sum(1 for fb in fb_list if fb.get("violated"))

    expected_properties_pass_rate = (
        (passed_expected_properties / total_expected_properties * 100.0)
        if total_expected_properties > 0 else 0.0
    )
    forbidden_behavior_violation_rate = (
        (violated_forbidden_behaviors / total_forbidden_behaviors * 100.0)
        if total_forbidden_behaviors > 0 else 0.0
    )

    # Проверка порогов Quality Gate
    pass_rate_gate = pass_rate >= MIN_PASS_RATE
    ep_gate = expected_properties_pass_rate >= MIN_EXPECTED_PROPERTIES_PASS_RATE
    fb_gate = forbidden_behavior_violation_rate <= MAX_FORBIDDEN_BEHAVIOR_VIOLATION_RATE
    errors_gate = errors <= MAX_ERRORS

    overall_status = "PASS" if (pass_rate_gate and ep_gate and fb_gate and errors_gate) else "FAIL"

    # Консольный отчет
    print("\n" + "=" * 80)
    print("📋 QUALITY GATE ИТОГИ")
    print("=" * 80)
    print(f"Pass Rate >= {MIN_PASS_RATE:.1f}%: {'✅ PASS' if pass_rate_gate else '❌ FAIL'} (фактически: {pass_rate:.1f}%)")
    print(f"Expected Properties >= {MIN_EXPECTED_PROPERTIES_PASS_RATE:.1f}%: {'✅ PASS' if ep_gate else '❌ FAIL'} (фактически: {expected_properties_pass_rate:.1f}%)")
    print(f"Forbidden Behavior <= {MAX_FORBIDDEN_BEHAVIOR_VIOLATION_RATE:.1f}%: {'✅ PASS' if fb_gate else '❌ FAIL'} (фактически: {forbidden_behavior_violation_rate:.1f}%)")
    print(f"Ошибки исполнения <= {MAX_ERRORS}: {'✅ PASS' if errors_gate else '❌ FAIL'} (фактически: {errors})")
    print(f"\nИТОГОВЫЙ СТАТУС QUALITY GATE: {'🎉 PASS' if overall_status == 'PASS' else '🛑 FAIL'}")
    print("=" * 80)

    # Формирование JSON-отчета
    report = {
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(pass_rate, 1),
            "average_score": round(average_score, 2),
            "expected_properties_pass_rate": round(expected_properties_pass_rate, 1),
            "forbidden_behavior_violation_rate": round(forbidden_behavior_violation_rate, 1),
            "overall_status": overall_status,
        },
        "metrics": {
            "expected_properties": {
                "total": total_expected_properties,
                "passed": passed_expected_properties,
                "pass_rate": round(expected_properties_pass_rate, 1),
            },
            "forbidden_behavior": {
                "total": total_forbidden_behaviors,
                "violated": violated_forbidden_behaviors,
                "violation_rate": round(forbidden_behavior_violation_rate, 1),
            },
        },
        "quality_gate": {
            "status": overall_status,
            "criteria": {
                "pass_rate": {
                    "threshold": MIN_PASS_RATE,
                    "actual": round(pass_rate, 1),
                    "passed": pass_rate_gate,
                },
                "expected_properties_pass_rate": {
                    "threshold": MIN_EXPECTED_PROPERTIES_PASS_RATE,
                    "actual": round(expected_properties_pass_rate, 1),
                    "passed": ep_gate,
                },
                "forbidden_behavior_violation_rate": {
                    "threshold": MAX_FORBIDDEN_BEHAVIOR_VIOLATION_RATE,
                    "actual": round(forbidden_behavior_violation_rate, 1),
                    "passed": fb_gate,
                },
                "errors": {
                    "threshold": MAX_ERRORS,
                    "actual": errors,
                    "passed": errors_gate,
                },
            },
        },
        "results": eval_results,
    }

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Формирование Markdown-отчета
    md_content = f"""# 📊 AI Eval Pipeline: Итоговый отчет тестирования агентов

**Дата:** 2026-11-08  
**Итоговый статус Quality Gate:** **`{overall_status}`**  
**Общий Pass Rate:** **`{pass_rate:.1f}%`** (Успешно: {passed}/{total})  
**Average Score:** **`{average_score:.2f}`**

---

## 1. Метрики качества (Quality Gate Metrics)

| Метрика | Порог допуска | Фактическое значение | Статус |
| :--- | :--- | :--- | :---: |
| **Pass Rate** | $\\ge 100.0\\%$ | **{pass_rate:.1f}%** | {'✅ PASS' if pass_rate_gate else '❌ FAIL'} |
| **Expected Properties Pass Rate** | $\\ge 95.0\\%$ | **{expected_properties_pass_rate:.1f}%** ({passed_expected_properties}/{total_expected_properties}) | {'✅ PASS' if ep_gate else '❌ FAIL'} |
| **Forbidden Behavior Violation Rate** | $\\le 0.0\\%$ | **{forbidden_behavior_violation_rate:.1f}%** ({violated_forbidden_behaviors}/{total_forbidden_behaviors}) | {'✅ PASS' if fb_gate else '❌ FAIL'} |
| **Ошибки выполнения (Errors)** | $\\le 0$ | **{errors}** | {'✅ PASS' if errors_gate else '❌ FAIL'} |

---

## 2. Результаты по каждому Eval Case

| ID | Название | Категория | Статус | Score | Обоснование |
| :--- | :--- | :--- | :---: | :---: | :--- |
"""
    for r in eval_results:
        ev = r["evaluation"]
        st = ev.get("status", "FAIL")
        sc = ev.get("score", 0.0)
        badge = "✅ PASS" if st == "PASS" else "❌ FAIL"
        # Собираем причины
        reasons = []
        for ep in ev.get("expected_properties", []):
            if not ep.get("passed"):
                reasons.append(f"⚠️ EP: {ep.get('reason')}")
        for fb in ev.get("forbidden_behavior", []):
            if fb.get("violated"):
                reasons.append(f"🛑 FB: {fb.get('reason')}")
        if not reasons:
            reasons.append("Все свойства выполнены, запрещенное поведение отсутствует")
        md_content += f"| **{r['eval_case_id']}** | {r['name']} | `{r['category']}` | {badge} | {sc:.1f} | {'<br>'.join(reasons)} |\n"

    md_content += f"\n*Файл сырых данных: `{results_file.name}`*\n"

    with open(report_md_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n💾 Отчеты сохранены:\n - JSON: {results_file}\n - Markdown: {report_md_file}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Eval Pipeline Runner (LLM-as-a-Judge)")
    parser.add_argument("--case", type=str, help="Запустить только определенный кейс по ID (например TC-EVAL-001)")
    parser.add_argument("--limit", type=int, help="Ограничить количество кейсов для прогона")
    args = parser.parse_args()

    try:
        report = run_eval_pipeline(target_case_id=args.case, limit=args.limit)
        sys.exit(0 if report["quality_gate"]["status"] == "PASS" else 1)
    except Exception as e:
        print(f"❌ Критическая ошибка Runner: {e}")
        sys.exit(1)
