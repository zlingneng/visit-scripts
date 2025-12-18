#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据Excel文件中的医院名称和科室信息，在指定文件夹中创建相应的文件夹结构
"""

import pandas as pd
import os
from pathlib import Path

# ==================== 配置区域 ====================
# 在这里修改所有配置参数

# Excel文件路径
EXCEL_FILE_PATH = "/Users/a000/Documents/济生/医院拜访25/贵州省医院医生信息_20251207.xlsx"

# 目标图片文件夹路径
TARGET_FOLDER_PATH = "/Users/a000/Pictures/医院2512"

# Excel工作表名称
SHEET_NAME = "导出筛选结果"

# 城市筛选配置：只处理指定城市的医院，为空列表则处理所有城市
# 示例：['贵阳'] - 只处理贵阳的医院；[] - 处理所有城市
CITY_CONFIG = ['贵阳']

# ==================== 配置结束 ====================

def clean_name(name):
    """清理文件夹名称中的特殊字符"""
    clean_name = str(name).strip()
    # 移除可能引起问题的字符
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        clean_name = clean_name.replace(char, '')
    return clean_name

def create_hospital_folders():
    """根据Excel文件创建医院和科室文件夹"""
    print("开始读取Excel文件...")
    
    try:
        # 读取Excel文件中的指定工作表
        df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=SHEET_NAME)
        print(f"成功读取数据，共{len(df)}条记录")
        print(f"列名：{list(df.columns)}")
        
        # 根据城市配置筛选数据
        if CITY_CONFIG:
            df = df[df['所属城市'].isin(CITY_CONFIG)]
            print(f"根据城市筛选条件{', '.join(CITY_CONFIG)}，筛选后剩余{len(df)}条记录")
            
            if len(df) == 0:
                print("筛选后没有符合条件的数据，程序将退出")
                return
        
        # 获取唯一的医院名称
        hospitals = df['医院名称'].unique()
        print(f"共找到{len(hospitals)}家医院")
        
        # 创建计数器
        created_hospitals = 0
        created_departments = 0
        skipped_hospitals = 0
        updated_hospitals = 0
        
        # 为每个医院创建文件夹
        for hospital in hospitals:
            # 清理医院名称中的特殊字符，避免文件夹命名问题
            clean_hospital_name = clean_name(hospital)
            
            # 创建医院文件夹路径
            hospital_folder_path = os.path.join(TARGET_FOLDER_PATH, clean_hospital_name)
            
            # 检查医院文件夹是否已存在
            if os.path.exists(hospital_folder_path):
                print(f"处理已存在的医院文件夹: {clean_hospital_name}")
                skipped_hospitals += 1
                
                # 检查是否已存在"大门"文件夹，如果不存在则创建
                gate_folder_path = os.path.join(hospital_folder_path, "大门")
                if not os.path.exists(gate_folder_path):
                    os.makedirs(gate_folder_path)
                    print(f"  创建大门文件夹")
            else:
                # 创建医院文件夹
                try:
                    os.makedirs(hospital_folder_path)
                    print(f"创建医院文件夹: {clean_hospital_name}")
                    created_hospitals += 1
                    
                    # 为该医院创建"大门"文件夹
                    gate_folder_path = os.path.join(hospital_folder_path, "大门")
                    os.makedirs(gate_folder_path)
                    print(f"  创建大门文件夹")
                except Exception as e:
                    print(f"创建医院文件夹时出错 {clean_hospital_name}: {e}")
                    continue
            
            # 获取该医院的所有科室
            hospital_df = df[df['医院名称'] == hospital]
            departments = hospital_df['科室'].unique()
            
            # 为每个科室创建文件夹（包括已存在的医院）
            departments_created = 0
            for department in departments:
                # 清理科室名称中的特殊字符
                clean_department_name = clean_name(department)
                
                # 创建科室文件夹路径
                department_folder_path = os.path.join(hospital_folder_path, clean_department_name)
                
                # 检查科室文件夹是否已存在，如果不存在则创建
                if not os.path.exists(department_folder_path):
                    try:
                        os.makedirs(department_folder_path)
                        print(f"  创建科室文件夹: {clean_department_name}")
                        created_departments += 1
                        departments_created += 1
                    except Exception as e:
                        print(f"  创建科室文件夹时出错 {clean_department_name}: {e}")
            
            if departments_created > 0:
                print(f"  为{clean_hospital_name}新增了{departments_created}个科室文件夹")
                if os.path.exists(hospital_folder_path):
                    updated_hospitals += 1
        
        print("\n=== 创建完成 ===")
        print(f"新创建医院文件夹数量: {created_hospitals}")
        print(f"处理已存在医院文件夹数量: {skipped_hospitals}")
        print(f"更新科室信息的医院数量: {updated_hospitals}")
        print(f"创建科室文件夹数量: {created_departments}")
        print(f"额外创建'大门'文件夹数量: {created_hospitals}")
        
    except Exception as e:
        print(f"读取Excel文件或创建文件夹时出错: {e}")

if __name__ == "__main__":
    create_hospital_folders()