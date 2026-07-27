"""
手动防空反导本体种子脚本

基于人工决策链（Human-in-the-Loop）的防空反导指挥控制本体。
指挥层级：指挥所(Commander) → 雷达站/火力单元(Operators)
人工决策节点：探测→报告→请求开火→指挥员审批→执行拦截

用法：python seed_manual_air_defense.py
"""

import requests, json, sys, math, random, uuid, time

BASE = "http://localhost:18020/api/v1"
V2 = "http://localhost:18020/api/v2"
H = {}  # headers, filled after login

# ═══════════════════════════════════════════════════
# 1. 登录
# ═══════════════════════════════════════════════════

def login():
    global H
    r = requests.post(f"{BASE}/auth/login", json={"username": "admin", "password": "changeme123"})
    r.raise_for_status()
    token = r.json()["data"]["access_token"]
    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("✓ 登录成功")

# ═══════════════════════════════════════════════════
# 2. 创建本体项目
# ═══════════════════════════════════════════════════

def create_ontology():
    r = requests.post(f"{BASE}/ontologies", headers=H, json={
        "name": "手动防空反导",
        "domain": "军事",
        "description": "基于人工决策链（HITL）的防空反导指挥控制本体。\n"
                       "指挥体系：指挥所(指挥官) → 雷达站(操作员) / 火力单元(火控手)\n"
                       "人工节点：目标探测→操作员报告→火控手请求开火→指挥员审批→手动发射",
        "build_mode": "manual",
    })
    r.raise_for_status()
    oid = r.json()["data"]["id"]
    print(f"✓ 创建本体: {oid}")
    return oid

# ═══════════════════════════════════════════════════
# 3. 创建 ObjectType
# ═══════════════════════════════════════════════════

type_ids = {}

def create_object_type(oid, name_cn, name_en, property_schema):
    r = requests.post(f"{V2}/ontologies/{oid}/object-types", headers=H, json={
        "name_cn": name_cn,
        "name_en": name_en,
        "property_schema": property_schema,
    })
    r.raise_for_status()
    tid = r.json()["data"]["id"]
    type_ids[name_en] = tid
    print(f"  + ObjectType: {name_cn} ({name_en})")
    return tid

def create_types(oid):
    # 指挥控制层
    create_object_type(oid, "指挥所", "CommandPost", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "commander_name": {"type": "string"},
        "command_level": {"type": "number", "unit": "级"},
        "decision_mode": {"type": "string"},  # manual / semi_auto / auto
        "status": {"type": "string"},
    })
    create_object_type(oid, "雷达操作员", "RadarOperator", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "operator_name": {"type": "string"},
        "operator_status": {"type": "string"},  # ready / busy / offline
        "experience_level": {"type": "number", "unit": "级"},
        "max_track_targets": {"type": "number"},
    })
    create_object_type(oid, "火控手", "FireControlOfficer", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "operator_name": {"type": "string"},
        "operator_status": {"type": "string"},
        "fire_mode": {"type": "string"},  # manual / semi_auto
    })
    # 物理资产层
    create_object_type(oid, "预警雷达", "EarlyWarningRadar", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "max_range_km": {"type": "number", "unit": "km"},
        "tracking_capacity": {"type": "number", "unit": "批"},
        "scan_interval_ms": {"type": "number", "unit": "ms"},
        "detection_mode": {"type": "string"},  # auto / manual
        "status": {"type": "string"},
    })
    create_object_type(oid, "中段拦截弹", "MidRangeInterceptor", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "max_range_km": {"type": "number", "unit": "km"},
        "min_range_km": {"type": "number", "unit": "km"},
        "kill_prob_single": {"type": "number", "unit": "概率"},
        "ammo_count": {"type": "number", "unit": "发"},
        "max_altitude_km": {"type": "number", "unit": "km"},
        "speed_mach": {"type": "number", "unit": "Mach"},
        "fire_mode": {"type": "string"},  # manual(需审批) / semi / auto
        "status": {"type": "string"},
    })
    create_object_type(oid, "近防炮", "CIWS", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "max_range_km": {"type": "number", "unit": "km"},
        "kill_prob_single": {"type": "number", "unit": "概率"},
        "ammo_count": {"type": "number", "unit": "发"},
        "fire_rate_rpm": {"type": "number", "unit": "rpm"},
        "fire_mode": {"type": "string"},
        "status": {"type": "string"},
    })
    # 威胁层
    create_object_type(oid, "弹道导弹", "BallisticMissile", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "speed_mach": {"type": "number", "unit": "Mach"},
        "rcs": {"type": "number", "unit": "m²"},
        "warhead_type": {"type": "string"},
        "apogee_km": {"type": "number", "unit": "km"},
        "target_latitude": {"type": "number", "unit": "deg"},
        "target_longitude": {"type": "number", "unit": "deg"},
        "direction_deg": {"type": "number", "unit": "deg"},
        "status": {"type": "string"},
    })
    create_object_type(oid, "巡航导弹", "CruiseMissile", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "speed_mach": {"type": "number", "unit": "Mach"},
        "rcs": {"type": "number", "unit": "m²"},
        "flight_altitude_m": {"type": "number", "unit": "m"},
        "direction_deg": {"type": "number", "unit": "deg"},
        "status": {"type": "string"},
    })
    create_object_type(oid, "诱饵弹", "Decoy", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "speed_mach": {"type": "number", "unit": "Mach"},
        "rcs": {"type": "number", "unit": "m²"},
        "is_decoy": {"type": "boolean"},
        "direction_deg": {"type": "number", "unit": "deg"},
        "status": {"type": "string"},
    })
    create_object_type(oid, "高价值目标", "HighValueAsset", {
        "latitude": {"type": "number", "unit": "deg"},
        "longitude": {"type": "number", "unit": "deg"},
        "hardening_level": {"type": "number", "unit": "级"},
        "value_score": {"type": "number", "unit": "分"},
        "radius_m": {"type": "number", "unit": "m"},
        "protection_status": {"type": "string"},
    })
    print(f"  → 共 {len(type_ids)} 个 ObjectType")

