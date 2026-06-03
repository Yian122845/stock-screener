#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動更新財務資料腳本 (Level 2 適配版)

跟原版差別：
  - 原版：patch industry_mindmap_v6.html 和 pulse_v0_5.html 內的 const FINANCIALS
  - 新版：直接寫到 data/financials.js（window.PULSE_FINANCIALS = {...}）

執行：
  從專案根目錄（含 data/ 和 scripts/）跑：
    python scripts\\update_financials.py
  或直接從 scripts/ 內跑（自動回上一層找 token + data）：
    cd scripts
    python update_financials.py

需求：
  - 專案根目錄要有 finmind_token.txt
  - 專案根目錄要有 data/ 資料夾
  - data/stocks.js 用來萃 ticker 清單（會自動讀）
  - 也支援額外 EXTRA_TICKERS（給興櫃/非 mapping 內的個股）

每月例行：python scripts\\update_financials.py
"""

import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("請先安裝：pip install requests")
    sys.exit(1)


# ─── 路徑設定（自動偵測） ──────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
# 如果腳本在 scripts/ 內 → 專案根在上一層
# 如果腳本直接在專案根 → 專案根就是 SCRIPT_DIR
if SCRIPT_DIR.name == 'scripts':
    ROOT = SCRIPT_DIR.parent
else:
    ROOT = SCRIPT_DIR

TOKEN_FILE = ROOT / "finmind_token.txt"
STOCKS_FILE = ROOT / "data" / "stocks.js"
FINANCIALS_OUTPUT = ROOT / "data" / "financials.js"
BACKUP_DIR = ROOT / "_backup_financials"


# ─── FinMind 設定（跟原版一致） ───────────────────────
START_DATE = "2024-01-01"
API_URL = "https://api.finmindtrade.com/api/v4/data"
SLEEP_SECONDS = 0.5


# ─── 額外 ticker（不在 mapping 內，但想抓財報的） ─────
# 用途：保留興櫃股或還沒升等到 mapping 但想觀察的個股
# 例如：7415, 3560 在原版有但 V3 mapping 已淘汰
EXTRA_TICKERS = [
    "7415", "3560",   # 興櫃股，保留財務基準對比用（如需淘汰可刪）
]


# ─── Step 1: 讀 token ──────────────────────────────────
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 開始自動更新 (Level 2)")
print("=" * 60)
print(f"專案根目錄: {ROOT}")

if not TOKEN_FILE.exists():
    print(f"❌ 找不到 token 檔: {TOKEN_FILE}")
    print(f"   請在 {ROOT} 建立 finmind_token.txt，內容只放 token 字串")
    sys.exit(1)

TOKEN = TOKEN_FILE.read_text(encoding="utf-8-sig").strip()
TOKEN = TOKEN.strip("\ufeff \t\n\r\"'")
if not TOKEN or not TOKEN.startswith("eyJ"):
    print(f"❌ token 看起來無效")
    print(f"   檔案路徑: {TOKEN_FILE}")
    print(f"   讀到內容長度: {len(TOKEN)}")
    if TOKEN:
        print(f"   開頭 5 字: {repr(TOKEN[:5])}")
    print(f"   FinMind token 應該長這樣（以 eyJ 開頭、3 段以 . 分隔）:")
    print(f"   eyJ0eXAiOiJKV1QiLCJhbGc...xxx.yyy.zzz")
    sys.exit(1)
print(f"✓ Token 讀入 ({len(TOKEN)} 字)")


# ─── Step 2: 從 data/stocks.js 萃 ticker 清單 ───────────
if not STOCKS_FILE.exists():
    print(f"❌ 找不到 {STOCKS_FILE}")
    print(f"   確認你在 Level 2 重構後的專案目錄內跑這個腳本")
    sys.exit(1)

stocks_content = STOCKS_FILE.read_text(encoding="utf-8")
mapping_tickers = re.findall(r"ticker:'(\d+)'", stocks_content)
mapping_tickers = sorted(set(mapping_tickers))
print(f"✓ 從 data/stocks.js 萃出 {len(mapping_tickers)} 檔 mapping 內個股")

# Merge: mapping + EXTRA
TICKERS = sorted(set(mapping_tickers) | set(EXTRA_TICKERS))
print(f"✓ 加上 EXTRA_TICKERS {len(EXTRA_TICKERS)} 檔 → 共 {len(TICKERS)} 檔要抓")


# ─── Step 3: 抓 FinMind 資料（用 Bearer header） ───────
print(f"\n預估時間: {len(TICKERS) * 2 * SLEEP_SECONDS / 60:.1f} 分鐘\n")

def fetch(dataset, ticker):
    """跟原版一致：Bearer header + 重試 429"""
    params = {"dataset": dataset, "data_id": ticker, "start_date": START_DATE}
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        r = requests.get(API_URL, params=params, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json().get("data", []), 200
        elif r.status_code == 429:
            time.sleep(60)
            return None, 429
        return None, r.status_code
    except Exception as e:
        return None, str(e)

monthly_raw = defaultdict(list)
quarterly_raw = defaultdict(list)
skipped = []
start_t = time.time()

for i, t in enumerate(TICKERS, 1):
    elapsed = time.time() - start_t
    eta = (elapsed / i) * (len(TICKERS) - i) if i > 0 else 0
    print(f"[{i:>3}/{len(TICKERS)}] {t:>5}  ({elapsed:.0f}s, ETA {eta:.0f}s)", end="  ")

    q, c1 = fetch("TaiwanStockFinancialStatements", t)
    if q:
        for row in q:
            quarterly_raw[t].append({"date": row["date"], "type": row.get("type"), "value": row.get("value")})
        n_q = len({r["date"] for r in quarterly_raw[t]})
        print(f"季 {n_q:>2}", end="  ")
    else:
        print(f"季 ✗({c1})", end="  ")
        skipped.append((t, f"q:{c1}"))

    time.sleep(SLEEP_SECONDS)

    m, c2 = fetch("TaiwanStockMonthRevenue", t)
    if m:
        for row in m:
            try:
                rev = float(row.get("revenue", 0))
                if rev <= 0:
                    continue
                monthly_raw[t].append({
                    "date": row["date"],
                    "revenue": rev,
                    "year": int(row["revenue_year"]) if row.get("revenue_year") else 0,
                    "month": int(row["revenue_month"]) if row.get("revenue_month") else 0,
                })
            except Exception:
                pass
        print(f"月 {len(m):>3}")
    else:
        print(f"月 ✗({c2})")
        skipped.append((t, f"m:{c2}"))

    time.sleep(SLEEP_SECONDS)

print(f"\n抓取完成，{time.time() - start_t:.0f} 秒")


# ─── Step 4: 處理成 FINANCIALS object（跟原版邏輯 100% 一致） ──
print("\n計算動能指標...")

def build_summary(ticker):
    m_list = sorted(monthly_raw[ticker], key=lambda x: x["date"])
    q_rows = quarterly_raw[ticker]
    by_date = {}
    for row in q_rows:
        d = row["date"]
        ty = row.get("type", "")
        v = row.get("value")
        if d not in by_date:
            by_date[d] = {"date": d, "stock_id": ticker}
        if ty:
            try:
                by_date[d][ty] = float(v) if v else None
            except Exception:
                pass

    q_list = []
    for d in sorted(by_date.keys()):
        r = by_date[d]
        rev = r.get("Revenue")
        gp = r.get("GrossProfit")
        op = r.get("OperatingIncome")
        eps = r.get("EPS")
        q_list.append({
            "d": d,
            "rev": round(rev / 1e8, 2) if rev else None,
            "gm": round(gp / rev * 100, 1) if (gp and rev) else None,
            "om": round(op / rev * 100, 1) if (op and rev) else None,
            "eps": eps,
        })

    by_ym = {(d["year"], d["month"]): d["revenue"] for d in m_list}
    monthly_series = []
    for d in m_list:
        last_y = by_ym.get((d["year"] - 1, d["month"]))
        yoy = round((d["revenue"] - last_y) / last_y * 100, 1) if last_y and last_y > 0 else None
        monthly_series.append({
            "d": d["date"][:7],
            "rev": round(d["revenue"] / 1e8, 2),
            "yoy": yoy,
        })

    by_q = {d["d"]: d["rev"] for d in q_list if d["rev"]}
    for d in q_list:
        if not d["rev"]:
            d["yoy"] = None
            continue
        try:
            y, m, day = d["d"].split("-")
            last_q = f"{int(y)-1}-{m}-{day}"
            ly = by_q.get(last_q)
            d["yoy"] = round((d["rev"] - ly) / ly * 100, 1) if ly else None
        except Exception:
            d["yoy"] = None

    summary = {}
    if monthly_series:
        recent = [m for m in monthly_series[-12:] if m["yoy"] is not None]
        if recent:
            summary["latest_month"] = recent[-1]["d"]
            summary["latest_month_yoy"] = recent[-1]["yoy"]
            streak = 0
            for m in reversed(recent):
                if m["yoy"] is not None and m["yoy"] > 0:
                    streak += 1
                else:
                    break
            summary["consecutive_growth_months"] = streak
            yoys = [m["yoy"] for m in recent if m["yoy"] is not None]
            summary["avg_yoy_12m"] = round(sum(yoys) / len(yoys), 1) if yoys else None
    if q_list:
        latest = next((q for q in reversed(q_list) if q["rev"]), None)
        if latest:
            summary["latest_quarter"] = latest["d"]
            summary["latest_quarter_yoy"] = latest.get("yoy")
            summary["latest_gm"] = latest["gm"]
            summary["latest_om"] = latest["om"]
            summary["latest_eps"] = latest["eps"]
        recent_gm = [q["gm"] for q in q_list[-4:] if q["gm"] is not None]
        if len(recent_gm) >= 2:
            summary["gm_trend"] = round(recent_gm[-1] - recent_gm[0], 1)
        recent_eps = [q["eps"] for q in q_list[-4:] if q["eps"] is not None]
        if len(recent_eps) >= 2:
            summary["eps_change"] = round(recent_eps[-1] - recent_eps[0], 2)

    return {"summary": summary, "monthly": monthly_series[-12:], "quarterly": q_list[-8:]}

all_tickers = set(monthly_raw.keys()) | set(quarterly_raw.keys())
FINANCIALS = {t: build_summary(t) for t in sorted(all_tickers)}
print(f"處理 {len(FINANCIALS)} 檔")


# ─── Step 5: 寫到 data/financials.js（Level 2） ──────────
print("\n寫入 data/financials.js...")

BACKUP_DIR.mkdir(exist_ok=True)
backup_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

# 備份現有的 financials.js
if FINANCIALS_OUTPUT.exists():
    backup_path = BACKUP_DIR / f"financials_{backup_ts}.js"
    backup_path.write_text(FINANCIALS_OUTPUT.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"✓ 已備份舊版 → {backup_path.name}")

# 寫新版（保留 Level 2 格式：window.PULSE_FINANCIALS = ...）
js_content = (
    "// FinMind 財務動能 — 由 update_financials.py 自動更新，不要手改\n"
    f"// Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    f"// Tickers: {len(FINANCIALS)} 檔\n"
    "window.PULSE_FINANCIALS = "
    + json.dumps(FINANCIALS, ensure_ascii=False, separators=(',', ':'))
    + ";\n"
)
FINANCIALS_OUTPUT.write_text(js_content, encoding="utf-8")
print(f"✓ 寫入 {FINANCIALS_OUTPUT}")


# ─── Step 6: 更新摘要 ─────────────────────────────────
print("\n" + "=" * 60)
print("本次更新摘要")
print("=" * 60)

latest_months = [f["summary"].get("latest_month") for f in FINANCIALS.values() if f["summary"].get("latest_month")]
if latest_months:
    print(f"最新月營收涵蓋至：{max(latest_months)}")

ranked = sorted(FINANCIALS.items(), key=lambda kv: kv[1]["summary"].get("latest_month_yoy") or -999, reverse=True)
print("\n🔥 最新月 YoY 前 10：")
for t, f in ranked[:10]:
    s = f["summary"]
    yoy = s.get('latest_month_yoy')
    yoy_str = f"{yoy:+}%" if yoy is not None else "N/A"
    cgm = s.get('consecutive_growth_months', 0)
    print(f"  {t}: {s.get('latest_month')} YoY {yoy_str} 連 {cgm} 月")

declining = [(t, f) for t, f in FINANCIALS.items() if (f["summary"].get("latest_month_yoy") or 0) < 0]
if declining:
    print(f"\n📉 衰退中（最新月 YoY < 0）: {len(declining)} 檔")
    for t, f in declining[:5]:
        s = f["summary"]
        print(f"  {t}: YoY {s['latest_month_yoy']:+}%")

if skipped:
    print(f"\n⚠️  {len(skipped)} 個 dataset 失敗（多半是興櫃股或被淘汰股）")

print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完成 ✅")
print(f"→ 重新整理 pulse.html 看新資料")
