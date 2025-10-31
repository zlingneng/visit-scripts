import pandas as pd
import os
import random
import shutil
from pathlib import Path

def analyze_excel_file(excel_file):
    """分析Excel文件结构"""
    
    try:
        # 读取所有工作表
        xl_file = pd.ExcelFile(excel_file)
        print(f"工作表列表: {xl_file.sheet_names}")
        
        # 读取拜访计划工作表
        if '拜访计划' in xl_file.sheet_names:
            visit_plan = pd.read_excel(excel_file, sheet_name='拜访计划')
            print("\n拜访计划工作表结构:")
            print(f"列名: {list(visit_plan.columns)}")
            print(f"数据行数: {len(visit_plan)}")
            print("\n前5行数据:")
            print(visit_plan.head())
        
        # 读取导出计数_列B工作表
        if '导出计数_列B' in xl_file.sheet_names:
            hospital_count = pd.read_excel(excel_file, sheet_name='导出计数_列B')
            print("\n导出计数_列B工作表结构:")
            print(f"列名: {list(hospital_count.columns)}")
            print(f"数据行数: {len(hospital_count)}")
            print("\n前5行数据:")
            print(hospital_count.head())
            
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")

def check_photos_directory(photo_dir):
    """检查照片目录"""
    
    if not os.path.exists(photo_dir):
        print(f"照片目录不存在: {photo_dir}")
        return []
    
    # 获取以数字-或数字_开头的照片文件
    photo_files = []
    for file in os.listdir(photo_dir):
        if is_valid_photo_filename(file):
            photo_files.append(file)
    
    print(f"\n找到 {len(photo_files)} 张以数字-或数字_开头的照片:")
    for photo in sorted(photo_files)[:10]:  # 显示前10张
        print(f"  {photo}")
    if len(photo_files) > 10:
        print(f"  ... 还有 {len(photo_files) - 10} 张照片")
    
    return photo_files

def is_valid_photo_filename(filename):
    """检查文件名是否符合以数字-或数字_开头的格式"""
    if '-' in filename:
        parts = filename.split('-', 1)  # 只分割第一个-
        if parts[0].isdigit():
            return True
    if '_' in filename:
        parts = filename.split('_', 1)  # 只分割第一个_
        if parts[0].isdigit():
            return True
    return False

def extract_hospital_number(filename):
    """从文件名中提取医院编号"""
    if '-' in filename:
        return int(filename.split('-', 1)[0])
    elif '_' in filename:
        return int(filename.split('_', 1)[0])
    else:
        raise ValueError(f"无法从文件名 {filename} 中提取医院编号")