# ═══════════════════════════════════════════════════
# 4. 创建 ObjectInstance（想定模板实例）
# ═══════════════════════════════════════════════════

instance_ids = {}  # name -> id

def create_instance(oid, type_name, name, properties, confidence=0.95):
    tid = type_ids[type_name]
    r = requests.post(f"{V2}/ontologies/{oid}/object-instances", headers=H, json={
        "object_type_id": tid,
        "name_cn": name,
        "properties": properties,
        "confidence": confidence,
    })
    r.raise_for_status()
    iid = r.json()["data"]["id"]
    instance_ids[name] = iid
    return iid

def create_instances(oid):
    # ── 指挥所 ──
    create_instance(oid, "CommandPost", "东区联合指挥所", {
        "latitude": 31.23, "longitude": 121.47,
        "commander_name": "张将军",
        "command_level": 1,
        "decision_mode": "manual",
        "status": "standby",
    })
    create_instance(oid, "RadarOperator", "预警雷达操作员-王", {
        "latitude": 31.25, "longitude": 121.50,
        "operator_name": "王少校",
        "operator_status": "ready",
        "experience_level": 5,
        "max_track_targets": 12,
    })
    create_instance(oid, "FireControlOfficer", "红旗-9火控手-李", {
        "latitude": 31.20, "longitude": 121.50,
        "operator_name": "李上尉",
        "operator_status": "ready",
        "fire_mode": "manual",
    })

    # ── 预警雷达 ──
    create_instance(oid, "EarlyWarningRadar", "远程预警雷达-A", {
        "latitude": 31.25, "longitude": 121.50,
        "max_range_km": 480,
        "tracking_capacity": 100,
        "scan_interval_ms": 2000,
        "detection_mode": "auto",
        "status": "standby",
    })

    # ── 拦截系统 ──
    create_instance(oid, "MidRangeInterceptor", "红旗-9A发射车", {
        "latitude": 31.20, "longitude": 121.50,
        "max_range_km": 200, "min_range_km": 5,
        "kill_prob_single": 0.75, "ammo_count": 16,
        "max_altitude_km": 30, "speed_mach": 6,
        "fire_mode": "manual",
        "status": "standby",
    })
    create_instance(oid, "MidRangeInterceptor", "红旗-9B发射车", {
        "latitude": 31.18, "longitude": 121.52,
        "max_range_km": 260, "min_range_km": 7,
        "kill_prob_single": 0.80, "ammo_count": 12,
        "max_altitude_km": 35, "speed_mach": 6.5,
        "fire_mode": "manual",
        "status": "standby",
    })
    create_instance(oid, "CIWS", "陆基近防炮-A", {
        "latitude": 31.22, "longitude": 121.48,
        "max_range_km": 3,
        "kill_prob_single": 0.65,
        "ammo_count": 3000,
        "fire_rate_rpm": 6000,
        "fire_mode": "auto",  # 近防炮通常自动，但可手动干预
        "status": "standby",
    })

    # ── 高价值目标 ──
    create_instance(oid, "HighValueAsset", "市中心政务区", {
        "latitude": 31.23, "longitude": 121.47,
        "hardening_level": 3,
        "value_score": 100,
        "radius_m": 5000,
        "protection_status": "protected",
    })

    # ── 威胁（弹道导弹） ──
    create_instance(oid, "BallisticMissile", "SS-21 来袭弹道导弹-1", {
        "latitude": 32.50, "longitude": 122.80,
        "speed_mach": 8, "rcs": 0.5,
        "warhead_type": "HE",
        "apogee_km": 120,
        "target_latitude": 31.23, "target_longitude": 121.47,
        "direction_deg": 225,
        "status": "flying",
    })
    create_instance(oid, "BallisticMissile", "SS-21 来袭弹道导弹-2", {
        "latitude": 32.60, "longitude": 122.90,
        "speed_mach": 7.5, "rcs": 0.6,
        "warhead_type": "HE",
        "apogee_km": 110,
        "target_latitude": 31.23, "target_longitude": 121.47,
        "direction_deg": 230,
        "status": "flying",
    })
    # ── 巡航空袭 ──
    create_instance(oid, "CruiseMissile", "鹰击-18 巡航导弹-1", {
        "latitude": 32.30, "longitude": 123.00,
        "speed_mach": 0.8, "rcs": 0.15,
        "flight_altitude_m": 50,
        "direction_deg": 240,
        "status": "flying",
    })
    create_instance(oid, "CruiseMissile", "鹰击-18 巡航导弹-2", {
        "latitude": 32.35, "longitude": 123.10,
        "speed_mach": 0.85, "rcs": 0.12,
        "flight_altitude_m": 45,
        "direction_deg": 245,
        "status": "flying",
    })
    # ── 诱饵 ──
    create_instance(oid, "Decoy", "诱饵弹-D1", {
        "latitude": 32.40, "longitude": 122.50,
        "speed_mach": 0.9, "rcs": 3.0,
        "is_decoy": True,
        "direction_deg": 220,
        "status": "flying",
    })
    create_instance(oid, "Decoy", "诱饵弹-D2", {
        "latitude": 32.45, "longitude": 122.70,
        "speed_mach": 0.85, "rcs": 2.5,
        "is_decoy": True,
        "direction_deg": 235,
        "status": "flying",
    })

    print(f"  → 共 {len(instance_ids)} 个 ObjectInstance")

