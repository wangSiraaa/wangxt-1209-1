#!/usr/bin/env python3
"""缺陷复核与并网冻结逻辑回归测试

重点验证：
1. AI标注员可以成功创建裂纹、雷击点、结冰三类缺陷
2. 创建缺陷时自动冻结对应机组并网
3. 缺陷等级升高时稳定冻结并网
4. 维修关闭后正确解冻并网
5. 并网确认后自动创建下一次pending记录
6. 同一机组不会出现多条非confirmed记录（数据库约束+应用层逻辑）
7. 追溯查询返回完整的照片、缺陷、时间线
"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:19509/api"

INSPECTOR = "50ccedbb-d3af-48a8-b486-d258064c7f4e"
ANNOTATOR = "3b9e4bda-2671-4b62-afca-eb43b3d56649"
SUPERVISOR = "36e7db33-d512-4eb9-8825-4126ddc54d42"
TURBINE = "3d158af8-3c00-442d-bd44-5deab5877e07"

JPEG_BYTES = bytes([
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
    0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
    0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
    0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
    0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
    0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
    0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
    0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
    0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
    0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
    0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
    0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
    0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
    0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
    0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
    0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
    0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
    0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
    0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
    0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
    0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
    0x00, 0x00, 0x3F, 0x00, 0x7B, 0x40, 0x1B, 0xFF, 0xD9
])

passed = 0
failed = 0


def api(method, path, data=None, user_id=None, is_form=False):
    url = f"{BASE}{path}"
    headers = {}
    if user_id:
        headers["X-User-Id"] = user_id
    if data is not None and not is_form:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    elif is_form:
        body = data
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = err_body
        return e.code, err_json


def upload_photo(inspection_id, blade_no, side, user_id):
    boundary = "----testboundary12345"
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"blade_no\"\r\n\r\n{blade_no}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"side\"\r\n\r\n{side}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"blade{blade_no}_{side}.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode())
    parts.append(JPEG_BYTES)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    form_data = b"".join(parts)
    url = f"{BASE}/inspections/{inspection_id}/photos"
    req = urllib.request.Request(url, data=form_data, headers={
        "X-User-Id": user_id,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} — {detail}")


def get_active_grid_count(turbine_id, user_id=SUPERVISOR):
    """获取指定机组非confirmed状态的并网记录数量"""
    status, grids = api("GET", f"/grid-connections?turbine_id={turbine_id}", user_id=user_id)
    if status != 200 or not isinstance(grids, list):
        return -1
    return len([g for g in grids if g.get("status") != "confirmed"])


def get_active_grid(turbine_id, user_id=SUPERVISOR):
    """获取指定机组最新的非confirmed并网记录"""
    status, grids = api("GET", f"/grid-connections?turbine_id={turbine_id}", user_id=user_id)
    if status != 200 or not isinstance(grids, list):
        return None
    active = [g for g in grids if g.get("status") != "confirmed"]
    active.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return active[0] if active else None


print("\n" + "="*70)
print("缺陷复核与并网冻结逻辑 — 回归测试")
print("="*70)

SIDES = ["pressure", "suction", "leading"]

# ============================================================
# 前置：创建并提交一个巡检（三面照片齐全）
# ============================================================
print("\n📌 前置准备: 创建巡检并上传三面照片")
status, insp = api("POST", "/inspections", {
    "turbine_id": TURBINE,
    "inspection_date": "2026-06-21",
}, user_id=INSPECTOR)
check("创建巡检单", status == 200, f"status={status}, body={insp}")
inspection_id = insp.get("id") if status == 200 else None

# 上传全部9张照片
photo_ids = {}
for blade in [1, 2, 3]:
    for side in SIDES:
        s, p = upload_photo(inspection_id, blade, side, INSPECTOR)
        if s == 200:
            photo_ids[(blade, side)] = p.get("id")
check("上传全部9张照片", len(photo_ids) == 9, f"上传成功{len(photo_ids)}张")

# 提交巡检
status, result = api("POST", f"/inspections/{inspection_id}/submit", user_id=INSPECTOR)
check("提交巡检", status == 200, f"status={status}")

# ============================================================
# 测试1: 创建裂纹缺陷 (crack)
# ============================================================
print("\n📌 测试1: 创建裂纹缺陷（crack, L2）")
crack_photo_id = photo_ids.get((1, "leading"))
status, defect = api("POST", "/defects", {
    "inspection_id": inspection_id,
    "photo_id": crack_photo_id,
    "blade_no": 1,
    "side": "leading",
    "defect_type": "crack",
    "severity": "L2",
    "description": "前缘裂纹约5cm",
}, user_id=ANNOTATOR)
check("创建裂纹缺陷成功", status == 200, f"status={status}, body={defect}")
crack_defect_id = defect.get("id") if status == 200 else None

if status == 200:
    check("缺陷类型为crack", defect.get("defect_type") == "crack")
    check("缺陷等级为L2", defect.get("severity") == "L2")
    check("状态为open", defect.get("status") == "open")

# 验证并网冻结
active_grid = get_active_grid(TURBINE)
check("并网状态已冻结", active_grid and active_grid.get("status") == "frozen",
      f"status={active_grid.get('status') if active_grid else 'N/A'}")
if active_grid:
    check("冻结原因关联缺陷ID", active_grid.get("frozen_by_defect_id") == crack_defect_id)

# 验证同一机组只有1条非confirmed记录
active_count = get_active_grid_count(TURBINE)
check("同一机组仅有1条非confirmed并网记录", active_count == 1, f"实际有{active_count}条")

# ============================================================
# 测试2: 创建雷击点缺陷 (lightning)
# ============================================================
print("\n📌 测试2: 创建雷击点缺陷（lightning, L3）")
lightning_photo_id = photo_ids.get((2, "pressure"))
status, defect = api("POST", "/defects", {
    "inspection_id": inspection_id,
    "photo_id": lightning_photo_id,
    "blade_no": 2,
    "side": "pressure",
    "defect_type": "lightning",
    "severity": "L3",
    "description": "迎风面雷击点约8mm",
}, user_id=ANNOTATOR)
check("创建雷击点缺陷成功", status == 200, f"status={status}, body={defect}")
lightning_defect_id = defect.get("id") if status == 200 else None

if status == 200:
    check("缺陷类型为lightning", defect.get("defect_type") == "lightning")

# 验证并网仍然为冻结（更新冻结原因）
active_grid = get_active_grid(TURBINE)
check("并网保持冻结状态", active_grid and active_grid.get("status") == "frozen")
if active_grid:
    check("冻结原因更新为最新缺陷", active_grid.get("frozen_by_defect_id") == lightning_defect_id)

# 验证仍然只有1条非confirmed记录
active_count = get_active_grid_count(TURBINE)
check("仍然仅有1条非confirmed并网记录", active_count == 1, f"实际有{active_count}条")

# ============================================================
# 测试3: 创建结冰缺陷 (icing)
# ============================================================
print("\n📌 测试3: 创建结冰缺陷（icing, L1）")
icing_photo_id = photo_ids.get((3, "suction"))
status, defect = api("POST", "/defects", {
    "inspection_id": inspection_id,
    "photo_id": icing_photo_id,
    "blade_no": 3,
    "side": "suction",
    "defect_type": "icing",
    "severity": "L1",
    "description": "背风面轻微结冰",
}, user_id=ANNOTATOR)
check("创建结冰缺陷成功", status == 200, f"status={status}, body={defect}")
icing_defect_id = defect.get("id") if status == 200 else None

if status == 200:
    check("缺陷类型为icing", defect.get("defect_type") == "icing")

active_count = get_active_grid_count(TURBINE)
check("仍然仅有1条非confirmed并网记录", active_count == 1, f"实际有{active_count}条")

# ============================================================
# 测试4: 缺陷等级升高 L1→L4，验证稳定冻结
# ============================================================
print("\n📌 测试4: 缺陷等级升高 L1→L4，验证稳定冻结")
status, defect = api("PUT", f"/defects/{icing_defect_id}", {
    "severity": "L4",
    "description": "结冰扩展至整个叶片，等级升高至L4",
}, user_id=ANNOTATOR)
check("缺陷等级升至L4", status == 200, f"status={status}, body={defect}")
if status == 200:
    check("previous_severity记录为L1", defect.get("previous_severity") == "L1",
          f"prev={defect.get('previous_severity')}")
    check("当前severity为L4", defect.get("severity") == "L4")

# 验证并网冻结更新
active_grid = get_active_grid(TURBINE)
check("并网仍然冻结", active_grid and active_grid.get("status") == "frozen")
if active_grid:
    check("冻结原因更新为升级缺陷", active_grid.get("frozen_by_defect_id") == icing_defect_id)

active_count = get_active_grid_count(TURBINE)
check("仍然仅有1条非confirmed并网记录", active_count == 1, f"实际有{active_count}条")

# ============================================================
# 测试5: 尝试确认冻结的并网（应失败，423）
# ============================================================
print("\n📌 测试5: 尝试确认冻结的并网（应被拒绝）")
active_grid = get_active_grid(TURBINE)
if active_grid:
    grid_id = active_grid["id"]
    status, result = api("POST", f"/grid-connections/{grid_id}/confirm", user_id=SUPERVISOR)
    check("冻结状态下确认被拒绝", status == 423, f"status={status}, body={result}")
else:
    check("冻结状态下确认被拒绝", False, "未找到冻结的并网记录")

# ============================================================
# 测试6: 为升级缺陷创建维修单并关闭，验证解冻
# ============================================================
print("\n📌 测试6: 创建维修单并关闭，验证并网解冻")
status, repair = api("POST", "/repair-orders", {
    "defect_id": icing_defect_id,
    "decision": "repair",
}, user_id=SUPERVISOR)
check("创建维修单", status == 200, f"status={status}, body={repair}")
repair_id = repair.get("id") if status == 200 else None

status, repair = api("PUT", f"/repair-orders/{repair_id}/close", {
    "closure_notes": "结冰已清除，叶片表面恢复正常",
}, user_id=SUPERVISOR)
check("关闭维修单", status == 200, f"status={status}")
if status == 200:
    check("维修单状态为closed", repair.get("status") == "closed")

# 验证并网解冻
active_grid = get_active_grid(TURBINE)
check("并网状态恢复为pending", active_grid and active_grid.get("status") == "pending",
      f"status={active_grid.get('status') if active_grid else 'N/A'}")
if active_grid:
    check("frozen_reason已清空", active_grid.get("frozen_reason") is None)
    check("frozen_by_defect_id已清空", active_grid.get("frozen_by_defect_id") is None)

active_count = get_active_grid_count(TURBINE)
check("仍然仅有1条非confirmed并网记录", active_count == 1, f"实际有{active_count}条")

# ============================================================
# 测试7: 确认并网，验证自动创建下一次pending记录
# ============================================================
print("\n📌 测试7: 确认并网，验证自动创建下一次pending记录")
pending_grid = get_active_grid(TURBINE)
if pending_grid and pending_grid.get("status") == "pending":
    old_grid_id = pending_grid["id"]
    status, new_grid = api("POST", f"/grid-connections/{old_grid_id}/confirm", user_id=SUPERVISOR)
    check("确认并网成功", status == 200, f"status={status}, body={new_grid}")
    if status == 200:
        check("返回的是新的pending记录", new_grid.get("status") == "pending",
              f"status={new_grid.get('status')}")
        check("新记录ID与原记录不同", new_grid.get("id") != old_grid_id,
              f"new={new_grid.get('id')}, old={old_grid_id}")

    # 验证：旧记录已confirmed，新记录pending，总共只有1条非confirmed
    active_count = get_active_grid_count(TURBINE)
    check("仍然仅有1条非confirmed并网记录", active_count == 1, f"实际有{active_count}条")

    new_pending = get_active_grid(TURBINE)
    check("新记录为pending状态", new_pending and new_pending.get("status") == "pending")
else:
    check("确认并网成功", False, "未找到pending状态的并网记录")

# ============================================================
# 测试8: 追溯查询
# ============================================================
print("\n📌 测试8: 维修单追溯查询（原始照片+复核意见+时间线）")
status, trace = api("GET", f"/repair-orders/{repair_id}/trace", user_id=SUPERVISOR)
check("追溯查询成功", status == 200, f"status={status}")
if status == 200:
    check("包含维修单信息", trace.get("repair_order") is not None)
    check("包含关联缺陷信息", trace.get("defect") is not None)
    if trace.get("defect"):
        check("缺陷类型正确", trace["defect"].get("defect_type") == "icing")
        check("缺陷升级记录可追溯", trace["defect"].get("previous_severity") == "L1")
    check("包含原始照片（9张）", trace.get("photos") and len(trace["photos"]) == 9,
          f"照片数={len(trace.get('photos', []))}")
    check("包含同巡检所有缺陷（3个）", trace.get("defects") and len(trace["defects"]) == 3,
          f"缺陷数={len(trace.get('defects', []))}")
    check("包含审计时间线", trace.get("timeline") and len(trace["timeline"]) > 0,
          f"时间线条数={len(trace.get('timeline', []))}")

# ============================================================
# 测试9: 校验规则验证（负面测试）
# ============================================================
print("\n📌 测试9: 负面测试 - 校验规则")

# 尝试为draft状态的巡检创建缺陷
print("  9.1 尝试为draft巡检创建缺陷（应失败）")
status, draft_insp = api("POST", "/inspections", {
    "turbine_id": TURBINE,
    "inspection_date": "2026-06-21",
}, user_id=INSPECTOR)
if status == 200:
    draft_insp_id = draft_insp["id"]
    # 上传一张照片
    s, p = upload_photo(draft_insp_id, 1, "pressure", INSPECTOR)
    if s == 200:
        status, result = api("POST", "/defects", {
            "inspection_id": draft_insp_id,
            "photo_id": p["id"],
            "blade_no": 1,
            "side": "pressure",
            "defect_type": "crack",
            "severity": "L1",
        }, user_id=ANNOTATOR)
        check("draft巡检不能创建缺陷", status == 400, f"status={status}, body={result}")

# 尝试使用不属于该巡检的照片
print("  9.2 尝试使用不属于巡检的照片（应失败）")
status, result = api("POST", "/defects", {
    "inspection_id": inspection_id,
    "photo_id": p["id"],  # 来自另一个巡检的照片
    "blade_no": 1,
    "side": "pressure",
    "defect_type": "crack",
    "severity": "L1",
}, user_id=ANNOTATOR)
check("不属于巡检的照片被拒绝", status == 400, f"status={status}, body={result}")

# 尝试使用不匹配的叶片号/面
print("  9.3 尝试使用不匹配的叶片号（应失败）")
status, result = api("POST", "/defects", {
    "inspection_id": inspection_id,
    "photo_id": crack_photo_id,  # 叶片1前缘的照片
    "blade_no": 2,  # 故意写错
    "side": "leading",
    "defect_type": "crack",
    "severity": "L1",
}, user_id=ANNOTATOR)
check("叶片号不匹配被拒绝", status == 400, f"status={status}, body={result}")

# ============================================================
# 总结
# ============================================================
print("\n" + "="*70)
print(f"回归测试结果: ✅ {passed} 通过  ❌ {failed} 失败")
print("="*70)

if failed > 0:
    exit(1)
else:
    exit(0)