def process_photo_renaming(excel_file, photo_dir):
    """处理照片重命名的主要逻辑"""
    
    try:
        # 读取拜访计划和医院编号对应关系
        visit_plan = pd.read_excel(excel_file, sheet_name='拜访计划')
        hospital_mapping = pd.read_excel(excel_file, sheet_name='导出计数_列B')
        
        print("拜访计划列名:", list(visit_plan.columns))
        print("医院映射列名:", list(hospital_mapping.columns))
        
        # 创建医院名称到编号的映射
        # 先过滤掉NaN值，然后转换为整数
        valid_mapping = hospital_mapping.dropna(subset=['编号', '列B'])
        hospital_to_number = dict(zip(valid_mapping['列B'], valid_mapping['编号'].astype(int)))
        print("\n医院编号映射:")
        for hospital, number in hospital_to_number.items():
            print(f"  {number}: {hospital}")
        
        # 分析拜访计划，找出每天每家医院的最早和最晚时间
        visit_plan['日期'] = pd.to_datetime(visit_plan['日期'])
        
        # 按日期和医院分组，找出每组的最早和最晚时间
        daily_hospital_schedule = []
        
        for (date, hospital), group in visit_plan.groupby(['日期', '医院名称']):
            # 转换时间列为时间格式进行比较
            times = pd.to_datetime(group['拜访开始时间'], format='%H:%M', errors='coerce')
            
            earliest_idx = times.idxmin()
            latest_idx = times.idxmax()
            
            # 最早时间的记录
            earliest_record = group.loc[earliest_idx]
            daily_hospital_schedule.append({
                '原序号': earliest_record['原序号'],
                '日期': date.strftime('%Y/%m/%d'),
                '医院': hospital,
                '医院编号': int(hospital_to_number.get(hospital, 0)),
                '时间': earliest_record['拜访开始时间'],
                '类型': '最早'
            })
            
            # 如果最早和最晚不是同一条记录，添加最晚时间的记录
            if earliest_idx != latest_idx:
                latest_record = group.loc[latest_idx]
                daily_hospital_schedule.append({
                    '原序号': latest_record['原序号'],
                    '日期': date.strftime('%Y/%m/%d'),
                    '医院': hospital,
                    '医院编号': int(hospital_to_number.get(hospital, 0)),
                    '时间': latest_record['拜访开始时间'],
                    '类型': '最晚'
                })
        
        # 显示需要照片的记录
        print(f"\n需要照片的记录数: {len(daily_hospital_schedule)}")
        for record in daily_hospital_schedule:
            print(f"原序号 {record['原序号']}: {record['日期']} {record['医院']} {record['时间']} ({record['类型']})")
        
        # 获取照片文件
        if not os.path.exists(photo_dir):
            print(f"照片目录不存在: {photo_dir}")
            return
        
        photo_files = []
        for file in os.listdir(photo_dir):
            if is_valid_photo_filename(file):
                photo_files.append(file)
        
        print(f"\n找到 {len(photo_files)} 张照片")
        
        # 按医院编号分组照片
        photos_by_hospital = {}
        for photo in photo_files:
            try:
                hospital_num = extract_hospital_number(photo)
                if hospital_num not in photos_by_hospital:
                    photos_by_hospital[hospital_num] = []
                photos_by_hospital[hospital_num].append(photo)
            except ValueError as e:
                print(f"警告: 无法处理照片 {photo} - {e}")
        
        print("\n按医院分组的照片数量:")
        for hospital_num, photos in photos_by_hospital.items():
            hospital_name = next((name for name, num in hospital_to_number.items() if int(num) == hospital_num), f"未知医院{hospital_num}")
            print(f"  医院 {int(hospital_num)} ({hospital_name}): {len(photos)} 张照片")
        
        # 执行重命名
        rename_count = 0
        for record in daily_hospital_schedule:
            hospital_num = record['医院编号']
            target_name = f"{record['原序号']}"
            
            if hospital_num in photos_by_hospital and photos_by_hospital[hospital_num]:
                # 随机选择一张照片
                selected_photo = random.choice(photos_by_hospital[hospital_num])
                photos_by_hospital[hospital_num].remove(selected_photo)
                
                # 获取文件扩展名
                file_ext = os.path.splitext(selected_photo)[1]
                
                # 构建新文件名
                new_filename = f"{target_name}{file_ext}"
                
                # 在原文件夹直接重命名
                old_path = os.path.join(photo_dir, selected_photo)
                new_path = os.path.join(photo_dir, new_filename)
                
                try:
                    os.rename(old_path, new_path)
                    print(f"重命名: {selected_photo} -> {new_filename}")
                    rename_count += 1
                except Exception as e:
                    print(f"重命名失败 {selected_photo}: {e}")
            else:
                print(f"警告: 医院 {int(hospital_num)} ({record['医院']}) 没有可用照片用于原序号 {record['原序号']}")
        
        print(f"\n重命名完成，共处理 {rename_count} 张照片")
        
    except Exception as e:
        print(f"处理过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # ==================== 配置区域 ====================
    # 输入文件路径
    EXCEL_FILE = '/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/贵州医生拜访2510-何勇-蔡林川-周星贤.xlsx'
    
    # 目录路径
    PHOTO_DIR = '/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/照片2'
    # ================================================
    
    print("=== 分析Excel文件 ===")
    analyze_excel_file(EXCEL_FILE)
    
    print("\n=== 检查照片目录 ===")
    check_photos_directory(PHOTO_DIR)
    
    print("\n=== 开始照片重命名 ===")
    process_photo_renaming(EXCEL_FILE, PHOTO_DIR)