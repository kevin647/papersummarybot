"""
Register paper4LGM to run at Windows startup (Task Scheduler).
Run once as administrator:  python setup_autostart.py
"""
import subprocess
import sys
from pathlib import Path

TASK_NAME   = "paper4LGM_alert"
VBS_PATH    = Path(__file__).parent / "run_background.vbs"
PYTHON_PATH = Path(sys.executable).parent / "pythonw.exe"
MAIN_PATH   = Path(__file__).parent / "main.py"


def register():
    # VBS 경로가 맞는지 확인
    if not VBS_PATH.exists():
        print(f"run_background.vbs 없음: {VBS_PATH}")
        return

    # 기존 작업 삭제 (있으면)
    subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True,
    )

    # 새 작업 등록: 로그온 시 VBS 실행 (콘솔 창 없음)
    result = subprocess.run(
        [
            "schtasks", "/create",
            "/tn",  TASK_NAME,
            "/tr",  f'wscript.exe "{VBS_PATH}"',
            "/sc",  "onlogon",
            "/rl",  "highest",
            "/f",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"✅ 작업 스케줄러 등록 완료: '{TASK_NAME}'")
        print(f"   로그인할 때마다 백그라운드에서 자동 실행됩니다.")
        print(f"\n지금 바로 시작하려면:")
        print(f'   wscript.exe "{VBS_PATH}"')
    else:
        print(f"❌ 등록 실패:\n{result.stderr}")
        print("\n관리자 권한으로 실행해주세요:")
        print("  우클릭 → '관리자 권한으로 실행'")


def unregister():
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"✅ '{TASK_NAME}' 작업 삭제됨.")
    else:
        print(f"작업 없음 또는 실패: {result.stderr}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--unregister", action="store_true", help="자동시작 해제")
    args = parser.parse_args()

    if args.unregister:
        unregister()
    else:
        register()