# ═══════════════════════════════════════════════════
# 5. 创建 LinkType
# ═══════════════════════════════════════════════════

link_type_ids = {}

def create_link_type(oid, name_cn, name_en, property_schema=None):
    r = requests.post(f"{V2}/ontologies/{oid}/link-types", headers=H, json={
        "name_cn": name_cn,
        "name_en": name_en,
        "property_schema": property_schema or {},
    })
    r.raise_for_status()
    lid = r.json()["data"]["id"]
    link_type_ids[name_en] = lid
    print(f"  + LinkType: {name_cn} ({name_en})")
    return lid

def create_link_types(oid):
    create_link_type(oid, "指挥链", "COMMAND_CHAIN", {
        "authority_level": {"type": "number"},
        "command_type": {"type": "string"},
        "issued_at_tick": {"type": "number"},
        "status": {"type": "string"},  # active / revoked
    })
    create_link_type(oid, "情报上报", "REPORT_UP", {
        "report_type": {"type": "string"},  # detection / status / urgent
        "report_time_ms": {"type": "number"},
        "priority": {"type": "number"},
        "content": {"type": "string"},
        "status": {"type": "string"},
    })
    create_link_type(oid, "探测流", "DETECT_FLOW", {
        "snr": {"type": "number"},
        "distance_km": {"type": "number"},
        "is_locked": {"type": "boolean"},
        "lock_quality": {"type": "number"},
        "detected_at_tick": {"type": "number"},
    })
    create_link_type(oid, "火力通道", "FIRE_CHANNEL", {
        "time_to_intercept_ms": {"type": "number"},
        "p_kill": {"type": "number"},
        "ammo_assigned": {"type": "number"},
        "salvo_count": {"type": "number"},
        "status": {"type": "string"},  # requested / approved / guiding / hit / miss
    })
    create_link_type(oid, "威胁流", "THREAT_FLOW", {
        "leak_probability": {"type": "number"},
        "estimated_damage": {"type": "number"},
        "time_to_impact_ms": {"type": "number"},
        "threat_level": {"type": "string"},
    })
    create_link_type(oid, "开火请求", "FIRE_REQUEST", {
        "target_id": {"type": "string"},
        "target_distance_km": {"type": "number"},
        "requested_salvo": {"type": "number"},
        "urgency": {"type": "string"},
        "status": {"type": "string"},  # pending / approved / denied
    })
    create_link_type(oid, "开火命令", "FIRE_ORDER", {
        "approved_by": {"type": "string"},
        "salvo_authorized": {"type": "number"},
        "engagement_rule": {"type": "string"},
        "issued_at_tick": {"type": "number"},
        "status": {"type": "string"},  # issued / executed / cancelled
    })
    create_link_type(oid, "隶属", "ASSIGNED_TO", {
        "assignment_type": {"type": "string"},
        "assigned_at_tick": {"type": "number"},
        "status": {"type": "string"},
    })
    print(f"  → 共 {len(link_type_ids)} 个 LinkType")

# ═══════════════════════════════════════════════════
# 6. 创建 ObjectRule
# ═══════════════════════════════════════════════════

rule_ids = {}

def create_rule(oid, name_cn, python_code, type_name=None, inst_name=None):
    payload = {"name_cn": name_cn, "python_code": python_code}
    if type_name:
        payload["object_type_id"] = type_ids[type_name]
    if inst_name:
        payload["object_instance_id"] = instance_ids[inst_name]
    r = requests.post(f"{V2}/ontologies/{oid}/rules", headers=H, json=payload)
    r.raise_for_status()
    rid = r.json()["id"]
    rule_ids[name_cn] = rid
    print(f"  + Rule: {name_cn}")
    return rid

