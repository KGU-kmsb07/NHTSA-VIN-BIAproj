#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
NHTSA 한국 생산 수출차량 단일 마스터 데이터셋 구축 통합 파이프라인
파일명: run_pipeline.py
위치: dataset/build_py/
실행: python3 run_pipeline.py
역할:
  - 1단계: 원본 ZIP 파일 자동 압축 해제 (01_unzip_raw.py)
  - 2단계: NHTSA vPIC VIN 해독 및 한국산 차량 선별 (02_vpic_vin_match.py)
  - 3단계: 전략 A 차종-연식-시스템 마스터셋 생성 (03_build_master_a.py)
  - 4단계: 전략 B 리콜 부품-협력사 SCM 마스터셋 생성 (04_build_master_b.py)
==============================================================================
"""

import os
import sys
import subprocess
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.dirname(SCRIPT_DIR)

PIPELINE_STEPS = [
    ("01_unzip_raw.py", "1단계: 원본 ZIP 파일 자동 압축 해제"),
    ("02_vpic_vin_match.py", "2단계: NHTSA vPIC VIN 해독 및 한국산 차량 선별"),
    ("03_build_master_a.py", "3단계: 전략 A 차종-연식-시스템 마스터셋 생성 (RDS/CSV)"),
    ("04_build_master_b.py", "4단계: 전략 B 리콜 부품-협력사 마스터셋 생성 (RDS/CSV)")
]

def main():
    start_total = time.time()
    print("======================================================================")
    print(">> [통합 파이프라인] NHTSA 한국 생산 차량 데이터셋 구축을 시작합니다.")
    print(f">> 기준 디렉토리: {DATASET_DIR}")
    print("======================================================================\n")

    for idx, (py_name, desc) in enumerate(PIPELINE_STEPS, 1):
        step_path = os.path.join(SCRIPT_DIR, py_name)
        print(f"\n>>> [{idx}/{len(PIPELINE_STEPS)}] {desc} 실행 중...")
        step_start = time.time()
        
        res = subprocess.run([sys.executable, step_path], check=True)
        
        step_elapsed = time.time() - step_start
        print(f">>> [{idx}/{len(PIPELINE_STEPS)}] 완료 (소요 시간: {step_elapsed:.1f}초)\n")

    total_elapsed = time.time() - start_total
    print("======================================================================")
    print(">> ★ 모든 파이프라인이 성공적으로 완료되었습니다!")
    print(f">> 총 소요 시간: {total_elapsed:.1f}초")
    print(f">> 생성 결과물 위치: {DATASET_DIR}")
    print("   • dataset/rds/master_vehicle_system_2020.rds (클러스터링용)")
    print("   • dataset/rds/master_parts_recalls_2020.rds  (부품/협력사 분석용)")
    print("   • dataset/raw/master_vehicle_system_2020.csv (플랫 CSV)")
    print("   • dataset/raw/master_parts_recalls_2020.csv  (플랫 CSV)")
    print("======================================================================")

if __name__ == "__main__":
    main()
