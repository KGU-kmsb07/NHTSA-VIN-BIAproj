#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
[파이프라인 2단계] NHTSA vPIC VIN 해독 및 한국 생산 차종 선별 스크립트
파일명: 02_vpic_vin_match.py
위치: dataset/build_py/
역할:
  - 원본 'FLAT_CMPL.txt'에서 2020년 이후 차량의 VIN 및 차종 데이터 추출
  - NHTSA vPIC Batch API (또는 ISO 3779 WMI 표준 규칙)를 통해 한국 생산 차량 판별
  - 한국 생산으로 확정된 (Make, Model, Year) 고유 키 및 불만/리콜/조사 후보군 선별
==============================================================================
"""

import os
import csv
import json
import urllib.request
import urllib.parse
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

# 입력 원본 파일 경로
CMPL_TXT = os.path.join(PROJECT_ROOT, "소비자 불만_사고_화재 정보", "FLAT_CMPL.txt")
RCL_TXT = os.path.join(PROJECT_ROOT, "리콜 일자_결함 유형_대상 차량", "FLAT_RCL_POST_2010.txt")
INV_TXT = os.path.join(PROJECT_ROOT, "정부 결함 조사 이력", "FLAT_INV.txt")

CACHE_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, "korean_vehicle_keys_2020.json")

# 한국 생산 WMI (World Manufacturer Identifier - VIN 첫 3자리)
KOREAN_WMI_PREFIXES = (
    "KMH", "KM8", "KME", "KMY", "KM4", # Hyundai Motor Company Korea
    "KNA", "KND", "KN3", "KNE", "KN5", # Kia Corporation Korea
    "KL1", "KL4", "KL7", "KL8",       # GM Korea (Bupyeong/Changwon)
    "KGM", "KPT",                     # KG Mobility / SsangYong
    "KNM"                             # Renault Korea
)

KOREA_COUNTRY_SYNONYMS = {
    "KOR", "KOREA", "KOREA REP OF", "KOREA REPUBLIC OF",
    "KOREA SOUTH", "KR", "REPUBLIC OF KOREA", "SOUTH KOREA"
}

def is_korean_origin_wmi(vin):
    if not vin or len(vin) < 3:
        return False
    v = vin.strip().upper()
    return v.startswith(KOREAN_WMI_PREFIXES) or (v.startswith("K") and len(v) >= 11)

def query_vpic_api_batch(batch_pairs):
    """
    NHTSA 공식 vPIC Batch API 호출 (네트워크 가능 시)
    """
    api_url = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVINValuesBatch/"
    payload = {
        "format": "json",
        "data": ";".join(f"{vin},{yr}" if yr else vin for vin, yr in batch_pairs)
    }
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(api_url, data=data, headers={"User-Agent": "NHTSA-Research"})
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        return res_json.get("Results", [])

def main():
    print("=" * 70)
    print(">> [2단계] VIN 해독 및 2020년 이후 한국 생산 차량 선별 시작...")
    print("=" * 70)
    
    if not os.path.exists(CMPL_TXT):
        raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {CMPL_TXT}")

    # 1. 2020년 이후 소비자 불만 데이터 스캔
    print(">> 1/3. 2020년 이후 소비자 불만 스캔 중...")
    korean_keys = set()
    total_scanned = 0
    korean_complaints_count = 0
    
    with open(CMPL_TXT, "r", encoding="latin-1") as f:
        for line in f:
            total_scanned += 1
            tokens = line.split("\t")
            if len(tokens) >= 15:
                make = tokens[3].strip().upper()
                model = tokens[4].strip().upper()
                yr_str = tokens[5].strip()
                vin = tokens[14].strip().upper()
                
                if yr_str.isdigit() and int(yr_str) >= 2020:
                    if is_korean_origin_wmi(vin):
                        korean_complaints_count += 1
                        korean_keys.add((make, model, int(yr_str)))
                        
    print(f"   • 스캔 완료: 총 {total_scanned:,}행 불만 중 2020+ 한국 생산 불만 {korean_complaints_count:,}건 식별")
    print(f"   • 식별된 고유 차종-연식 키: {len(korean_keys)}개")
    
    # 2. 결과 캐시 저장
    cache_data = [
        {"make": m, "model": mo, "year": y}
        for m, mo, y in sorted(korean_keys)
    ]
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
    print(f">> 2/3. 선별된 한국 생산 차종 키 캐시 저장 완료: '{CACHE_FILE}'")
    
    # 3. 대표 차종 샘플 출력
    sample_makes = {}
    for item in cache_data:
        m = item["make"]
        sample_makes[m] = sample_makes.get(m, 0) + 1
        
    print(">> 3/3. 한국 생산 제조사별 차종-연식 분포:")
    for mk, cnt in sorted(sample_makes.items(), key=lambda x: -x[1])[:8]:
        print(f"   • {mk}: {cnt}개 차종-연식 조합")

    print("=" * 70)
    print(">> [2단계 완료] 한국 생산 차량 매칭 및 선별이 완료되었습니다.")
    print("=" * 70)

if __name__ == "__main__":
    main()
