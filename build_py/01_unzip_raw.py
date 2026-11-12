#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
[파이프라인 1단계] NHTSA 원천 ZIP 데이터 자동 압축 해제 스크립트
파일명: 01_unzip_raw.py
위치: dataset/build_py/
역할:
  - '소비자 불만_사고_화재 정보/FLAT_CMPL.zip'
  - '리콜 일자_결함 유형_대상 차량/FLAT_RCL_POST_2010.zip'
  - '정부 결함 조사 이력/FLAT_INV.zip'
  위 3개 원본 압축본을 각 폴더 내에 안전하게 압축 해제합니다.
==============================================================================
"""

import os
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

TASKS = [
    (
        os.path.join(PROJECT_ROOT, "소비자 불만_사고_화재 정보", "FLAT_CMPL.zip"),
        os.path.join(PROJECT_ROOT, "소비자 불만_사고_화재 정보"),
        "FLAT_CMPL.txt"
    ),
    (
        os.path.join(PROJECT_ROOT, "리콜 일자_결함 유형_대상 차량", "FLAT_RCL_POST_2010.zip"),
        os.path.join(PROJECT_ROOT, "리콜 일자_결함 유형_대상 차량"),
        "FLAT_RCL_POST_2010.txt"
    ),
    (
        os.path.join(PROJECT_ROOT, "정부 결함 조사 이력", "FLAT_INV.zip"),
        os.path.join(PROJECT_ROOT, "정부 결함 조사 이력"),
        "FLAT_INV.txt"
    )
]

def main():
    print("=" * 70)
    print(">> [1단계] NHTSA 원천 데이터 압축 해제 시작...")
    print("=" * 70)
    
    for zip_path, extract_dir, check_file in TASKS:
        target_file = os.path.join(extract_dir, check_file)
        if os.path.exists(target_file):
            size_mb = os.path.getsize(target_file) / (1024 * 1024)
            print(f"   • 이미 압축 해제됨: '{check_file}' ({size_mb:.1f} MB) -> 건너뜁니다.")
            continue
            
        if not os.path.exists(zip_path):
            print(f"   [오류] 압축 파일이 없습니다: '{zip_path}'")
            continue
            
        print(f"   • 압축 푸는 중: '{os.path.basename(zip_path)}' -> '{extract_dir}' ...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
            
        size_mb = os.path.getsize(target_file) / (1024 * 1024)
        print(f"   ★ 압축 해제 완료: '{check_file}' ({size_mb:.1f} MB)")

    print("=" * 70)
    print(">> [1단계 완료] 모든 원본 텍스트 파일이 준비되었습니다.")
    print("=" * 70)

if __name__ == "__main__":
    main()
