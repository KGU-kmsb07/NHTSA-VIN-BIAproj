#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
[파이프라인 4단계] 전략 B 리콜 부품-협력사(SCM) 마스터셋 생성 스크립트 (Fast Engine)
파일명: 04_build_master_b.py
위치: dataset/build_py/
출력:
  - dataset/rds/master_parts_recalls_2020.rds (R 협력사 SCM/부품교체 분석용)
  - dataset/raw/master_parts_recalls_2020.csv (엑셀 및 공용 플랫 테이블)
==============================================================================
"""

import os
import csv
import json
import subprocess
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(DATASET_DIR)

RCL_TXT = os.path.join(PROJECT_ROOT, "리콜 일자_결함 유형_대상 차량", "FLAT_RCL_POST_2010.txt")
CACHE_KEYS = os.path.join(DATASET_DIR, "cache", "korean_vehicle_keys_2020.json")

RDS_DIR = os.path.join(DATASET_DIR, "rds")
RAW_DIR = os.path.join(DATASET_DIR, "raw")
CSV_OUT = os.path.join(RAW_DIR, "master_parts_recalls_2020.csv")
RDS_OUT = os.path.join(RDS_DIR, "master_parts_recalls_2020.rds")
VEH_CSV = os.path.join(RAW_DIR, "master_vehicle_system_2020.csv")

def standardize_system(comp_desc):
    c = (comp_desc or "").strip().upper()
    if not c:
        return "UNKNOWN"
    if any(k in c for k in ["ELECTRICAL", "BATTERY", "WIRING", "HYBRID", "FUSE", "LIGHT"]):
        return "ELECTRICAL"
    if any(k in c for k in ["ENGINE", "COOLING", "EXHAUST", "OIL"]):
        return "ENGINE"
    if any(k in c for k in ["POWER TRAIN", "TRANSMISSION", "DRIVE SHAFT", "AXLE"]):
        return "POWERTRAIN"
    if any(k in c for k in ["FUEL", "GASOLINE", "PROPULSION", "PUMP", "INJECTOR"]):
        return "FUEL_SYSTEM"
    if any(k in c for k in ["BRAKE", "HYDRAULIC", "ABS", "ESC"]):
        return "BRAKES"
    if any(k in c for k in ["SEAT BELT", "SEATBELT", "BUCKLE", "RETRACTOR"]):
        return "SEAT_BELTS"
    if any(k in c for k in ["AIR BAG", "AIRBAG", "INFLATOR"]):
        return "AIR_BAGS"
    if any(k in c for k in ["STEERING", "COLUMN", "TIE ROD", "GEAR"]):
        return "STEERING"
    if any(k in c for k in ["FORWARD COLLISION", "LANE", "CAMERA", "RADAR", "ADAS", "CRUISE", "BACK OVER"]):
        return "ADAS_SAFETY"
    if any(k in c for k in ["SUSPENSION", "SPRING", "SHOCK"]):
        return "SUSPENSION"
    if any(k in c for k in ["STRUCTURE", "BODY", "DOOR", "LATCH", "LOCK", "ROOF"]):
        return "BODY_STRUCTURE"
    if any(k in c for k in ["VISIBILITY", "WIPER", "WINDSHIELD", "WINDOW", "MIRROR"]):
        return "VISIBILITY"
    if any(k in c for k in ["TIRE", "WHEEL", "RIM"]):
        return "TIRES_WHEELS"
    return "OTHER"

def main():
    print("=" * 70)
    print(">> [4단계] 전략 B 리콜 부품-협력사 마스터셋 생성 시작 (Fast Engine)...")
    print("=" * 70)

    # 1. 한국산 키 로드
    with open(CACHE_KEYS, "r", encoding="utf-8") as f:
        keys_data = json.load(f)
    kor_keys = {(d["make"].upper(), d["model"].upper(), int(d["year"])) for d in keys_data}

    # 2. 리콜 부품 데이터 추출
    print(">> 1/3. 2020년 이후 리콜 데이터에서 부품번호(Part No.) 유효 데이터 추출 중...")
    parts_map = defaultdict(lambda: {
        "models": set(), "years": [], "potaff": 0.0,
        "park_outside": 0, "do_not_drive": 0,
        "is_replacement": 0, "is_sw_update": 0,
        "desc_defect": "", "corrective_action": "",
        "make": "", "mfr_comp_name": ""
    })

    total_rec_2020 = 0
    with open(RCL_TXT, "r", encoding="latin-1") as f:
        for line in f:
            tokens = line.split("\t")
            if len(tokens) >= 12:
                yr_str = tokens[4].strip()
                if not (yr_str.isdigit() and int(yr_str) >= 2020):
                    continue
                make = tokens[2].strip().upper()
                model = tokens[3].strip().upper()
                year = int(yr_str)
                
                if not ((make, model, year) in kor_keys or any(k in make for k in ["HYUNDAI", "KIA", "GENESIS", "GM KOREA"])):
                    continue
                    
                total_rec_2020 += 1
                campno = tokens[1].strip()
                pt_no = tokens[26].strip() if len(tokens) >= 27 else ""
                if not pt_no:
                    continue
                    
                system = standardize_system(tokens[6])
                p_key = (campno, pt_no, system)
                item = parts_map[p_key]
                
                item["make"] = make
                item["models"].add(f"{make} {model}")
                item["years"].append(year)
                
                if len(tokens) >= 25 and tokens[24].strip() and not item["mfr_comp_name"]:
                    item["mfr_comp_name"] = tokens[24].strip()
                    
                try:
                    pot = float(tokens[11].strip() or 0)
                    if pot > item["potaff"]:
                        item["potaff"] = pot
                except ValueError:
                    pass
                    
                if len(tokens) >= 29 and tokens[28].strip().upper() == "Y":
                    item["park_outside"] = 1
                if len(tokens) >= 28 and tokens[27].strip().upper() == "Y":
                    item["do_not_drive"] = 1
                    
                action = tokens[21].strip() if len(tokens) >= 22 else ""
                action_u = action.upper()
                if any(k in action_u for k in ["REPLACE", "REPLACEMENT", "INSTALL NEW"]):
                    item["is_replacement"] = 1
                if any(k in action_u for k in ["UPDATE", "SOFTWARE", "REPROGRAM", "REFLASH"]):
                    item["is_sw_update"] = 1
                    
                if not item["corrective_action"]:
                    item["corrective_action"] = action
                if not item["desc_defect"] and len(tokens) >= 20:
                    item["desc_defect"] = tokens[19].strip()

    print(f"   • 2020+ 한국 생산 리콜 {total_rec_2020}건 중 고유 (캠페인-부품번호) {len(parts_map)}건 식별")

    # 3. 소비자 불만 규모 연계 (전략 A 결과 참조)
    print(">> 2/3. 소비자 불만/화재 규모 매핑 중...")
    sys_cmpl_totals = defaultdict(int)
    sys_fire_totals = defaultdict(int)

    if os.path.exists(VEH_CSV):
        with open(VEH_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mk_sys = (row["make"].upper(), row["system"].upper())
                sys_cmpl_totals[mk_sys] += int(float(row.get("cmpl_count", 0)))
                sys_fire_totals[mk_sys] += int(float(row.get("fire_count", 0)))

    parts_rows = []
    for p_key, val in parts_map.items():
        campno, pt_no, system = p_key
        make = val["make"]
        
        linked_cmpl = sys_cmpl_totals.get((make, system), 0)
        linked_fire = sys_fire_totals.get((make, system), 0)
        
        parts_rows.append({
            "campno": campno,
            "mfr_comp_ptno": pt_no,
            "system": system,
            "make": make,
            "mfr_comp_name": val["mfr_comp_name"],
            "affected_models": ", ".join(sorted(val["models"])),
            "model_year_min": min(val["years"]) if val["years"] else "",
            "model_year_max": max(val["years"]) if val["years"] else "",
            "potaff": val["potaff"],
            "park_outside_yn": val["park_outside"],
            "do_not_drive_yn": val["do_not_drive"],
            "is_part_replacement": val["is_replacement"],
            "is_sw_update_only": val["is_sw_update"],
            "desc_defect": val["desc_defect"],
            "corrective_action": val["corrective_action"],
            "linked_system_cmpl_count": linked_cmpl,
            "linked_system_fire_count": linked_fire
        })

    parts_rows.sort(key=lambda x: -x["potaff"])

    # 4. 저장
    print(">> 3/3. CSV 및 RDS 파일 저장 중...")
    fieldnames = list(parts_rows[0].keys())
    with open(CSV_OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(parts_rows)
    print(f"   ★ CSV 저장 완료: '{CSV_OUT}' ({len(parts_rows):,}행, {len(fieldnames)}열)")

    r_code = f"""
    df <- read.csv("{CSV_OUT}", stringsAsFactors = FALSE, check.names = FALSE)
    saveRDS(df, "{RDS_OUT}")
    """
    subprocess.run(["Rscript", "-e", r_code], check=True)
    print(f"   ★ RDS 저장 완료: '{RDS_OUT}'")

    print("=" * 70)
    print(">> [4단계 완료] master_parts_recalls_2020가 완벽하게 생성되었습니다.")
    print("=" * 70)

if __name__ == "__main__":
    main()
