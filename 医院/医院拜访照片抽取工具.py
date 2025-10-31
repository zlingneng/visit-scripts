#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
医院拜访照片抽取工具
从Excel文件中分析拜访计划数据，统计每家医院的数据条数，
然后从对应医院的大门文件夹中随机抽取MOV文件帧并保存为PNG格式。
"""

import pandas as pd
import os
import random
import cv2
import math
from pathlib import Path
import numpy as np
from scipy.stats import beta

def analyze_hospital_data(excel_path, sheet_name='拜访计划'):
    """
    分析Excel文件中的医院拜访数据
    找出每天每家医院最早最晚的数据，统计每家医院数据条数
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print(f"成功读取Excel文件，共{len(df)}行数据")
        print(f"列名: {list(df.columns)}")
        
        # 显示前几行数据以便确认结构
        print("\n前5行数据:")
        print(df.head())
        
        # 查找医院列
        hospital_column = None
        for col in df.columns:
            if '医院' in str(col) or 'hospital' in str(col).lower():
                hospital_column = col
                break
        
        if hospital_column is None:
            print("未找到医院列，请手动指定医院列名")
            print("可用列名:", list(df.columns))
            return None
        
        # 查找日期/时间列
        date_column = None
        time_column = None
        for col in df.columns:
            col_str = str(col).lower()
            if '日期' in col_str or 'date' in col_str:
                date_column = col
            elif '时间' in col_str or 'time' in col_str:
                time_column = col
        
        print(f"\n使用医院列: {hospital_column}")
        print(f"使用日期列: {date_column}")
        print(f"使用时间列: {time_column}")
        
        # 统计每家医院需要的照片数量（基于每天最早最晚数据）
        hospital_counts = {}
        
        # 如果有日期和时间列，进行详细分析
        if date_column is not None:
            # 确保日期列是datetime格式
            if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
                df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            # 按日期和医院分组，找出每天每家医院的最早最晚数据
            df['日期'] = df[date_column].dt.date
            
            print("\n=== 每天每家医院的最早最晚数据分析 ===")
            
            for date in df['日期'].unique():
                if pd.isna(date):
                    continue
                    
                date_data = df[df['日期'] == date]
                print(f"\n日期: {date}")
                
                for hospital in date_data[hospital_column].unique():
                    if pd.isna(hospital):
                        continue
                        
                    hospital_day_data = date_data[date_data[hospital_column] == hospital]
                    
                    if time_column and time_column in hospital_day_data.columns:
                        # 如果有时间列，找最早最晚时间的记录
                        times = hospital_day_data[time_column].dropna()
                        if len(times) > 0:
                            earliest = times.min()
                            latest = times.max()
                            
                            # 只统计最早和最晚的记录（如果是同一条记录则只算1条）
                            if earliest == latest:
                                daily_count = 1
                            else:
                                daily_count = 2
                            
                            print(f"  {hospital}: 最早: {earliest}, 最晚: {latest}, 统计条数: {daily_count}")
                            
                            # 累加到医院总计数
                            if hospital not in hospital_counts:
                                hospital_counts[hospital] = 0
                            hospital_counts[hospital] += daily_count
                    else:
                        # 如果没有时间列，每天每家医院算1条
                        daily_count = 1
                        print(f"  {hospital}: {len(hospital_day_data)}条原始数据, 统计条数: {daily_count}")
                        
                        if hospital not in hospital_counts:
                            hospital_counts[hospital] = 0
                        hospital_counts[hospital] += daily_count
        else:
            # 如果没有日期列，使用原来的统计方法
            hospital_counts = df[hospital_column].value_counts().to_dict()
        
        print(f"\n=== 每家医院最终统计条数（用于计算照片抽取数量） ===")
        for hospital, count in hospital_counts.items():
            print(f"{hospital}: {count}条")
        
        return hospital_counts
        
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return None

