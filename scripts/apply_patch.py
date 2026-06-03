"""
apply_patch.py — 套用 Claude 給的 JSON patch 到 data/*.js

用法：
    python apply_patch.py <patch.json>

JSON patch 格式範例：
{
  "target": "stocks",        // stocks / themes / signals / timeline
  "operations": [
    {
      "op": "update",         // update / add / delete
      "ticker": "8299",       // 主鍵（stocks 用 ticker, themes 用 id, signals 用 name, timeline 用 month）
      "fields": {             // 要更新的欄位（op=update 時用）
        "yuanta_tp": 2400,
        "score": 12
      }
    },
    {
      "op": "add",
      "data": {               // 完整 entry（op=add 時用）
        "ticker": "3530",
        "name": "采鈺",
        "themes": ["ai_pc"],
        ...
      }
    },
    {
      "op": "delete",
      "ticker": "1597"        // 主鍵
    }
  ]
}

設計理念：用「找+替換」操作 JS 物件文本，而不是 parse JS（因為 stocks.js 不是純 JSON 格式）
"""
import json
import sys
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'

# 各 target 的主鍵欄位
KEY_FIELDS = {
    'stocks': 'ticker',
    'themes': 'id',
    'signals': 'name',
    'timeline': 'month',
}


def load_data_file(target):
    """讀 data/<target>.js 內容（純文字）"""
    path = DATA_DIR / f'{target}.js'
    if not path.exists():
        raise FileNotFoundError(f"找不到 {path}")
    return path.read_text(encoding='utf-8'), path


def save_data_file(content, path):
    path.write_text(content, encoding='utf-8')


def find_entry_block(content, key_field, key_value):
    """
    找到 entry 物件的起訖位置。
    entry 結構：{ ticker:'XXXX', name:'XX', ... },
    回傳 (start_pos, end_pos) 或 None
    """
    # 構造正則：{ <key>:'<value>', ... }（可能跨多行，到 }, 結束）
    # 用 escape 處理特殊字元
    escaped_value = re.escape(key_value)
    pattern = re.compile(
        rf"  {{ {key_field}:'{escaped_value}',.*?\}}(?:,|\s*\n\];)",
        re.DOTALL
    )
    match = pattern.search(content)
    if not match:
        return None
    return match.start(), match.end()


def update_entry(target, key_value, fields):
    """更新某個 entry 的若干欄位"""
    content, path = load_data_file(target)
    key_field = KEY_FIELDS[target]

    block_range = find_entry_block(content, key_field, key_value)
    if not block_range:
        print(f"⚠️  找不到 {target} 內 {key_field}='{key_value}'")
        return False

    start, end = block_range
    block = content[start:end]

    # 對每個 field 做替換
    new_block = block
    for fname, fval in fields.items():
        # 構造正則匹配 fname:OLD_VALUE,
        # 處理 number / string / null / boolean / array
        new_val = format_js_value(fval)

        # 嘗試找到 fname: ... ,
        field_pattern = re.compile(
            rf"({re.escape(fname)}:)([^,\n}}]+)([,\n}}])",
        )
        m = field_pattern.search(new_block)
        if m:
            new_block = new_block[:m.start()] + f"{m.group(1)}{new_val}{m.group(3)}" + new_block[m.end():]
        else:
            print(f"  ⚠️ 在 {key_value} 內找不到欄位 {fname}（可能要手動加）")

    new_content = content[:start] + new_block + content[end:]
    save_data_file(new_content, path)
    print(f"✅ 更新 {target}/{key_value}: {list(fields.keys())}")
    return True


def format_js_value(v):
    """把 Python 值轉成 JS 字面量"""
    if v is None:
        return 'null'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        # 用單引號（跟現有風格一致）
        return "'" + v.replace("'", "\\'") + "'"
    if isinstance(v, list):
        return '[' + ','.join(format_js_value(x) for x in v) + ']'
    return repr(v)


def add_entry(target, data):
    """新增 entry 到 array 結尾（} 前）"""
    content, path = load_data_file(target)

    # 把 data dict 轉成 JS 物件文本
    js_obj = '  { ' + ', '.join(
        f"{k}:{format_js_value(v)}" for k, v in data.items()
    ) + ' }'

    # 找最後的 ]; 並在前面插入
    # 規則：在 \n]; 前加入 ,\n<js_obj>\n
    if '\n];' not in content:
        print(f"⚠️ {target}.js 結構不對")
        return False

    # 插在 ]; 前
    last_bracket_idx = content.rfind('\n];')
    new_content = content[:last_bracket_idx] + ',\n\n' + js_obj + content[last_bracket_idx:]
    save_data_file(new_content, path)
    print(f"✅ 新增 {target} 內 {data.get(KEY_FIELDS[target], '?')}")
    return True


def delete_entry(target, key_value):
    """刪除某個 entry"""
    content, path = load_data_file(target)
    key_field = KEY_FIELDS[target]
    block_range = find_entry_block(content, key_field, key_value)
    if not block_range:
        print(f"⚠️ 找不到 {target} 內 {key_field}='{key_value}'")
        return False
    start, end = block_range
    # 刪除整段 + 可能的前置 \n
    new_content = content[:start] + content[end:]
    # 清掉多餘空行
    new_content = re.sub(r'\n\n\n+', '\n\n', new_content)
    save_data_file(new_content, path)
    print(f"✅ 刪除 {target}/{key_value}")
    return True


def apply_patch(patch_file):
    with open(patch_file, encoding='utf-8') as f:
        patch = json.load(f)

    target = patch.get('target')
    if target not in KEY_FIELDS:
        print(f"❌ 不認識的 target: {target}")
        return

    key_field = KEY_FIELDS[target]
    success = 0
    fail = 0

    for op_obj in patch.get('operations', []):
        op = op_obj.get('op')
        if op == 'update':
            ok = update_entry(target, op_obj[key_field], op_obj['fields'])
        elif op == 'add':
            ok = add_entry(target, op_obj['data'])
        elif op == 'delete':
            ok = delete_entry(target, op_obj[key_field])
        else:
            print(f"❌ 不認識的 op: {op}")
            ok = False
        if ok:
            success += 1
        else:
            fail += 1

    print(f"\n結果：成功 {success} / 失敗 {fail}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python apply_patch.py <patch.json>")
        sys.exit(1)
    apply_patch(sys.argv[1])