def create_rules(oid):
    # 规则1：雷达自动探测（操作员远程雷达自动扫描）
    create_rule(oid, "雷达探测规则", """import math

def check(context):
    radar_lat = context.get("latitude", 0)
    radar_lon = context.get("longitude", 0)
    radar_range = context.get("max_range_km", 0)
    capacity = context.get("tracking_capacity", 0)
    scan_mode = context.get("detection_mode", "auto")

    threats = []
    for other in context.get("all_instances", []):
        props = other.get("properties", {})
        ot_name = other.get("type_name_en", "")
        if ot_name in ("BallisticMissile", "CruiseMissile", "Decoy") and props.get("status") != "destroyed":
            dlat = math.radians(props.get("latitude", 0) - radar_lat)
            dlon = math.radians(props.get("longitude", 0) - radar_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(radar_lat)) * math.cos(math.radians(props.get("latitude", 0))) * math.sin(dlon/2)**2
            dist_km = 6371 * 2 * math.asin(math.sqrt(a))
            if dist_km <= radar_range:
                rcs = props.get("rcs", 1.0)
                snr = (rcs / (dist_km ** 2 + 1)) * 5000
                is_locked = snr > 3.0
                threats.append({
                    "instance_id": other.get("instance_id"),
                    "instance_name": other.get("instance_name"),
                    "type_name_en": ot_name,
                    "distance_km": round(dist_km, 2),
                    "snr": round(snr, 2),
                    "is_locked": is_locked,
                })

    threats.sort(key=lambda x: x["snr"], reverse=True)
    locked = threats[:capacity]

    links_to_create = []
    for t in locked:
        if t["is_locked"]:
            links_to_create.append({
                "link_type": "DETECT_FLOW",
                "source_instance_id": context.get("instance_id"),
                "target_instance_id": t["instance_id"],
                "properties": {
                    "snr": t["snr"],
                    "distance_km": t["distance_km"],
                    "is_locked": True,
                    "lock_quality": min(1.0, t["snr"] / 20),
                    "detected_at_tick": context.get("tick", 0),
                }
            })

    return {
        "passed": len(locked) > 0,
        "message": f"〔操作员报告〕雷达探测到 {len(threats)} 个目标，锁定 {len(locked)} 个",
        "links_to_create": links_to_create,
        "properties_update": {"status": "tracking" if locked else "scanning"},
    }
""", type_name="EarlyWarningRadar")

    # 规则2：火控手手动请求开火（人工决策节点）
    create_rule(oid, "火控请求规则", """import math

def check(context):
    launcher_lat = context.get("latitude", 0)
    launcher_lon = context.get("longitude", 0)
    max_range = context.get("max_range_km", 0)
    min_range = context.get("min_range_km", 0)
    ammo = context.get("ammo_count", 0)
    fire_mode = context.get("fire_mode", "manual")
    operator_status = context.get("status", "standby")

    if ammo <= 0:
        return {"passed": False, "message": "弹药耗尽，无法开火"}
    if fire_mode != "manual":
        return {"passed": False, "message": "非手动模式，由自动化系统处理"}
    if operator_status != "standby":
        return {"passed": False, "message": "火控手未就绪"}

    # 查找已探测到的目标（通过 DETECT_FLOW 链路）
    detected_targets = []
    for rel in context.get("related_instances", []):
        rel_props = rel.get("properties", {})
        link_type = rel.get("link_type_id", "")
        if "DETECT" in str(link_type) and rel_props.get("is_locked"):
            detected_targets.append(rel)

    # 如果没有关联探测，遍历所有实例
    if not detected_targets:
        for other in context.get("all_instances", []):
            props = other.get("properties", {})
            ot_name = other.get("type_name_en", "")
            if ot_name in ("BallisticMissile", "CruiseMissile") and props.get("status") != "destroyed":
                t_lat, t_lon = props.get("latitude", 0), props.get("longitude", 0)
                dlat = math.radians(t_lat - launcher_lat)
                dlon = math.radians(t_lon - launcher_lon)
                a = math.sin(dlat/2)**2 + math.cos(math.radians(launcher_lat)) * math.cos(math.radians(t_lat)) * math.sin(dlon/2)**2
                dist_km = 6371 * 2 * math.asin(math.sqrt(a))
                if min_range <= dist_km <= max_range:
                    detected_targets.append({
                        "instance_id": other.get("instance_id"),
                        "instance_name": other.get("instance_name"),
                        "distance_km": round(dist_km, 2),
                    })

    if not detected_targets:
        return {"passed": False, "message": "〔火控手报告〕射程内无锁定目标"}

    # 火控手选择最近目标请求开火
    detected_targets.sort(key=lambda x: x.get("distance_km", 99999))
    target = detected_targets[0]

    # 提醒：操作员需手动审批（链接创建后需人工确认 /confirm-links）
    links_to_create = [{
        "link_type": "FIRE_REQUEST",
        "source_instance_id": context.get("instance_id"),
        "target_instance_id": target["instance_id"],
        "properties": {
            "target_id": target["instance_id"],
            "target_distance_km": target.get("distance_km", 0),
            "requested_salvo": min(2, ammo),
            "urgency": "high",
            "status": "pending",
        }
    }]

    return {
        "passed": True,
        "message": f"〔火控手李上尉请求开火〕目标「{target.get('instance_name','')}」距离 {target.get('distance_km',0):.0f}km，请求齐射2发，请指挥员审批！",
        "links_to_create": links_to_create,
        "properties_update": {"status": "requesting"},
    }
""", type_name="MidRangeInterceptor")

    # 规则3：指挥员决策规则（收到开火请求后）
    create_rule(oid, "指挥员审批规则", """def check(context):
    decision_mode = context.get("decision_mode", "manual")
    commander_status = context.get("status", "standby")

    if commander_status != "standby":
        return {"passed": False, "message": "指挥员繁忙"}

    # 检查是否有待审批的开火请求
    pending_requests = []
    for rel in context.get("related_instances", []):
        rel_props = rel.get("properties", {})
        if "FIRE_REQUEST" in str(rel.get("link_type_id", "")) and rel_props.get("status") == "pending":
            pending_requests.append(rel)

    if not pending_requests:
        return {"passed": False, "message": "无敌对开火请求"}

    # 指挥员选择第一个请求审批
    req = pending_requests[0]
    req_props = req.get("properties", {})

    # 获取火控手信息和目标信息
    requester_name = req.get("instance_name", "火控手")
    target_name = req_props.get("target_id", "未知目标")

    # 在 manual 模式下，指挥员的审批需要手动确认
    # 这里通过创建 FIRE_ORDER 来表达指挥员的批准决定
    links_to_create = [{
        "link_type": "FIRE_ORDER",
        "source_instance_id": context.get("instance_id"),
        "target_instance_id": req.get("instance_id"),
        "properties": {
            "approved_by": context.get("commander_name", "张将军"),
            "salvo_authorized": req_props.get("requested_salvo", 2),
            "engagement_rule": "standard",
            "issued_at_tick": context.get("tick", 0),
            "status": "issued",
        }
    }]

    return {
        "passed": True,
        "message": f"〔指挥员命令〕张将军已批准开火请求，授权发射 {req_props.get('requested_salvo',2)} 发！",
        "links_to_create": links_to_create,
        "properties_update": {"status": "commanding"},
    }
""", type_name="CommandPost")

    # 规则4：威胁评估（目标到 HVA 的距离评估）
    create_rule(oid, "威胁评估规则", """import math

def check(context):
    hva_lat = context.get("latitude", 0)
    hva_lon = context.get("longitude", 0)
    hva_radius = context.get("radius_m", 5000)
    
    threats_nearby = []
    for other in context.get("all_instances", []):
        props = other.get("properties", {})
        ot_name = other.get("type_name_en", "")
        if ot_name in ("BallisticMissile", "CruiseMissile", "Decoy") and props.get("status") != "destroyed":
            t_lat, t_lon = props.get("latitude", 0), props.get("longitude", 0)
            dlat = math.radians(t_lat - hva_lat)
            dlon = math.radians(t_lon - hva_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(hva_lat)) * math.cos(math.radians(t_lat)) * math.sin(dlon/2)**2
            dist_m = 6371000 * 2 * math.asin(math.sqrt(a))
            if dist_m < 500000:  # 500km 以内
                time_to_impact_ms = int(dist_m / (props.get("speed_mach", 1) * 343) * 1000)
                threats_nearby.append({
                    "instance_id": other.get("instance_id"),
                    "instance_name": other.get("instance_name"),
                    "distance_m": dist_m,
                    "time_to_impact_ms": time_to_impact_ms,
                })

    if not threats_nearby:
        return {"passed": False, "message": "警戒范围内无威胁目标"}

    links_to_create = []
    for t in threats_nearby:
        level = "critical" if t["distance_m"] < 100000 else ("high" if t["distance_m"] < 300000 else "medium")
        links_to_create.append({
            "link_type": "THREAT_FLOW",
            "source_instance_id": t["instance_id"],
            "target_instance_id": context.get("instance_id"),
            "properties": {
                "threat_level": level,
                "distance_m": t["distance_m"],
                "time_to_impact_ms": t["time_to_impact_ms"],
                "estimated_damage": 0.8 if level == "critical" else (0.5 if level == "high" else 0.2),
            }
        })

    threat_count = len(threats_nearby)
    critical_count = sum(1 for t in threats_nearby if t["distance_m"] < 100000)
    return {
        "passed": True,
        "message": f"〔态势评估〕发现 {threat_count} 个威胁目标，其中 {critical_count} 个临界威胁！",
        "links_to_create": links_to_create,
        "properties_update": {"protection_status": "under_attack" if critical_count > 0 else "monitoring"},
    }
""", type_name="HighValueAsset")

    # 规则5：近防炮自动拦截（末段自动防御）
    create_rule(oid, "近防炮自动拦截规则", """import math

def check(context):
    ciws_lat = context.get("latitude", 0)
    ciws_lon = context.get("longitude", 0)
    max_range = context.get("max_range_km", 0) * 1000
    ammo = context.get("ammo_count", 0)
    fire_mode = context.get("fire_mode", "auto")

    if ammo <= 0:
        return {"passed": False, "message": "近防炮弹药耗尽"}

    # 找距离最近的未摧毁威胁
    closest = None
    closest_dist = 999999
    for other in context.get("all_instances", []):
        props = other.get("properties", {})
        ot_name = other.get("type_name_en", "")
        if ot_name in ("BallisticMissile", "CruiseMissile") and props.get("status") not in ("destroyed", "intercepted"):
            t_lat, t_lon = props.get("latitude", 0), props.get("longitude", 0)
            dlat = math.radians(t_lat - ciws_lat)
            dlon = math.radians(t_lon - ciws_lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(ciws_lat)) * math.cos(math.radians(t_lat)) * math.sin(dlon/2)**2
            dist_m = 6371000 * 2 * math.asin(math.sqrt(a))
            if dist_m <= max_range and dist_m < closest_dist:
                closest = other
                closest_dist = dist_m

    if not closest:
        return {"passed": False, "message": "近防炮射程内无目标"}

    p_kill = context.get("kill_prob_single", 0.6)
    fire_rate = context.get("fire_rate_rpm", 6000)
    # 每 tick 消耗约 100 发
    ammo_per_tick = min(100, ammo)

    links_to_create = [{
        "link_type": "FIRE_CHANNEL",
        "source_instance_id": context.get("instance_id"),
        "target_instance_id": closest["instance_id"],
        "properties": {
            "status": "guiding",
            "time_to_intercept_ms": 500,
            "p_kill": p_kill,
            "ammo_assigned": ammo_per_tick,
            "salvo_count": 1,
        }
    }]

    return {
        "passed": True,
        "message": f"〔近防炮自动开火〕拦截目标 {closest.get('instance_name','')} 距离 {closest_dist:.0f}m",
        "links_to_create": links_to_create,
        "properties_update": {"ammo_count": ammo - ammo_per_tick, "status": "firing"},
    }
""", type_name="CIWS")

    print(f"  → 共 {len(rule_ids)} 条规则")

