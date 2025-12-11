#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科室照片重命名工具

根据Excel文件中的拜访计划数据，将科室照片按照规则重命名：
1. 匹配文件名中的第一个编号与Excel中医院编号
2. 根据科室名称与拜访记录匹配
3. 不匹配各医院每天最早最晚的拜访记录
4. 匹配上的照片随机分配相应原序号作为照片名称
"""

import pandas as pd
import os
import random
import re
from pathlib import Path
from collections import defaultdict

# ==================== 配置部分 ====================
# Excel文件路径
EXCEL_FILE_PATH = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-贵阳/贵州医生拜访2512-贵阳1-11徐桂莲何玲周星贤/贵州医生拜访2512-贵阳1-11徐桂莲何玲周星贤.xlsx"

# 照片文件夹路径
PHOTO_FOLDER_PATH = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-贵阳/贵州医生拜访2512-贵阳1-11徐桂莲何玲周星贤/科室"

# 目标文件夹路径（重命名后的照片将保存到这里）
TARGET_FOLDER_PATH = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-贵阳/贵州医生拜访2512-贵阳1-11徐桂莲何玲周星贤/重命名后科室照片"

# ==================== 脚本主体 ====================

def load_excel_data():
    """加载Excel文件中的数据"""
    print("正在读取Excel文件...")
    
    # 读取导出计数_列B工作表（医院编号与医院名称对应关系）
    hospital_mapping_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name='导出计数_列B')
    hospital_mapping = {}
    for _, row in hospital_mapping_df.iterrows():
        if pd.notna(row['编号']) and pd.notna(row['列B']):
            hospital_mapping[int(row['编号'])] = row['列B']
    
    print(f"加载了 {len(hospital_mapping)} 个医院的编号映射关系")
    
    # 读取拜访计划工作表
    visit_plan_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name='拜访计划')
    
    # 转换日期列为datetime类型
    visit_plan_df['日期'] = pd.to_datetime(visit_plan_df['日期'])
    
    print(f"加载了 {len(visit_plan_df)} 条拜访记录")
    return hospital_mapping, visit_plan_df

def filter_early_late_visits(visit_plan_df):
    """过滤掉每天每家医院最早和最晚的拜访记录"""
    print("正在过滤每天每家医院最早和最晚的拜访记录...")
    
    filtered_data = []
    
    # 按日期和医院分组
    for (date, hospital), group in visit_plan_df.groupby(['日期', '医院名称']):
        if len(group) <= 2:
            # 如果某天某医院的拜访记录少于等于2条，则全部过滤掉
            continue
        
        # 转换时间列为datetime类型以便比较
        group = group.copy()
        group['拜访开始时间_dt'] = pd.to_datetime(group['拜访开始时间'], format='%H:%M').dt.time
        
        # 找到最早和最晚的时间
        earliest_time = group['拜访开始时间_dt'].min()
        latest_time = group['拜访开始时间_dt'].max()
        
        # 过滤掉最早和最晚的记录
        filtered_group = group[
            (group['拜访开始时间_dt'] != earliest_time) & 
            (group['拜访开始时间_dt'] != latest_time)
        ]
        
        filtered_data.append(filtered_group)
    
    # 合并过滤后的数据
    if filtered_data:
        filtered_df = pd.concat(filtered_data, ignore_index=True)
        print(f"过滤后剩余 {len(filtered_df)} 条拜访记录")
        return filtered_df
    else:
        print("过滤后没有剩余记录")
        return pd.DataFrame()

def create_visit_mapping(filtered_df, hospital_mapping):
    """创建拜访记录映射：编号_科室 -> [原序号列表]"""
    print("正在创建拜访记录映射...")
    
    # 创建映射字典：编号_科室 -> [原序号列表]
    visit_mapping = defaultdict(list)
    
    for _, row in filtered_df.iterrows():
        # 查找医院编号
        hospital_name = row['医院名称']
        hospital_id = None
        for id, name in hospital_mapping.items():
            if name == hospital_name:
                hospital_id = id
                break
        
        if hospital_id is not None:
            key = f"{hospital_id}_{row['科室']}"
            visit_mapping[key].append(int(row['原序号']))
    
    print(f"创建了 {len(visit_mapping)} 个科室的拜访记录映射")
    return visit_mapping

def process_photos(visit_mapping):
    """处理照片文件重命名"""
    print("正在处理照片文件重命名...")
    
    # 创建目标文件夹
    os.makedirs(TARGET_FOLDER_PATH, exist_ok=True)
    
    # 获取照片文件夹中的所有文件
    photo_files = [f for f in os.listdir(PHOTO_FOLDER_PATH) 
                   if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    print(f"找到 {len(photo_files)} 个照片文件")
    
    # 用于跟踪已使用的原序号
    used_numbers = defaultdict(set)
    
    # 处理每个照片文件
    renamed_count = 0
    for photo_file in photo_files:
        # 从文件名中提取编号和科室
        match = re.match(r'^(\d+)_(.+?)_', photo_file)
        if match:
            photo_id = int(match.group(1))
            photo_dept = match.group(2)
            key = f"{photo_id}_{photo_dept}"
            
            # 检查是否有匹配的拜访记录
            if key in visit_mapping and visit_mapping[key]:
                # 获取可用的原序号列表（排除已使用的）
                available_numbers = [num for num in visit_mapping[key] 
                                   if num not in used_numbers[key]]
                
                if available_numbers:
                    # 随机选择一个原序号
                    selected_number = random.choice(available_numbers)
                    used_numbers[key].add(selected_number)
                    
                    # 创建新文件名
                    file_extension = os.path.splitext(photo_file)[1]
                    new_filename = f"{selected_number}{file_extension}"
                    new_filepath = os.path.join(TARGET_FOLDER_PATH, new_filename)
                    
                    # 复制文件到目标文件夹并重命名
                    old_filepath = os.path.join(PHOTO_FOLDER_PATH, photo_file)
                    try:
                        # 使用复制而不是移动，保留原文件
                        with open(old_filepath, 'rb') as src, open(new_filepath, 'wb') as dst:
                            dst.write(src.read())
                        print(f"重命名: {photo_file} -> {new_filename}")
                        renamed_count += 1
                    except Exception as e:
                        print(f"复制文件 {photo_file} 时出错: {e}")
                else:
                    print(f"警告: 照片 {photo_file} 对应的科室已无可用原序号")
            else:
                print(f"警告: 照片 {photo_file} 未找到匹配的拜访记录 ({key})")
        else:
            print(f"警告: 无法解析照片文件名 {photo_file}")
    
    print(f"成功重命名 {renamed_count} 个照片文件")

def main():
    """主函数"""
    print("=== 科室照片重命名工具 ===")
    
    try:
        # 加载Excel数据
        hospital_mapping, visit_plan_df = load_excel_data()
        
        # 过滤掉每天每家医院最早和最晚的拜访记录
        filtered_df = filter_early_late_visits(visit_plan_df)
        
        # 创建拜访记录映射
        visit_mapping = create_visit_mapping(filtered_df, hospital_mapping)
        
        # 处理照片重命名
        process_photos(visit_mapping)
        
        print("=== 处理完成 ===")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()