def get_hospital_code_mapping(excel_path, sheet_name='导出计数_列B'):
    """
    从导出计数_列B标签页获取医院名称到编号的映射
    """
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        print(f"\n成功读取{sheet_name}标签页，共{len(df)}行数据")
        print(f"列名: {list(df.columns)}")
        
        # 显示前几行数据以便确认结构
        print("\n前5行数据:")
        print(df.head())
        
        # 根据实际数据结构调整列索引
        # 假设列A是编号，列B是医院名称
        if len(df.columns) >= 2:
            # 读取编号列（列A，索引0）和医院名称列（列B，索引1）
            codes = df.iloc[:, 0]  # 列A (索引0) - 编号
            hospital_names = df.iloc[:, 1]  # 列B (索引1) - 医院名称
            
            mapping = {}
            for code, hospital in zip(codes, hospital_names):
                # 跳过空值
                if pd.notna(code) and pd.notna(hospital):
                    # 直接使用获取到的编号数据，不进行格式化
                    if isinstance(code, (int, float)):
                        formatted_code = str(int(code))
                    else:
                        formatted_code = str(code)
                    mapping[hospital] = formatted_code
            
            print(f"医院编号映射: {mapping}")
            return mapping
        else:
            print("导出计数_列B标签页列数不足")
            return {}
            
    except Exception as e:
        print(f"读取导出计数_列B标签页时出错: {e}")
        return {}

def extract_frame_at_time(mov_path, hospital_code, mov_filename, target_time_seconds):
    """
    从MOV文件中抽取指定时间点的帧并保存为PNG
    返回生成的文件路径，如果失败返回None
    """
    try:
        cap = cv2.VideoCapture(mov_path)
        if not cap.isOpened():
            print(f"无法打开视频文件: {mov_path}")
            return None
        
        # 获取视频信息
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        if total_frames <= 0:
            print(f"视频文件帧数为0: {mov_path}")
            cap.release()
            return None
        
        if fps <= 0:
            fps = 30  # 默认帧率
        
        # 计算目标帧号
        target_frame = int(target_time_seconds * fps)
        if target_frame >= total_frames:
            target_frame = total_frames - 1
        elif target_frame < 0:
            target_frame = 0
        
        # 定位到目标帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        # 读取帧
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # 生成文件名：医院编号_MOV文件名_抽取帧秒数.png（秒数保留2位精度但不显示小数点）
            mov_name_without_ext = os.path.splitext(mov_filename)[0]
            time_str = f"{int(target_time_seconds * 100):04d}"  # 转换为整数，保留2位精度
            output_filename = f"{hospital_code}_{mov_name_without_ext}_{time_str}.png"
            
            return output_filename, frame
        else:
            print(f"无法读取帧: {mov_path}")
            return None
            
    except Exception as e:
        print(f"处理视频文件时出错: {e}")
        return None