# ═══════════════════════════════════════════════════
# 7. 创建 ObjectAction
# ═══════════════════════════════════════════════════

action_ids = {}

def create_action(oid, name_cn, python_code, type_name=None, inst_name=None, rule_name=None):
    payload = {"name_cn": name_cn, "python_code": python_code}
    if type_name:
        payload["object_type_id"] = type_ids[type_name]
    if inst_name:
        payload["object_instance_id"] = instance_ids[inst_name]
    if rule_name:
        payload["object_rule_id"] = rule_ids[rule_name]
    r = requests.post(f"{V2}/ontologies/{oid}/actions-v2", headers=H, json=payload)
    r.raise_for_status()
    aid = r.json()["id"]
    action_ids[name_cn] = aid
    print(f"  + Action: {name_cn}")
    return aid

def create_actions(oid):
    # 动作1：发射拦截弹（火控手执行开火命令）
    create_action(oid, "执行拦截弹发射", """import math, random

def execute(context):
    participants = context.get("participants", [])
    active_links = context.get("active_links", [])
    tick = context.get("tick", 0)
    db = context.get("db")

    results = []

    # 查找已审批的 FIRE_ORDER，对应的火力通道
    for link in active_links:
        props = link.get("properties", {})
        lt_name = link.get("link_type_name", "")
        if "FIRE_ORDER" in lt_name and props.get("status") == "issued":
            # 找到对应的发射车，创建火力通道
            fire_orders_approved = True
            results.append({
                "status": "launching",
                "message": f"Tick {tick}: 火控手收到开火命令，执行发射！",
                "link_id": link.get("link_id"),
            })

    return {
        "status": "done",
        "results": results,
        "message": f"拦截弹发射命令已执行 ({len(results)} 条)",
    }
""", type_name="MidRangeInterceptor")

    # 动作2：拦截结果评估
    create_action(oid, "拦截命中评估", """import math, random

def execute(context):
    participants = context.get("participants", [])
    active_links = context.get("active_links", [])
    tick = context.get("tick", 0)

    results = []
    threats_intercepted = []

    for link in active_links:
        props = link.get("properties", {})
        lt_name = link.get("link_type_name", "")
        if "FIRE_CHANNEL" in lt_name and props.get("status") in ("guiding",):
            p_kill = props.get("p_kill", 0.5)
            hit = random.random() < p_kill

            if hit:
                threats_intercepted.append({
                    "instance_id": link.get("target_instance_id"),
                    "interceptor_id": link.get("source_instance_id"),
                })
                results.append({
                    "status": "hit",
                    "message": f"Tick {tick}: 拦截命中！目标已摧毁",
                    "target_id": link.get("target_instance_id"),
                })
            else:
                results.append({
                    "status": "miss",
                    "message": f"Tick {tick}: 拦截未命中，需要补射",
                    "target_id": link.get("target_instance_id"),
                })

    return {
        "status": "done",
        "results": results,
        "threats_destroyed": [t["instance_id"] for t in threats_intercepted],
        "message": f"拦截评估完成: {len(results)} 次交战",
    }
""", type_name="MidRangeInterceptor")

    print(f"  → 共 {len(action_ids)} 个动作")

