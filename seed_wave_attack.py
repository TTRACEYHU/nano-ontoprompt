"""
多波次防空反导本体种子脚本 — 展示图谱动态变化

核心演示目标：
  - 实体增：新波次导弹在指定 tick 出现（节点出现）
  - 实体减：导弹被拦截后从图谱消失（节点消失）
  - 关系增：雷达发现目标 → DETECT 连线出现
  - 关系减：目标消失 → 关联连线消失

用法：python seed_wave_attack.py
"""

import requests, json, sys, math, uuid

BASE = "http://localhost:18020/api/v1"
V2 = "http://localhost:18020/api/v2"
H = {}

def login():
    global H
    r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "changeme123"})
    r.raise_for_status()
    H = {"Authorization": f"Bearer {r.json()['data']['access_token']}", "Content-Type": "application/json"}
    print("✓ 登录成功")

def create_ontology():
    r = requests.post(f"{BASE}/ontologies", headers=H, json={
        "name": f"多波次防空反导-{uuid.uuid4().hex[:4]}",
        "domain": "军事",
        "description": "展示图谱动态变化：三波次攻击，实体/关系随推演增减",
        "build_mode": "manual",
    })
    r.raise_for_status()
    oid = r.json()["data"]["id"]
    print(f"✓ 创建本体: {oid}")
    return oid

# ── ObjectType ──
type_ids = {}

def create_type(oid, name_cn, name_en, schema):
    r = requests.post(f"{V2}/ontologies/{oid}/object-types", headers=H, json={
        "name_cn": name_cn, "name_en": name_en, "property_schema": schema,
    })
    r.raise_for_status()
    tid = r.json()["data"]["id"]
    type_ids[name_en] = tid
    print(f"  + {name_cn} ({name_en})")

# ── ObjectInstance ──
instance_ids = {}

def create_instance(oid, type_name, name, props):
    r = requests.post(f"{V2}/ontologies/{oid}/object-instances", headers=H, json={
        "object_type_id": type_ids[type_name], "name_cn": name, "properties": props,
    })
    r.raise_for_status()
    iid = r.json()["data"]["id"]
    instance_ids[name] = iid

# ── LinkType ──
link_type_ids = {}

def create_link_type(oid, name_cn, name_en):
    r = requests.post(f"{V2}/ontologies/{oid}/link-types", headers=H, json={
        "name_cn": name_cn, "name_en": name_en, "property_schema": {},
    })
    r.raise_for_status()
    lid = r.json()["data"]["id"]
    link_type_ids[name_en] = lid
    print(f"  + {name_cn} ({name_en})")

