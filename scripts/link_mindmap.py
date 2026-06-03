#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
link_mindmap.py — 把 mindmap.html 連結到 Level 2 的 data/financials.js

執行（從 完整網站\\ 根目錄）:
    python scripts\\link_mindmap.py

做什麼：
1. 找 mindmap.html 內的 const FINANCIALS = {大堆 JSON};
2. 替換成 const FINANCIALS = window.PULSE_FINANCIALS;
3. 在 </head> 前加 <script src="data/financials.js"></script>
4. 自動備份原檔到 _backup_financials/

效果：
- 跑完後，心智圖會自動讀 data/financials.js
- 之後跑 update_financials.py，心智圖跟 pulse.html 同步更新
- 不用再手動同步兩處

副作用：
- 不動 STOCKS_DB / CONFIDENCE_MAP / 心智圖節點關係（這些下一輪再處理）
- 心智圖的個股 mapping 跟 pulse.html 暫時各自獨立（升等 mapping 時要手動同步兩處）
"""
import re
import shutil
from datetime import datetime
from pathlib import Path

# ─── 路徑偵測 ───
SCRIPT_DIR = Path(__file__).parent.resolve()
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == 'scripts' else SCRIPT_DIR
MINDMAP_FILE = ROOT / 'mindmap.html'
BACKUP_DIR = ROOT / '_backup_financials'

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 連結心智圖到 Level 2")
print("=" * 60)
print(f"專案根目錄: {ROOT}")

# ─── 檢查檔案存在 ───
if not MINDMAP_FILE.exists():
    print(f"❌ 找不到 {MINDMAP_FILE}")
    print(f"   確認你已經把 industry_mindmap_v6.html 複製過來改名為 mindmap.html")
    exit(1)

html = MINDMAP_FILE.read_text(encoding='utf-8')
print(f"✓ 讀入 mindmap.html ({len(html) / 1024:.1f} KB)")

# ─── 備份 ───
BACKUP_DIR.mkdir(exist_ok=True)
backup_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = BACKUP_DIR / f"mindmap_{backup_ts}.html"
backup_path.write_text(html, encoding='utf-8')
print(f"✓ 備份原檔 → {backup_path.name}")

# ─── Step 1: 確認 FINANCIALS 存在 ───
financials_pattern = r"const FINANCIALS = \{.*?\};"
match = re.search(financials_pattern, html, re.DOTALL)

if not match:
    print(f"⚠️  找不到 'const FINANCIALS = {{...}}' 區塊")
    print(f"   可能 mindmap.html 沒有 FINANCIALS（不需要改）")
    print(f"   或者格式不同，請手動檢查")
    exit(1)

old_block = match.group(0)
old_size = len(old_block) / 1024
print(f"✓ 找到 const FINANCIALS = {{...}} ({old_size:.1f} KB)")

# ─── Step 2: 替換 ───
new_html = re.sub(
    financials_pattern,
    "const FINANCIALS = window.PULSE_FINANCIALS;",
    html,
    count=1,
    flags=re.DOTALL
)

# ─── Step 3: 加 <script src="data/financials.js"> ───
script_tag = '<script src="data/financials.js"></script>'

if script_tag in new_html:
    print(f"  (已經有 <script src=\"data/financials.js\">，不重複加)")
else:
    if '</head>' in new_html:
        new_html = new_html.replace('</head>', f'{script_tag}\n</head>', 1)
        print(f"✓ 在 </head> 前加入 <script src=\"data/financials.js\">")
    else:
        print(f"⚠️  找不到 </head>，無法插入 script tag")
        print(f"   你要手動加 {script_tag} 到 mindmap.html 開頭附近")

# ─── Step 4: 寫回 ───
MINDMAP_FILE.write_text(new_html, encoding='utf-8')

# ─── 統計 ───
new_size = len(new_html) / 1024
saved = old_size  # 大概省下這麼多（被 script tag 取代後相當乾淨）

print("\n" + "=" * 60)
print(f"✅ 完成")
print(f"   - mindmap.html: {len(html)/1024:.1f} KB → {new_size:.1f} KB（瘦身 {(1-new_size/(len(html)/1024))*100:.0f}%）")
print(f"   - 備份在 {backup_path}")
print()
print("下一步：")
print("  1. 重新整理瀏覽器內的 mindmap.html (Ctrl+Shift+R 強制清快取)")
print("  2. 開 F12 → Console 確認沒有錯誤")
print("  3. 從 pulse.html 點任一個股 → 心智圖按鈕 → 確認財報數據還在顯示")
print()
print("之後每月跑 update_financials.py，心智圖會自動同步 ✨")