# ═══════════════════════════════════════════════════
# 8. 创建 Scenario（想定）
# ═══════════════════════════════════════════════════

scenario_ids = {}

# 模板实例的初始属性（用于构建 initial_state）
TEMPLATE_INIT_PROPS = {
    '东区联合指挥所': {'latitude': 31.23, 'longitude': 121.47, 'commander_name': '张将军', 'command_level': 1, 'decision_mode': 'manual', 'status': 'standby'},
    '预警雷达操作员-王': {'latitude': 31.25, 'longitude': 121.50, 'operator_name': '王少校', 'operator_status': 'ready', 'experience_level': 5, 'max_track_targets': 12},
    '红旗-9火控手-李': {'latitude': 31.20, 'longitude': 121.50, 'operator_name': '李上尉', 'operator_status': 'ready', 'fire_mode': 'manual'},
    '远程预警雷达-A': {'latitude': 31.25, 'longitude': 121.50, 'max_range_km': 480, 'tracking_capacity': 100, 'scan_interval_ms': 2000, 'detection_mode': 'auto', 'status': 'standby'},
    '红旗-9A发射车': {'latitude': 31.20, 'longitude': 121.50, 'max_range_km': 200, 'min_range_km': 5, 'kill_prob_single': 0.75, 'ammo_count': 16, 'max_altitude_km': 30, 'speed_mach': 6, 'fire_mode': 'manual', 'status': 'standby'},
    '红旗-9B发射车': {'latitude': 31.18, 'longitude': 121.52, 'max_range_km': 260, 'min_range_km': 7, 'kill_prob_single': 0.80, 'ammo_count': 12, 'max_altitude_km': 35, 'speed_mach': 6.5, 'fire_mode': 'manual', 'status': 'standby'},
    '陆基近防炮-A': {'latitude': 31.22, 'longitude': 121.48, 'max_range_km': 3, 'kill_prob_single': 0.65, 'ammo_count': 3000, 'fire_rate_rpm': 6000, 'fire_mode': 'auto', 'status': 'standby'},
    '市中心政务区': {'latitude': 31.23, 'longitude': 121.47, 'hardening_level': 3, 'value_score': 100, 'radius_m': 5000, 'protection_status': 'protected'},
    'SS-21 来袭弹道导弹-1': {'latitude': 32.50, 'longitude': 122.80, 'speed_mach': 8, 'rcs': 0.5, 'warhead_type': 'HE', 'apogee_km': 120, 'target_latitude': 31.23, 'target_longitude': 121.47, 'direction_deg': 225, 'status': 'flying'},
    'SS-21 来袭弹道导弹-2': {'latitude': 32.60, 'longitude': 122.90, 'speed_mach': 7.5, 'rcs': 0.6, 'warhead_type': 'HE', 'apogee_km': 110, 'target_latitude': 31.23, 'target_longitude': 121.47, 'direction_deg': 230, 'status': 'flying'},
    '鹰击-18 巡航导弹-1': {'latitude': 32.30, 'longitude': 123.00, 'speed_mach': 0.8, 'rcs': 0.15, 'flight_altitude_m': 50, 'direction_deg': 240, 'status': 'flying'},
    '鹰击-18 巡航导弹-2': {'latitude': 32.35, 'longitude': 123.10, 'speed_mach': 0.85, 'rcs': 0.12, 'flight_altitude_m': 45, 'direction_deg': 245, 'status': 'flying'},
    '诱饵弹-D1': {'latitude': 32.40, 'longitude': 122.50, 'speed_mach': 0.9, 'rcs': 3.0, 'is_decoy': True, 'direction_deg': 220, 'status': 'flying'},
    '诱饵弹-D2': {'latitude': 32.45, 'longitude': 122.70, 'speed_mach': 0.85, 'rcs': 2.5, 'is_decoy': True, 'direction_deg': 235, 'status': 'flying'},
}