# ── 构建本体 ──
def build():
    oid = create_ontology()

    print("\n--- ObjectType ---")
    create_type(oid, "预警雷达", "EarlyWarningRadar", {
        "latitude": {"type": "number"}, "longitude": {"type": "number"},
        "max_range_km": {"type": "number"}, "status": {"type": "string"},
    })
    create_type(oid, "中段拦截弹", "MidRangeInterceptor", {
        "latitude": {"type": "number"}, "longitude": {"type": "number"},
        "max_range_km": {"type": "number"}, "kill_prob_single": {"type": "number"},
        "ammo_count": {"type": "number"}, "fire_mode": {"type": "string"},
        "status": {"type": "string"},
    })
    create_type(oid, "近防炮", "CIWS", {
        "latitude": {"type": "number"}, "longitude": {"type": "number"},
        "max_range_km": {"type": "number"}, "kill_prob_single": {"type": "number"},
        "ammo_count": {"type": "number"}, "status": {"type": "string"},
    })
    create_type(oid, "弹道导弹", "BallisticMissile", {
        "latitude": {"type": "number"}, "longitude": {"type": "number"},
        "speed_mach": {"type": "number"}, "rcs": {"type": "number"},
        "direction_deg": {"type": "number"}, "status": {"type": "string"},
    })
    create_type(oid, "巡航导弹", "CruiseMissile", {
        "latitude": {"type": "number"}, "longitude": {"type": "number"},
        "speed_mach": {"type": "number"}, "rcs": {"type": "number"},
        "direction_deg": {"type": "number"}, "status": {"type": "string"},
    })
    create_type(oid, "高价值目标", "HighValueAsset", {
        "latitude": {"type": "number"}, "longitude": {"type": "number"},
        "value_score": {"type": "number"}, "protection_status": {"type": "string"},
    })

    print("\n--- ObjectInstance ---")
    create_instance(oid, "EarlyWarningRadar", "远程预警雷达", {
        "latitude": 31.25, "longitude": 121.50,
        "max_range_km": 500, "status": "standby",
    })
    create_instance(oid, "MidRangeInterceptor", "红旗-9发射车", {
        "latitude": 31.20, "longitude": 121.50,
        "max_range_km": 200, "kill_prob_single": 0.75,
        "ammo_count": 20, "fire_mode": "auto", "status": "standby",
    })
    create_instance(oid, "CIWS", "近防炮", {
        "latitude": 31.22, "longitude": 121.48,
        "max_range_km": 3, "kill_prob_single": 0.60,
        "ammo_count": 3000, "status": "standby",
    })
    create_instance(oid, "HighValueAsset", "政务中心", {
        "latitude": 31.23, "longitude": 121.47,
        "value_score": 100, "protection_status": "protected",
    })

    # 波次 1 的导弹（起始就存在）
    create_instance(oid, "BallisticMissile", "弹道导弹-W1-1", {
        "latitude": 32.50, "longitude": 122.50,
        "speed_mach": 8, "rcs": 0.5,
        "direction_deg": 225, "status": "flying",
    })
    create_instance(oid, "BallisticMissile", "弹道导弹-W1-2", {
        "latitude": 32.60, "longitude": 122.70,
        "speed_mach": 7.5, "rcs": 0.6,
        "direction_deg": 230, "status": "flying",
    })

    print("\n--- LinkType ---")
    create_link_type(oid, "探测流", "DETECT_FLOW")
    create_link_type(oid, "火力通道", "FIRE_CHANNEL")
    create_link_type(oid, "威胁流", "THREAT_FLOW")

    # ── 构建 spawn_schedule ──
    # 第二波：tick=3 出现 2 枚巡航导弹
    # 第三波：tick=6 出现 1 枚弹道导弹（突防）
    spawn_schedule = [
        {
            "tick": 3, "action": "spawn",
            "object_type_id": type_ids["CruiseMissile"],
            "name": "巡航导弹-W2-1",
            "properties": {
                "latitude": 32.40, "longitude": 123.00,
                "speed_mach": 0.8, "rcs": 0.15,
                "direction_deg": 240, "status": "flying",
            },
        },
        {
            "tick": 3, "action": "spawn",
            "object_type_id": type_ids["CruiseMissile"],
            "name": "巡航导弹-W2-2",
            "properties": {
                "latitude": 32.45, "longitude": 123.10,
                "speed_mach": 0.85, "rcs": 0.12,
                "direction_deg": 245, "status": "flying",
            },
        },
        {
            "tick": 6, "action": "spawn",
            "object_type_id": type_ids["BallisticMissile"],
            "name": "弹道导弹-W3",
            "properties": {
                "latitude": 32.80, "longitude": 123.20,
                "speed_mach": 9, "rcs": 0.3,
                "direction_deg": 220, "status": "flying",
            },
        },
    ]

    # ── 创建想定 ──
    participant_names = ["远程预警雷达", "红旗-9发射车", "近防炮", "政务中心",
                         "弹道导弹-W1-1", "弹道导弹-W1-2"]
    participant_ids = [instance_ids[n] for n in participant_names]

    initial_state = []
    template_props = {
        "远程预警雷达": {"latitude": 31.25, "longitude": 121.50, "max_range_km": 500, "status": "standby"},
        "红旗-9发射车": {"latitude": 31.20, "longitude": 121.50, "max_range_km": 200, "kill_prob_single": 0.75, "ammo_count": 20, "fire_mode": "auto", "status": "standby"},
        "近防炮": {"latitude": 31.22, "longitude": 121.48, "max_range_km": 3, "kill_prob_single": 0.60, "ammo_count": 3000, "status": "standby"},
        "政务中心": {"latitude": 31.23, "longitude": 121.47, "value_score": 100, "protection_status": "protected"},
        "弹道导弹-W1-1": {"latitude": 32.50, "longitude": 122.50, "speed_mach": 8, "rcs": 0.5, "direction_deg": 225, "status": "flying"},
        "弹道导弹-W1-2": {"latitude": 32.60, "longitude": 122.70, "speed_mach": 7.5, "rcs": 0.6, "direction_deg": 230, "status": "flying"},
    }
    for n in participant_names:
        iid = instance_ids.get(n)
        if iid and n in template_props:
            initial_state.append({"instance_id": iid, "initial_properties": dict(template_props[n])})

    payload = {
        "name": "三波次饱和攻击",
        "description": "三波次攻击：tick1 第一波2枚弹道导弹→tick3 第二波2枚巡航导弹→tick6 第三波1枚弹道导弹。"
                       "图谱变化：节点和连线随波次出现、随拦截消失。",
        "participant_instance_ids": participant_ids,
        "initial_state": initial_state,
        "spawn_schedule": spawn_schedule,
        "max_ticks": 50,
        "stop_condition": "max_ticks",
    }
    r = requests.post(f"{V2}/ontologies/{oid}/scenarios", headers=H, json=payload)
    r.raise_for_status()
    sid = r.json()["data"]["id"]
    print(f"\n✓ 创建想定: {sid[:8]} (spawn_schedule: {len(spawn_schedule)} 条)")

    # ── 创建方案 ──
    plans = [
        {
            "name": "自动拦截方案",
            "description": "引擎自动火力分配，逐波次拦截",
            "decisions": [
                {"trigger": "detected", "target": "interceptor", "action": "launch", "params": {"count": 2, "mode": "salvo"}},
                {"trigger": "intercept_success", "target": "", "action": "stop", "params": {}},
            ],
        },
    ]
    for p in plans:
        r = requests.post(f"{V2}/scenarios/{sid}/plans", headers=H, json={**p, "source": "manual"})
        if r.ok:
            print(f"  + 方案: {p['name']}")

    print(f"\n{'='*60}")
    print(f"✅ 多波次本体创建完成！")
    print(f"{'='*60}")
    print(f"  Ontology ID: {oid}")
    print(f"  Scenario ID: {sid}")
    print(f"  spawn_schedule: {len(spawn_schedule)} 条波次")
    print(f"\n📋 推演步骤:")
    print(f"  Tick 1: 第一波导弹被雷达探测 → DETECT 连线出现")
    print(f"  Tick 2: 火力通道建立 → FIRE_CHANNEL 连线出现")
    print(f"  Tick 3: 拦截命中 → 第一波节点/连线消失")
    print(f"          第二波巡航导弹出现 → 新节点 + DETECT 连线")
    print(f"  Tick 4-5: 第二波被拦截 → 节点/连线消失")
    print(f"  Tick 6: 第三波弹道导弹出现 → 新节点 + DETECT 连线")
    print(f"\n💡 访问: http://localhost:5173/simulation/{sid}?ontologyId={oid}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    login()
    build()
