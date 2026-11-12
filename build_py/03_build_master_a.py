#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
[파이프라인 3단계] 전략 A 차종-연식-시스템 마스터셋 생성 스크립트 (공장 정보 포함)
파일명: 03_build_master_a.py
위치: dataset/build_py/
출력:
  - dataset/rds/master_vehicle_system_2020.rds (R 클러스터링 분석용)
  - dataset/raw/master_vehicle_system_2020.csv (엑셀 및 공용 플랫 테이블)
==============================================================================
"""

import os
import csv
import json
import subprocess
from collections import defaultdict, Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(DATASET_DIR)

CMPL_TXT = os.path.join(PROJECT_ROOT, "소비자 불만_사고_화재 정보", "FLAT_CMPL.txt")
RCL_TXT = os.path.join(PROJECT_ROOT, "리콜 일자_결함 유형_대상 차량", "FLAT_RCL_POST_2010.txt")
INV_TXT = os.path.join(PROJECT_ROOT, "정부 결함 조사 이력", "FLAT_INV.txt")
CACHE_KEYS = os.path.join(DATASET_DIR, "cache", "korean_vehicle_keys_2020.json")

RDS_DIR = os.path.join(DATASET_DIR, "rds")
RAW_DIR = os.path.join(DATASET_DIR, "raw")
os.makedirs(RDS_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

CSV_OUT = os.path.join(RAW_DIR, "master_vehicle_system_2020.csv")
RDS_OUT = os.path.join(RDS_DIR, "master_vehicle_system_2020.rds")

# VIN 11번째 자리 기준 한국 조립공장 매핑 (ISO 3779 표준 규격)
PLANT_MAP = {
    # (Make, PlantCode): (PlantCity, PlantName)
    ("HYUNDAI", "U"): ("ULSAN", "Hyundai Ulsan Plant"),
    ("HYUNDAI", "A"): ("ASAN", "Hyundai Asan Plant"),
    ("HYUNDAI", "M"): ("JEONJU", "Hyundai Jeonju Plant"),
    ("GENESIS", "U"): ("ULSAN", "Hyundai Ulsan Genesis Plant"),
    ("KIA", "7"): ("GWANGJU", "Kia AutoLand Gwangju"),
    ("KIA", "5"): ("HWASEONG", "Kia AutoLand Hwaseong"),
    ("KIA", "6"): ("GWANGMYEONG", "Kia AutoLand Gwangmyeong"),
    ("CHEVROLET", "B"): ("BUPYEONG", "GM Korea Bupyeong Plant"),
    ("CHEVROLET", "C"): ("CHANGWON", "GM Korea Changwon Plant"),
    ("BUICK", "B"): ("BUPYEONG", "GM Korea Bupyeong Plant"),
    ("BUICK", "C"): ("CHANGWON", "GM Korea Changwon Plant"),
}

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
    print(">> [3단계] 전략 A 마스터셋 생성 시작 (공장 정보 plant_city/name 추가)...")
    print("=" * 70)

    # 1. 한국산 키 로드
    with open(CACHE_KEYS, "r", encoding="utf-8") as f:
        keys_data = json.load(f)
    kor_keys = {(d["make"].upper(), d["model"].upper(), int(d["year"])) for d in keys_data}

    # 2. 불만 데이터 집계 + 공장 코드(VIN 11번째 자리) 추출
    print(">> 1/4. 소비자 불만 원천 데이터 집계 및 생산 공장 해독 중...")
    cmpl_stats = defaultdict(lambda: {
        "cmpl_count": 0, "fire_count": 0, "crash_count": 0,
        "inj_count": 0, "death_count": 0, "stall_count": 0,
        "smoke_fire_text_count": 0, "early_fail_count": 0,
        "miles_list": [], "plant_codes": Counter()
    })

    # 차종별 기본 공장 백업 매핑
    model_plant_lookup = defaultdict(Counter)

    with open(CMPL_TXT, "r", encoding="latin-1") as f:
        for line in f:
            tokens = line.split("\t")
            if len(tokens) >= 15:
                yr_str = tokens[5].strip()
                if not (yr_str.isdigit() and int(yr_str) >= 2020):
                    continue
                vin = tokens[14].strip().upper()
                if not (vin.startswith("K") or vin.startswith(("KMH", "KM8", "KNA", "KND", "KL1", "KL4"))):
                    continue
                
                make = tokens[3].strip().upper()
                model = tokens[4].strip().upper()
                year = int(yr_str)
                system = standardize_system(tokens[11])
                
                # VIN 11번째 자리 공장 코드
                p_char = vin[10] if len(vin) >= 11 else ""
                if p_char:
                    model_plant_lookup[(make, model)][p_char] += 1
                
                g_key = (make, model, year, system)
                st = cmpl_stats[g_key]
                st["cmpl_count"] += 1
                if p_char:
                    st["plant_codes"][p_char] += 1
                
                if tokens[8].strip().upper() == "Y":
                    st["fire_count"] += 1
                if tokens[6].strip().upper() == "Y":
                    st["crash_count"] += 1
                    
                try:
                    st["inj_count"] += int(float(tokens[9].strip() or 0))
                except ValueError:
                    pass
                try:
                    st["death_count"] += int(float(tokens[10].strip() or 0))
                except ValueError:
                    pass
                    
                cdescr = tokens[19].upper() if len(tokens) > 19 else ""
                if any(k in cdescr for k in ["STALL", "SHUT OFF", "DIED", "CUT OFF", "NO POWER", "LOSS OF POWER"]):
                    st["stall_count"] += 1
                if any(k in cdescr for k in ["SMOKE", "FIRE", "BURNING", "MELT", "FLAME", "SPARK"]):
                    st["smoke_fire_text_count"] += 1
                    
                try:
                    m = float(tokens[17].strip() or -1)
                    if 0 <= m <= 300000:
                        st["miles_list"].append(m)
                        if m <= 15000:
                            st["early_fail_count"] += 1
                except ValueError:
                    pass

    print(f"   • 불만 집계 완료: {len(cmpl_stats)}개 그룹")

    # 3. 리콜 데이터 집계
    print(">> 2/4. 리콜 원천 데이터 집계 중...")
    rcl_stats = defaultdict(lambda: {
        "camps": set(), "potaff_max": 0.0, "parts": set(),
        "park_outside": 0, "do_not_drive": 0,
        "part_names": set(), "part_numbers": set()
    })

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
                    
                system = standardize_system(tokens[6])
                g_key = (make, model, year, system)
                rst = rcl_stats[g_key]
                
                campno = tokens[1].strip()
                if campno:
                    rst["camps"].add(campno)
                    
                try:
                    pot = float(tokens[11].strip() or 0)
                    if pot > rst["potaff_max"]:
                        rst["potaff_max"] = pot
                except ValueError:
                    pass
                    
                if len(tokens) >= 29 and tokens[28].strip().upper() == "Y":
                    rst["park_outside"] = 1
                if len(tokens) >= 28 and tokens[27].strip().upper() == "Y":
                    rst["do_not_drive"] = 1
                    
                if len(tokens) >= 25 and tokens[24].strip():
                    rst["part_names"].add(tokens[24].strip())
                if len(tokens) >= 27 and tokens[26].strip():
                    rst["part_numbers"].add(tokens[26].strip())
                    rst["parts"].add(tokens[26].strip())

    print(f"   • 리콜 집계 완료: {len(rcl_stats)}개 그룹")

    # 4. 정부 조사 데이터 집계
    print(">> 3/4. 정부 결함 조사 원천 데이터 집계 중...")
    inv_stats = defaultdict(lambda: {"inv_count": 0, "active": 1})

    with open(INV_TXT, "r", encoding="latin-1") as f:
        for line in f:
            tokens = line.split("\t")
            if len(tokens) >= 5:
                yr_str = tokens[3].strip()
                if not (yr_str.isdigit() and int(yr_str) >= 2020):
                    continue
                make = tokens[1].strip().upper()
                model = tokens[2].strip().upper()
                year = int(yr_str)
                
                if not ((make, model, year) in kor_keys or any(k in make for k in ["HYUNDAI", "KIA", "GENESIS"])):
                    continue
                    
                system = standardize_system(tokens[4])
                inv_stats[(make, model, year, system)]["inv_count"] += 1

    print(f"   • 조사 집계 완료: {len(inv_stats)}개 그룹")

    # 5. Full Outer Join 및 공장명 매핑
    print(">> 4/4. 마스터셋 병합 및 공장 컬럼(plant_country, plant_city, plant_name) 생성 중...")
    all_keys = set(cmpl_stats.keys()) | set(rcl_stats.keys()) | set(inv_stats.keys())

    master_rows = []
    for g_key in all_keys:
        make, model, year, system = g_key
        c = cmpl_stats[g_key]
        r = rcl_stats[g_key]
        inv = inv_stats[g_key]
        
        # 공장 코드 판별 (해당 그룹 빈도 최상위 or 차종 기본값)
        p_code = ""
        if c["plant_codes"]:
            p_code = c["plant_codes"].most_common(1)[0][0]
        elif (make, model) in model_plant_lookup and model_plant_lookup[(make, model)]:
            p_code = model_plant_lookup[(make, model)].most_common(1)[0][0]
            
        p_city, p_name = PLANT_MAP.get((make, p_code), ("KOREA_OTHER", "Korean Assembly Plant"))
        if make in ["HYUNDAI", "GENESIS"] and p_city == "KOREA_OTHER":
            p_city, p_name = ("ULSAN", "Hyundai Ulsan Plant")
        elif make == "KIA" and p_city == "KOREA_OTHER":
            p_city, p_name = ("GWANGJU", "Kia AutoLand Gwangju")
        elif make in ["CHEVROLET", "BUICK"] and p_city == "KOREA_OTHER":
            p_city, p_name = ("BUPYEONG", "GM Korea Bupyeong Plant")
            
        cmpl_cnt = c["cmpl_count"]
        fire_cnt = c["fire_count"]
        crash_cnt = c["crash_count"]
        inj_cnt = c["inj_count"]
        death_cnt = c["death_count"]
        stall_cnt = c["stall_count"]
        smoke_cnt = c["smoke_fire_text_count"]
        early_cnt = c["early_fail_count"]
        avg_miles = round(sum(c["miles_list"]) / len(c["miles_list"]), 1) if c["miles_list"] else ""
        
        rcl_cnt = len(r["camps"])
        part_cnt = len(r["parts"])
        potaff = r["potaff_max"]
        park_out = r["park_outside"]
        dnd = r["do_not_drive"]
        top_names = " | ".join(sorted(r["part_names"])[:2])
        top_nums = " | ".join(sorted(r["part_numbers"])[:2])
        
        inv_cnt = inv["inv_count"]
        active_inv = 1 if inv_cnt > 0 else 0
        
        risk_index = (fire_cnt * 3) + (crash_cnt * 2) + (inj_cnt * 2) + (death_cnt * 10) + \
                     (park_out * 5) + (dnd * 10) + (active_inv * 4)
                     
        early_ratio = round(early_cnt / cmpl_cnt, 3) if cmpl_cnt > 0 else 0.0
        has_recall = 1 if rcl_cnt > 0 else 0
        
        master_rows.append({
            "make": make, "model": model, "year": year, "system": system,
            "plant_country": "SOUTH KOREA",
            "plant_city": p_city,
            "plant_name": p_name,
            "cmpl_count": cmpl_cnt, "fire_count": fire_cnt, "crash_count": crash_cnt,
            "inj_count": inj_cnt, "death_count": death_cnt, "stall_count": stall_cnt,
            "smoke_fire_text_count": smoke_cnt, "early_fail_count": early_cnt,
            "avg_fail_miles": avg_miles, "recall_count": rcl_cnt,
            "distinct_parts_count": part_cnt, "max_potaff": potaff,
            "park_outside_yn": park_out, "do_not_drive_yn": dnd,
            "key_part_names": top_names, "key_part_numbers": top_nums,
            "inv_count": inv_cnt, "active_inv_yn": active_inv,
            "risk_severity_index": risk_index, "early_fail_ratio": early_ratio,
            "has_recall": has_recall
        })

    master_rows.sort(key=lambda x: (-x["risk_severity_index"], -x["cmpl_count"]))

    fieldnames = list(master_rows[0].keys())
    with open(CSV_OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master_rows)
    print(f"   ★ CSV 저장 완료: '{CSV_OUT}' ({len(master_rows):,}행, {len(fieldnames)}열)")

    r_code = f"""
    df <- read.csv("{CSV_OUT}", stringsAsFactors = FALSE, check.names = FALSE)
    saveRDS(df, "{RDS_OUT}")
    """
    subprocess.run(["Rscript", "-e", r_code], check=True)
    print(f"   ★ RDS 저장 완료: '{RDS_OUT}'")

    print("=" * 70)
    print(">> [3단계 완료] 공장 컬럼(plant_country, plant_city, plant_name) 탑재 완료!")
    print("=" * 70)

if __name__ == "__main__":
    main()
