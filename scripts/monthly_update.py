"""
monthly_update.py — 一鍵月度更新
================================
每月 10-15 號跑一次，自動：
1. 從 FinMind 抓最新月營收 + 季財報
2. 更新 data/financials.js

使用：
    python scripts/monthly_update.py

或雙擊 monthly_update.bat（如果有的話）

之後如果上 GitHub Pages，這個腳本還會自動 git commit + push。
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT = SCRIPT_DIR.parent

print("=" * 60)
print(f"Pulse 月度更新 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

# Step 1: 抓 FinMind 資料
print("\n[1/2] 抓 FinMind 月營收 + 季財報...")
result = subprocess.run(
    [sys.executable, str(SCRIPT_DIR / 'update_financials.py')],
    cwd=str(ROOT),
)
if result.returncode != 0:
    print("❌ FinMind 更新失敗，中斷")
    sys.exit(1)

# Step 2: 檢查是否在 git 倉庫內 → 如果是就自動 commit + push
print("\n[2/2] 檢查 git 狀態...")
is_git = subprocess.run(
    ['git', 'rev-parse', '--is-inside-work-tree'],
    cwd=str(ROOT),
    capture_output=True,
).returncode == 0

if is_git:
    print("  偵測到 git 倉庫，自動 commit + push...")
    today = datetime.now().strftime('%Y-%m-%d')
    subprocess.run(['git', 'add', 'data/financials.js'], cwd=str(ROOT))
    subprocess.run(['git', 'commit', '-m', f'Monthly FinMind update {today}'], cwd=str(ROOT))
    subprocess.run(['git', 'push'], cwd=str(ROOT))
    print("  ✅ 已推到 GitHub，網頁將自動更新")
else:
    print("  不在 git 倉庫內，跳過")
    print("  →  重新整理 pulse.html 看新資料")

print("\n✅ 月度更新完成")