def create_scenario(oid, name, description, participant_names, max_ticks=80, stop_condition="max_ticks"):
    participant_ids = [instance_ids[n] for n in participant_names if n in instance_ids]

    # 构建初始状态（使用硬编码的模板值，避免依赖API查询）
    initial_state = []
    for n in participant_names:
        iid = instance_ids.get(n)
        if not iid:
            continue
        props = TEMPLATE_INIT_PROPS.get(n, {})
        initial_state.append({
            "instance_id": iid,
            "initial_properties": dict(props),
        })

    design_params_map = {}
    for n, iid in instance_ids.items():
        design_params_map[iid] = {"name": n}

    payload = {
        "name": name,
        "description": description,
        "participant_instance_ids": participant_ids,
        "initial_state": initial_state,
        "design_params_map": design_params_map,
        "tick_interval_ms": 1000,
        "max_ticks": max_ticks,
        "stop_condition": stop_condition,
        "loop": False,
    }
    r = requests.post(f"{V2}/ontologies/{oid}/scenarios", headers=H, json=payload)
    r.raise_for_status()
    sid = r.json()["data"]["id"]
    scenario_ids[name] = sid
    print(f"  + Scenario: {name} ({sid[:8]}) 参与: {len(participant_ids)} 个实体")
    return sid

def create_scenarios(oid):
    # 想定1：单波次弹道导弹攻击（训练用）
    create_scenario(oid, "单波次弹道导弹攻击",
        "训练想定：2枚SS-21弹道导弹从东北方向来袭。"
        "雷达自动探测→操作员上报→火控手请求开火→指挥员审批→发射拦截→评估结果。"
        "手动决策全流程演练。",
        ["东区联合指挥所", "预警雷达操作员-王", "红旗-9火控手-李",
         "远程预警雷达-A", "红旗-9A发射车", "红旗-9B发射车", "陆基近防炮-A",
         "市中心政务区",
         "SS-21 来袭弹道导弹-1", "SS-21 来袭弹道导弹-2"],
        max_ticks=60, stop_condition="max_ticks")

    # 想定2：饱和攻击（综合测试）
    create_scenario(oid, "饱和攻击-混合威胁",
        "饱和攻击想定：2枚弹道导弹+2枚巡航导弹+2枚诱饵弹同时来袭。"
        "考验指挥所多目标处理能力、火控手优先级决策、"
        "以及手动模式下的快速反应能力。",
        ["东区联合指挥所", "预警雷达操作员-王", "红旗-9火控手-李",
         "远程预警雷达-A", "红旗-9A发射车", "红旗-9B发射车", "陆基近防炮-A",
         "市中心政务区",
         "SS-21 来袭弹道导弹-1", "SS-21 来袭弹道导弹-2",
         "鹰击-18 巡航导弹-1", "鹰击-18 巡航导弹-2",
         "诱饵弹-D1", "诱饵弹-D2"],
        max_ticks=80, stop_condition="max_ticks")

    # 想定3：高强度突防（近防炮末段）
    create_scenario(oid, "高强度突防-末段防御",
        "突防想定：多枚导弹已突破中段拦截进入末段，"
        "测试近防炮自动拦截和火控手紧急手动干预能力。",
        ["东区联合指挥所", "红旗-9火控手-李",
         "红旗-9A发射车", "陆基近防炮-A",
         "市中心政务区",
         "SS-21 来袭弹道导弹-1", "SS-21 来袭弹道导弹-2",
         "鹰击-18 巡航导弹-1", "鹰击-18 巡航导弹-2"],
        max_ticks=40, stop_condition="intercept_success")

    print(f"  → 共 {len(scenario_ids)} 个想定")

# ═══════════════════════════════════════════════════
# 9. 创建 Plan（人工决策方案模板）
# ═══════════════════════════════════════════════════

plan_ids = {}

def create_plan(scenario_id, name, description, decisions, source="manual"):
    payload = {
        "name": name,
        "description": description,
        "decisions": decisions,
        "source": source,
    }
    r = requests.post(f"{V2}/scenarios/{scenario_id}/plans", headers=H, json=payload)
    r.raise_for_status()
    pid = r.json()["data"]["id"]
    plan_ids[name] = pid
    print(f"  + Plan: {name} -> 决策: {len(decisions)} 条")
    return pid

