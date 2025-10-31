#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
药店拜访文件重命名脚本
功能：
1. 扫描指定目录中的PNG文件
2. 去掉文件名中的"-2"后缀（如果存在）
3. 根据Excel表格中的对应关系重命名文件
"""

import os
import pandas as pd
import re
from pathlib import Path

# 配置参数
TARGET_DIR = "/Users/a000/Downloads/2504何勇"
EXCEL_FILE = "/Users/a000/Downloads/2504何勇/贵州药店拜访2504何勇.xlsx"
SHEET_NAME = "Sheet2"
ORIGINAL_ID_COLUMN = "原编号"
VISIT_ID_COLUMN = "拜访编号"

def scan_png_files(directory):
    """扫描目录中的PNG文件"""
    png_files = []
    try:
        for file in os.listdir(directory):
            if file.lower().endswith('.png'):
                png_files.append(file)
        print(f"找到 {len(png_files)} 个PNG文件")
        return png_files
    except Exception as e:
        print(f"扫描目录失败: {e}")
        return []

def remove_suffix_2(filename):
    """去掉文件名中的-2后缀"""
    # 匹配文件名中的-2（在扩展名前）
    pattern = r'(.+)-2(\.png)$'
    match = re.match(pattern, filename, re.IGNORECASE)
    if match:
        return match.group(1) + match.group(2)
    return filename

def load_mapping_data(excel_file, sheet_name, original_col, visit_col):
    """从Excel文件加载映射数据"""
    try:
        # 使用第3行作为表头（header=2，因为索引从0开始）
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=2)
        print(f"Excel文件加载成功，共 {len(df)} 行数据")
        print(f"列名: {list(df.columns)}")
        
        # 检查列是否存在
        if original_col not in df.columns:
            print(f"警告：未找到列 '{original_col}'")
            return {}
        if visit_col not in df.columns:
            print(f"警告：未找到列 '{visit_col}'")
            return {}
        
        # 创建映射字典，去除空值
        mapping = {}
        for _, row in df.iterrows():
            original = str(row[original_col]).strip() if pd.notna(row[original_col]) else ''
            visit = str(row[visit_col]).strip() if pd.notna(row[visit_col]) else ''
            if original and original != 'nan' and visit and visit != 'nan':
                mapping[original] = visit
        
        print(f"有效映射关系 {len(mapping)} 条")
        return mapping
    except Exception as e:
        print(f"读取Excel文件失败: {e}")
        return {}

def preview_changes(png_files, mapping):
    """预览将要进行的重命名操作"""
    print("\n=== 重命名预览 ===")
    changes = []
    
    for filename in png_files:
        # 先去掉-2后缀
        cleaned_name = remove_suffix_2(filename)
        
        # 提取文件名（不含扩展名）
        name_without_ext = os.path.splitext(cleaned_name)[0]
        
        # 查找映射
        if name_without_ext in mapping:
            new_name = mapping[name_without_ext] + '.png'
            changes.append((filename, new_name))
            print(f"{filename} -> {new_name}")
        else:
            print(f"{filename} -> 未找到对应的拜访编号")
    
    return changes

def rename_files(directory, changes):
    """执行文件重命名"""
    print("\n=== 开始重命名 ===")
    success_count = 0
    
    for old_name, new_name in changes:
        old_path = os.path.join(directory, old_name)
        new_path = os.path.join(directory, new_name)
        
        try:
            # 检查新文件名是否已存在
            if os.path.exists(new_path):
                print(f"跳过 {old_name}: 目标文件 {new_name} 已存在")
                continue
            
            os.rename(old_path, new_path)
            print(f"✓ {old_name} -> {new_name}")
            success_count += 1
        except Exception as e:
            print(f"✗ 重命名失败 {old_name}: {e}")
    
    print(f"\n重命名完成，成功 {success_count} 个文件")

def main():
    print("药店拜访文件重命名工具")
    print(f"目标目录: {TARGET_DIR}")
    print(f"Excel文件: {EXCEL_FILE}")
    
    # 检查目录和文件是否存在
    if not os.path.exists(TARGET_DIR):
        print(f"错误：目录不存在 {TARGET_DIR}")
        return
    
    if not os.path.exists(EXCEL_FILE):
        print(f"错误：Excel文件不存在 {EXCEL_FILE}")
        return
    
    # 扫描PNG文件
    png_files = scan_png_files(TARGET_DIR)
    if not png_files:
        print("未找到PNG文件")
        return
    
    # 加载映射数据
    mapping = load_mapping_data(EXCEL_FILE, SHEET_NAME, ORIGINAL_ID_COLUMN, VISIT_ID_COLUMN)
    if not mapping:
        print("未找到有效的映射数据")
        return
    
    # 预览更改
    changes = preview_changes(png_files, mapping)
    
    if not changes:
        print("没有需要重命名的文件")
        return
    
    # 确认执行
    print(f"\n将重命名 {len(changes)} 个文件")
    confirm = input("确认执行重命名操作？(y/N): ")
    
    if confirm.lower() in ['y', 'yes']:
        rename_files(TARGET_DIR, changes)
    else:
        print("操作已取消")

if __name__ == "__main__":
    main()