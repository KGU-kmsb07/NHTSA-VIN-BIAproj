#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import re
import os

def test_integrity():
    # 1. Master A
    with open("dataset/raw/master_vehicle_system_2020.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        hdr_a = next(reader)
        row_cnt_a = sum(1 for _ in reader)

    # 2. Master B
    with open("dataset/raw/master_parts_recalls_2020.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        hdr_b = next(reader)
        row_cnt_b = sum(1 for _ in reader)

    # 3. README
    with open("dataset/README.md", "r", encoding="utf-8") as f:
        readme = f.read()

    # Section 5.1
    s51 = readme[readme.find("### 5.1."):readme.find("### 5.2.")]
    s51_cols = re.findall(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|", s51)

    # Section 5.2
    s52 = readme[readme.find("### 5.2."):readme.find("## 6.")]
    s52_cols = re.findall(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|", s52)

    print(f"Master A CSV: {row_cnt_a} rows, {len(hdr_a)} cols")
    print(f"Master A README: {len(s51_cols)} cols")
    assert hdr_a == s51_cols, f"Mismatch A: csv={hdr_a}, readme={s51_cols}"

    print(f"Master B CSV: {row_cnt_b} rows, {len(hdr_b)} cols")
    print(f"Master B README: {len(s52_cols)} cols")
    assert hdr_b == s52_cols, f"Mismatch B: csv={hdr_b}, readme={s52_cols}"

    # Check Section 6 counts (91 raw fields)
    s61 = readme[readme.find("### 6.1."):readme.find("### 6.2.")]
    s62 = readme[readme.find("### 6.2."):readme.find("### 6.3.")]
    s63 = readme[readme.find("### 6.3."):readme.find("## 7.")]

    cmpl_fields = re.findall(r"^\|\s*(\d+)\s*\|", s61, re.MULTILINE)
    rcl_fields = re.findall(r"^\|\s*(\d+)\s*\|", s62, re.MULTILINE)
    inv_fields = re.findall(r"^\|\s*(\d+)\s*\|", s63, re.MULTILINE)

    print(f"Section 6.1 CMPL fields: {len(cmpl_fields)} (expected 51)")
    print(f"Section 6.2 RCL fields: {len(rcl_fields)} (expected 29)")
    print(f"Section 6.3 INV fields: {len(inv_fields)} (expected 11)")
    assert len(cmpl_fields) == 51, f"Expected 51 CMPL, got {len(cmpl_fields)}"
    assert len(rcl_fields) == 29, f"Expected 29 RCL, got {len(rcl_fields)}"
    assert len(inv_fields) == 11, f"Expected 11 INV, got {len(inv_fields)}"

    # Check that there are NO slices [: in 03_build_master_a.py
    with open("dataset/build_py/03_build_master_a.py", "r", encoding="utf-8") as f:
        code_a = f.read()
    assert "[:2]" not in code_a, "[:2] still in 03_build_master_a.py"

    print("=" * 60)
    print(">> ALL INTEGRITY CHECKS PASSED 100% PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_integrity()