def create_plans(oid):
    # 为每个想定创建方案
    for scenario_name, sid in scenario_ids.items():
        if "单波次" in scenario_name:
            plans_for_single_wave(sid)
        elif "饱和攻击" in scenario_name:
            plans_for_saturation(sid)
        elif "高强度" in scenario_name:
            plans_for_terminal(sid)

def plans_for_single_wave(sid):
    # 方案1：稳妥拦截（手动单发）
    create_plan(sid, "稳妥拦截方案（手动单发）",
        "火控手手动操作流程：探测->报告->请求->审批->单发拦截。"
        "每次只发射1发，命中则停，未中则补射。",
        [
            {"trigger": "detected", "target": "interceptor", "action": "launch", "params": {"count": 1, "mode": "single"}},
            {"trigger": "intercept_success", "target": "", "action": "stop", "params": {}},
            {"trigger": "intercept_failed", "target": "interceptor", "action": "launch", "params": {"count": 1, "mode": "single"}},
        ], source="manual")

    # 方案2：积极拦截（齐射）
    create_plan(sid, "积极拦截方案（双发齐射）",
        "火控手主动迎击：一旦锁定，立即请求双发齐射以确保杀伤概率。"
        "适合高价值目标防御。",
        [
            {"trigger": "distance<400", "target": "interceptor", "action": "launch", "params": {"count": 2, "mode": "salvo"}},
            {"trigger": "intercept_success", "target": "", "action": "stop", "params": {}},
        ], source="manual")

def plans_for_saturation(sid):
    create_plan(sid, "分层拦截方案",
        "远程中段拦截+末段近防炮补射。优先拦截弹道导弹，"
        "巡航导弹留给近防炮处理。",
        [
            {"trigger": "distance<450", "target": "interceptor", "action": "launch", "params": {"count": 2, "mode": "salvo"}},
            {"trigger": "distance<100", "target": "ciws", "action": "launch", "params": {"count": 1, "mode": "auto"}},
            {"trigger": "intercept_success", "target": "", "action": "stop", "params": {}},
        ], source="manual")

    create_plan(sid, "优先反导方案",
        "优先拦截弹道导弹（速度快、威胁大），巡航导弹和诱饵"
        "交由末段近防炮处理。",
        [
            {"trigger": "detected", "target": "bm", "action": "launch", "params": {"count": 2, "mode": "priority"}},
            {"trigger": "distance<3", "target": "ciws", "action": "launch", "params": {"count": 1, "mode": "auto"}},
            {"trigger": "intercept_failed", "target": "interceptor", "action": "launch", "params": {"count": 1, "mode": "single"}},
        ], source="manual")

def plans_for_terminal(sid):
    create_plan(sid, "末段紧急拦截方案",
        "近防炮自动火力+火控手手动补射。在末段用最大火力密度拦截。",
        [
            {"trigger": "distance<10", "target": "ciws", "action": "launch", "params": {"count": 1, "mode": "auto"}},
            {"trigger": "intercept_failed", "target": "interceptor", "action": "launch", "params": {"count": 2, "mode": "salvo"}},
        ], source="manual")

# ═══════════════════════════════════════════════════
# 10. 验证与总结
# ═══════════════════════════════════════════════════

def print_summary(oid):
    print(f"\n{'='*60}")
    print(f"✅ 手动防空反导本体创建完成！")
    print(f"{'='*60}")
    print(f"  Ontology ID:    {oid}")
    print(f"  ObjectType:     {len(type_ids)} 个")
    print(f"  ObjectInstance: {len(instance_ids)} 个")
    print(f"  LinkType:       {len(link_type_ids)} 个")
    print(f"  Rule:           {len(rule_ids)} 条")
    print(f"  Action:         {len(action_ids)} 个")
    print(f"  Scenario:       {len(scenario_ids)} 个")
    print(f"  Plan:           {len(plan_ids)} 套")
    print(f"\n📋 前端访问: http://localhost:5173/ontologies/{oid}")
    print(f"📋 API访问:   http://localhost:18020/api/v1/ontologies/{oid}")

    # 列出想定
    print(f"\n📋 想定列表:")
    for name, sid in scenario_ids.items():
        print(f"   - [{sid[:8]}] {name}")

    # 列出方案
    print(f"\n📋 方案列表:")
    for name, pid in plan_ids.items():
        print(f"   - [{pid[:8]}] {name}")

    print(f"\n📖 手动防空反导流程:")
    print(f"   ① 雷达自动扫描 → ② 操作员确认目标")
    print(f"   ③ 火控手评估 → ④ 向指挥所请求开火")
    print(f"   ⑤ 指挥员审批 → ⑥ 下达开火命令")
    print(f"   ⑦ 火控手执行发射 → ⑧ 拦截结果评估")
    print(f"\n💡 可通过 POST /api/v2/ontologies/{{id}}/confirm-links 手动确认操作")
    print(f"💡 可通过 POST /api/v2/ontologies/{{id}}/scenarios/{{sid}}/start 开始推演")
    print(f"💡 可通过 POST /api/v2/ontologies/{{id}}/scenarios/{{sid}}/tick 推进到下一帧")
    print(f"💡 可通过 POST /api/v2/scenarios/{{sid}}/plans/{{pid}}/run 执行方案")
    print(f"{'='*60}\n")

# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════

def main():
    print("🚀 手动防空反导本体种子脚本\n")
    login()
    oid = create_ontology()
    create_types(oid)
    create_instances(oid)
    create_link_types(oid)
    create_rules(oid)
    create_actions(oid)
    create_scenarios(oid)
    create_plans(oid)
    print_summary(oid)

if __name__ == "__main__":
    main()
