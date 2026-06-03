# Pulse 選股工具（Level 2 資料分離架構）

## 📁 檔案結構

```
產業篩選建置/
├── pulse.html              ← 主網頁（雙擊開）
├── data/
│   ├── themes.js           ← 6 個題材
│   ├── stocks.js           ← 48 檔個股
│   ├── signals.js          ← 跨點訊號矩陣
│   ├── timeline.js         ← 時序軸
│   └── financials.js       ← FinMind 財務動能（91 檔）
├── scripts/
│   ├── update_financials.py    ← 每月跑：抓 FinMind 月營收 + 季財報
│   ├── apply_patch.py          ← 套用 Claude 給的 JSON patch
│   └── monthly_update.py       ← 一鍵月度更新（跑前 2 個）
└── README.md
```

---

## 🚀 使用方式

### 1. 開啟網頁
**雙擊 `pulse.html`**，Chrome 自動開啟。**不需要伺服器**。

### 2. 每月更新財務動能（自動）
```bash
cd scripts
python update_financials.py
```
完成後重新整理 `pulse.html` 即可看到最新數據。

或用一鍵腳本：
```bash
python scripts/monthly_update.py
```

### 3. 手動改個股 / TP / 評等
直接編輯 `data/stocks.js`，找到那檔個股的 `{ ticker:'XXXX', ... }`，改完存檔。重新整理網頁立刻生效。

範例：把 3653 健策 TP 改成 4270
```js
{ ticker:'3653', name:'健策', ...,
  yuanta_rating:'買進', yuanta_tp:4270,   // ← 改這個
  ...
}
```

### 4. 套用 Claude 給的 patch
當 Claude 升等 mapping 後給你 JSON patch：
```bash
python scripts/apply_patch.py path/to/patch.json
```

---

## 📝 個股結構（stocks.js）

每檔個股的欄位：
```js
{
  ticker: '8299',                  // 股票代碼（主鍵）
  name: '群聯',                     // 公司名稱
  themes: ['ai_server', 'memory'], // 跨題材（陣列）
  confidence: '🟢',                // 信心：🟢 STRONG / 🟡 MEDIUM / ⚪ WEAK
  score: 12,                       // 綜合分數
  role: 'L4 NAND 模組 — ...',       // 在產業鏈的角色
  customers: 'Micron / Kioxia',    // 主要客戶
  huitai: false,                   // 是否輝台宴點名
  yuanta_rating: '買進',            // 元大評等
  yuanta_tp: 2400,                 // 元大目標價（null 表示未評等）
  key_signals: '3 月單日 NAND +50%...', // 關鍵訊號
  transcript: '群聯 5/8 + 3/6 + 8/14',  // 法說會來源
  mock_price: 1845,                // mock 即時數據（之後接 FinMind API）
  mock_change: 5.42,
  mock_vol: 42.3,
}
```

---

## 🆕 加新個股

在 `data/stocks.js` 內找到 `];`（陣列結尾），在前面加一筆：
```js
  // ... 既有個股 ...

  { ticker:'3530', name:'采鈺', themes:['ai_pc'], confidence:'🟡', score:5,
    role:'AI PC 影像感測',
    customers:'NB 品牌', huitai:false,
    yuanta_rating:'未評等', yuanta_tp:null,
    key_signals:'...',
    transcript:'待補',
    mock_price: 0, mock_change: 0, mock_vol: 0 }
];
```

注意：**最後一筆不能有逗號**，倒數第二筆要有。

---

## 🎨 加新題材

編輯 `data/themes.js`：
```js
  { id:'ai_pc', name:'AI PC', version:'V1', count:9, strong:5,
    color:'bg-violet-50', icon:'💻',
    catalyst:'...',
    desc:'...' }
```

`id` 是主鍵，個股的 `themes` 陣列要用同樣的 id 才能正確篩選。

---

## 🐛 常見問題

### Q: 改了 data/*.js 但網頁沒變化
A: 強制重新整理（Ctrl+Shift+R）清快取，或關掉再開。

### Q: 跑 update_financials.py 後網頁壞掉
A: 檢查 `data/financials.js` 第一行是不是 `window.PULSE_FINANCIALS = `。如果是 `const FINANCIALS = ` 就是 update_financials.py 沒升級到 Level 2 版本，要改。

### Q: 想把網頁分享給朋友看
A: 把整個 `產業篩選建置/` 資料夾 zip 給他，或上傳 GitHub 用 GitHub Pages 免費 host（教學另附）。

---

## 🔄 更新工作流程

### 每月例行（你自己做，5 分鐘）
1. 跑 `python scripts/monthly_update.py`
2. 重新整理網頁
3. 看「財務動能榜」是否有新訊號

### 季報後 / 拿到新研報（找 Claude）
1. 把法說會逐字稿或研報 PDF 給 Claude
2. Claude 萃取訊號 → 給你 JSON patch
3. 你跑 `python scripts/apply_patch.py patch.json`
4. 重新整理網頁

### 開新題材（找 Claude）
1. 告訴 Claude 「我想開 X 題材 V1」
2. Claude 做完 mapping + 給你 JSON patch
3. 你套用 patch
4. 重新整理網頁

---

## 📦 升級到雲端（GitHub Pages）

當你想讓網頁「永遠在線可分享」：
1. 開 GitHub 帳號
2. 建 repo 名稱 `stock-screener`
3. 把整個資料夾推上去
4. Settings → Pages → 啟用
5. 5 分鐘後拿到網址 `https://你的帳號.github.io/stock-screener/`

之後每次更新 → `git add . && git commit -m "update" && git push` → 網頁自動更新。

詳細步驟另附文件（要再來找 Claude 寫）。
