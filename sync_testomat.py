#!/usr/bin/env python3
"""
Автоматическая синхронизация BDD тест-кейсов с Testomat.io TMS.
Считывает токен из .env или переменных окружения и выполняет npx check-cucumber.
"""

import datetime
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Настройка UTF-8 для вывода в консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parent
FEATURES_DIR = PROJECT_DIR / "features"
ARTIFACTS_DIR = PROJECT_DIR / "artifacts"
ENV_FILE = PROJECT_DIR / ".env"
SYNC_RESULT_FILE = ARTIFACTS_DIR / "testomat_sync_result.json"


def load_env_token() -> str:
    """Извлекает токен TESTOMATIO из окружения или .env файла."""
    token = os.environ.get("TESTOMATIO") or os.environ.get("TESTOMATIO_API_KEY")
    if token:
        return token.strip()

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k in ("TESTOMATIO", "TESTOMATIO_API_KEY") and v:
                    return v

    # Дефолтный токен проекта SHOP-QA
    return "tstmt_wXggia4NQN2Ql4PfHtvubfigWQY6WNW4nA1794135586"


def get_npx_cmd() -> str:
    """Возвращает корректный путь к бинарнику npx на Windows или Unix."""
    npx_bin = shutil.which("npx")
    if npx_bin:
        return npx_bin
    # Типичный путь на Windows
    win_npx = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs" / "npx.cmd"
    if win_npx.exists():
        return str(win_npx)
    return "npx"


def count_feature_scenarios() -> int:
    """Считает общее количество сценариев в папке features/."""
    total = 0
    for feature_path in FEATURES_DIR.glob("*.feature"):
        content = feature_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("Scenario:") or line.startswith("Scenario Outline:"):
                total += 1
    return total


def sync_with_testomat() -> bool:
    print("=" * 80)
    print("🚀 АВТОМАТИЧЕСКАЯ СИНХРОНИЗАЦИЯ ТЕСТ-КЕЙСОВ С TESTOMAT.IO TMS")
    print("=" * 80)

    token = load_env_token()
    if not token or not token.startswith("tstmt_"):
        print("❌ Ошибка: Не найден валидный API-токен Testomat.io (начинается с tstmt_).")
        print("Укажите TESTOMATIO в .env файле.")
        return False

    feature_files = list(FEATURES_DIR.glob("*.feature"))
    if not feature_files:
        print(f"❌ Ошибка: В каталоге {FEATURES_DIR} нет файлов *.feature.")
        return False

    scenarios_count = count_feature_scenarios()
    print(f"📁 Найдено feature-файлов: {len(feature_files)}")
    print(f"🧪 Всего BDD-сценариев к выгрузке: {scenarios_count}")
    print(f"🔑 Токен проекта: {token[:10]}...{token[-4:]}")

    npx_cmd = get_npx_cmd()
    print(f"⚙️ Используемый CLI: {npx_cmd} check-cucumber")

    env = os.environ.copy()
    env["TESTOMATIO"] = token

    cmd = [
        npx_cmd,
        "check-cucumber",
        "features/*.feature",
        "--create",
        "-U",
        "--sync",
    ]

    print("\n⏳ Отправка сценариев в app.testomat.io...", flush=True)

    try:
        process = subprocess.run(
            cmd,
            cwd=str(PROJECT_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True if sys.platform == "win32" else False,
        )

        stdout = process.stdout or ""
        stderr = process.stderr or ""

        if process.returncode == 0:
            print("✅ УСПЕШНО: Все сценарии выгружены и синхронизированы с Testomat.io!")
            if stdout.strip():
                print(stdout.strip())

            # Сохранение артефакта синхронизации
            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            result_data = {
                "tms": "Testomat.io",
                "status": "SUCCESS",
                "synced_at": datetime.datetime.now().isoformat(),
                "project": "SHOP-QA",
                "features_count": len(feature_files),
                "scenarios_count": scenarios_count,
                "token_prefix": token[:10],
                "details": stdout.strip(),
            }
            SYNC_RESULT_FILE.write_text(
                json.dumps(result_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"💾 Артефакт синхронизации сохранен: {SYNC_RESULT_FILE}")
            return True
        else:
            print(f"❌ Ошибка синхронизации (код {process.returncode}):")
            print(stderr or stdout)
            return False

    except Exception as exc:
        print(f"❌ Критическое исключение при вызове npx check-cucumber: {exc}")
        return False


if __name__ == "__main__":
    success = sync_with_testomat()
    sys.exit(0 if success else 1)