def process_hospital_photos(hospital_counts, hospital_codes, base_photo_dir, output_dir):
    """
    为每家医院处理照片抽取
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for hospital_name, count in hospital_counts.items():
        print(f"\n处理医院: {hospital_name} (数据条数: {count})")
        
        # 计算需要抽取的照片数量
        photos_needed = math.ceil(2 * count)
        # 如果需要生成的照片数少于6张，按照6张生成
        if photos_needed < 6:
            photos_needed = 6
        print(f"需要抽取照片数量: {photos_needed}")
        
        # 构建医院大门文件夹路径
        hospital_dir = os.path.join(base_photo_dir, hospital_name, '大门')
        
        if not os.path.exists(hospital_dir):
            print(f"医院文件夹不存在: {hospital_dir}")
            continue
        
        # 获取所有MOV文件及其持续时间和累积时间
        mov_files = [f for f in os.listdir(hospital_dir) 
                    if f.lower().endswith('.mov')]
        
        if not mov_files:
            print(f"在{hospital_dir}中未找到MOV文件")
            continue
        
        print(f"找到{len(mov_files)}个MOV文件")
        
        # 获取每个MOV文件的信息
        mov_info = []  # [(文件名, 持续时间, 累积开始时间, 累积结束时间)]
        cumulative_time = 0
        
        for mov_file in mov_files:
            mov_path = os.path.join(hospital_dir, mov_file)
            try:
                cap = cv2.VideoCapture(mov_path)
                if cap.isOpened():
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if fps > 0 and frame_count > 0:
                        duration = frame_count / fps
                        start_time = cumulative_time
                        end_time = cumulative_time + duration
                        mov_info.append((mov_file, duration, start_time, end_time))
                        cumulative_time += duration
                        print(f"  {mov_file}: {duration:.2f}秒 (累积: {start_time:.2f}-{end_time:.2f}秒)")
                    cap.release()
            except Exception as e:
                print(f"  无法读取{mov_file}的持续时间: {e}")
        
        if not mov_info:
            print(f"在{hospital_dir}中未找到有效的MOV文件")
            continue
        
        total_duration = cumulative_time
        print(f"总时长: {total_duration:.2f}秒")
        
        # 获取医院编号
        hospital_code = hospital_codes.get(hospital_name, '000')
        
        # 将总时长按照需要的照片数量均等分割
        segment_duration = total_duration / photos_needed
        print(f"每个时间段长度: {segment_duration:.2f}秒")
        
        # 抽取照片
        success_count = 0
        for i in range(photos_needed):
            # 计算当前时间段的范围
            segment_start = i * segment_duration
            segment_end = (i + 1) * segment_duration
            
            # 使用对称Beta分布(a=b=2)在时间段内选择时间点，中间概率最高
            beta_sample = beta.rvs(2, 2)  # 对称Beta分布，范围[0,1]
            target_time = segment_start + beta_sample * segment_duration
            
            print(f"\n第{i+1}张照片 - 时间段: [{segment_start:.2f}, {segment_end:.2f}]秒, 目标时间: {target_time:.2f}秒")
            
            # 找到目标时间对应的MOV文件
            selected_mov_info = None
            for mov_file, duration, start_time, end_time in mov_info:
                if start_time <= target_time < end_time:
                    selected_mov_info = (mov_file, duration, start_time, end_time)
                    break
            
            if selected_mov_info is None:
                # 如果目标时间超出范围，选择最后一个文件
                selected_mov_info = mov_info[-1]
            
            mov_file, duration, start_time, end_time = selected_mov_info
            mov_path = os.path.join(hospital_dir, mov_file)
            
            # 计算在该MOV文件内的相对时间
            relative_time = target_time - start_time
            if relative_time < 0:
                relative_time = 0
            elif relative_time >= duration:
                relative_time = duration - 0.1  # 避免超出文件长度
            
            print(f"选择文件: {mov_file}, 文件内时间: {relative_time:.2f}秒")
            
            # 抽取指定时间的帧
            result = extract_frame_at_time(mov_path, hospital_code, mov_file, relative_time)
            
            if result is not None:
                output_filename, frame = result
                output_path = os.path.join(output_dir, output_filename)
                
                # 保存为PNG
                if cv2.imwrite(output_path, frame):
                    print(f"成功抽取帧并保存到: {output_path} (时间: {target_time:.2f}s)")
                    success_count += 1
                else:
                    print(f"保存图片失败: {output_path}")
            
        print(f"成功抽取{success_count}/{photos_needed}张照片")

def main():
    # 配置文件路径
    excel_path = '/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/贵州医生拜访2510-何勇-蔡林川-周星贤.xlsx'
    base_photo_dir = '/Users/a000/Pictures/医院'
    output_dir = '/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/照片'
    
    print("开始处理医院拜访照片抽取任务...")
    
    # 1. 分析拜访计划数据
    print("\n=== 步骤1: 分析拜访计划数据 ===")
    hospital_counts = analyze_hospital_data(excel_path, '拜访计划')
    
    if hospital_counts is None:
        print("无法获取医院数据，程序退出")
        return
    
    # 2. 获取医院编号映射
    print("\n=== 步骤2: 获取医院编号映射 ===")
    hospital_codes = get_hospital_code_mapping(excel_path, '导出计数_列B')
    
    # 3. 处理照片抽取
    print("\n=== 步骤3: 处理照片抽取 ===")
    process_hospital_photos(hospital_counts, hospital_codes, base_photo_dir, output_dir)
    
    print("\n任务完成！")

if __name__ == '__main__':
    main()