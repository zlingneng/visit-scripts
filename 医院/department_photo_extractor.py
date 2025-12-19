import pandas as pd
import os
import random
import subprocess
from collections import defaultdict
from datetime import datetime

# 配置路径
EXCEL_FILE_PATH = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访251201-20张令能余荷英/贵州医生拜访251201-20-张令能/贵州医生拜访251201-20-张令能.xlsx"
VIDEO_BASE_PATH = "/Users/a000/Pictures/医院2512"
OUTPUT_PHOTO_PATH = os.path.join(os.path.dirname(EXCEL_FILE_PATH), "科室")

# 配置参数
TOTAL_PHOTOS_NEEDED = 140  # 总共需要截取的照片数

def analyze_hospital_data():
    """
    分析Excel数据，统计各医院各科室拜访总量
    排除每天最早和最晚的拜访记录
    """
    try:
        # 读取Excel文件
        df = pd.read_excel(EXCEL_FILE_PATH)
        
        # 数据清洗：去除空值和重复值
        df.dropna(subset=['日期', '医院名称', '科室'], inplace=True)
        df.drop_duplicates(inplace=True)
        
        # 转换日期和时间列为datetime类型
        df['日期'] = pd.to_datetime(df['日期'])
        df['拜访开始时间'] = pd.to_datetime(df['拜访开始时间'], format='%H:%M').dt.time
        df['拜访结束时间'] = pd.to_datetime(df['拜访结束时间'], format='%H:%M').dt.time
        
        # 按日期分组，排除每天最早和最晚的拜访记录
        filtered_data = []
        for date, group in df.groupby('日期'):
            # 找到当天最早的和最晚的拜访时间
            earliest_time = group['拜访开始时间'].min()
            latest_time = group['拜访开始时间'].max()
            
            # 过滤掉最早和最晚的记录
            filtered_group = group[
                (group['拜访开始时间'] != earliest_time) & 
                (group['拜访开始时间'] != latest_time)
            ]
            
            filtered_data.append(filtered_group)
        
        # 合并过滤后的数据
        if filtered_data:
            filtered_df = pd.concat(filtered_data, ignore_index=True)
        else:
            filtered_df = pd.DataFrame(columns=df.columns)
        
        # 统计各医院各科室的拜访总量
        hospital_dept_counts = defaultdict(lambda: defaultdict(int))
        for _, row in filtered_df.iterrows():
            hospital = row['医院名称']
            department = row['科室']
            hospital_dept_counts[hospital][department] += 1
            
        return hospital_dept_counts
    
    except Exception as e:
        print(f"分析Excel数据时出错: {e}")
        return {}

def get_hospital_code_mapping():
    """
    从Excel的"导出计数_列B"标签页获取医院名称到编号的映射
    """
    try:
        # 读取"导出计数_列B"标签页
        df = pd.read_excel(EXCEL_FILE_PATH, sheet_name='导出计数_列B')
        
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
            
            return mapping
        else:
            print("导出计数_列B标签页列数不足")
            return {}
            
    except Exception as e:
        print(f"读取导出计数_列B标签页时出错: {e}")
        return {}

def scan_department_videos(hospital_dept_counts):
    """
    扫描各医院各科室文件夹中的视频文件
    返回有视频文件的科室列表及其对应的文件数量
    """
    dept_with_videos = defaultdict(list)
    
    try:
        # 遍历医院文件夹
        for hospital_name in hospital_dept_counts.keys():
            hospital_path = os.path.join(VIDEO_BASE_PATH, hospital_name)
            
            # 检查医院文件夹是否存在
            if os.path.exists(hospital_path) and os.path.isdir(hospital_path):
                # 遍历科室文件夹（排除"大门"文件夹）
                for dept_folder in os.listdir(hospital_path):
                    dept_path = os.path.join(hospital_path, dept_folder)
                    
                    # 检查是否为文件夹且不是"大门"文件夹
                    if os.path.isdir(dept_path) and dept_folder != "大门":
                        # 检查该科室是否在统计数据中
                        if dept_folder in hospital_dept_counts[hospital_name]:
                            # 统计MOV文件数量
                            mov_files = [f for f in os.listdir(dept_path) if f.lower().endswith('.mov')]
                            
                            # 如果有视频文件，则记录该科室
                            if mov_files:
                                dept_with_videos[(hospital_name, dept_folder)] = {
                                    'files': mov_files,
                                    'max_photos': hospital_dept_counts[hospital_name][dept_folder]
                                }
        
        return dept_with_videos
    
    except Exception as e:
        print(f"扫描视频文件时出错: {e}")
        return {}

def distribute_photos_randomly(dept_with_videos, total_photos_needed):
    """
    在满足约束条件下，随机分配照片数量给各个科室
    """
    # 创建科室列表，每个科室根据其最大照片数重复相应次数
    dept_list = []
    for dept_key, dept_info in dept_with_videos.items():
        max_photos = min(dept_info['max_photos'], len(dept_info['files']) * 5)  # 简化处理，假设每个视频最多抽10张照片
        dept_list.extend([dept_key] * max_photos)
    
    # 随机分配照片
    photo_allocation = defaultdict(int)
    for _ in range(total_photos_needed):
        if dept_list:
            # 随机选择一个科室
            selected_dept = random.choice(dept_list)
            photo_allocation[selected_dept] += 1
            
            # 更新科室列表，避免某个科室分配过多
            dept_list = [dept for dept in dept_list if dept != selected_dept or photo_allocation[dept] < dept_with_videos[dept]['max_photos']]
    
    return photo_allocation

def extract_frames_from_video(video_path, output_path, num_frames):
    """
    从视频中抽取指定数量的帧并保存为图片
    """
    try:
        # 使用ffmpeg抽取帧
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f'fps={num_frames}/$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {video_path})',
            '-q:v', '2',  # 图片质量
            output_path
        ]
        
        # 简化处理，实际应用中可能需要更复杂的帧选择逻辑
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vframes', str(num_frames),
            '-q:v', '2',
            output_path
        ]
        
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"从视频 {video_path} 抽取帧时出错: {e}")
        return False

def process_department_photos(dept_with_videos, photo_allocation, hospital_codes):
    """
    处理各科室照片抽取和保存
    """
    photo_counter = 0  # 照片计数器
    
    # 确保输出目录存在
    os.makedirs(OUTPUT_PHOTO_PATH, exist_ok=True)
    
    # 遍历分配了照片的科室
    for (hospital_name, dept_name), num_photos in photo_allocation.items():
        if num_photos <= 0:
            continue
            
        # 获取医院编号
        hospital_code = hospital_codes.get(hospital_name, 'UNKNOWN')
        
        # 获取科室视频信息
        dept_info = dept_with_videos[(hospital_name, dept_name)]
        mov_files = dept_info['files']
        
        # 获取每个MOV文件的信息
        mov_info = []  # [(文件名, 持续时间, 累积开始时间, 累积结束时间)]
        cumulative_time = 0
        
        for mov_file in mov_files:
            video_path = os.path.join(VIDEO_BASE_PATH, hospital_name, dept_name, mov_file)
            try:
                # 使用ffprobe获取视频持续时间
                cmd = [
                    'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', video_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                duration = float(result.stdout.strip())
                
                start_time = cumulative_time
                end_time = cumulative_time + duration
                mov_info.append((mov_file, duration, start_time, end_time))
                cumulative_time += duration
            except Exception as e:
                print(f"  无法读取{mov_file}的持续时间: {e}")
        
        if not mov_info:
            print(f"在{hospital_name}/{dept_name}中未找到有效的视频文件")
            continue
        
        total_duration = cumulative_time
        print(f"科室 {hospital_name}/{dept_name} 总时长: {total_duration:.2f}秒")
        
        # 将总时长按照需要的照片数量均等分割
        segment_duration = total_duration / num_photos
        print(f"每个时间段长度: {segment_duration:.2f}秒")
        
        # 抽取照片
        success_count = 0
        for i in range(num_photos):
            # 计算当前时间段的范围
            segment_start = i * segment_duration
            segment_end = (i + 1) * segment_duration
            
            # 在时间段内随机选择时间点
            target_time = random.uniform(segment_start, segment_end)
            
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
            video_path = os.path.join(VIDEO_BASE_PATH, hospital_name, dept_name, mov_file)
            
            # 计算在该MOV文件内的相对时间
            relative_time = target_time - start_time
            if relative_time < 0:
                relative_time = 0
            elif relative_time >= duration:
                relative_time = duration - 0.1  # 避免超出文件长度
            
            # 抽取指定时间的帧
            photo_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{hospital_code}_{dept_name}_{mov_file.split('.')[0]}_{timestamp}_{photo_counter:03d}.png"
            output_path = os.path.join(OUTPUT_PHOTO_PATH, output_filename)
            
            # 使用ffmpeg抽取指定时间点的帧
            frame_cmd = [
                'ffmpeg',
                '-ss', str(relative_time),  # 指定时间点
                '-i', video_path,
                '-vframes', '1',  # 只抽取一帧
                '-q:v', '2',  # 图片质量
                output_path
            ]
            
            try:
                subprocess.run(frame_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                print(f"已保存照片: {output_filename} (时间: {target_time:.2f}s)")
                success_count += 1
            except Exception as e:
                print(f"抽取帧时出错: {e}")
        
        print(f"科室 {hospital_name}/{dept_name} 成功抽取{success_count}/{num_photos}张照片")

def main():
    print("开始处理医院科室照片抽取...")
    
    # 1. 分析Excel数据
    print("1. 分析Excel数据...")
    hospital_dept_counts = analyze_hospital_data()
    if not hospital_dept_counts:
        print("无法分析Excel数据，程序退出。")
        return
    
    # 2. 获取医院编号映射
    print("2. 获取医院编号映射...")
    hospital_codes = get_hospital_code_mapping()
    
    # 3. 扫描科室视频文件
    print("3. 扫描科室视频文件...")
    dept_with_videos = scan_department_videos(hospital_dept_counts)
    if not dept_with_videos:
        print("未找到任何有视频文件的科室，程序退出。")
        return
    
    # 4. 随机分配照片数量
    print("4. 随机分配照片数量...")
    photo_allocation = distribute_photos_randomly(dept_with_videos, TOTAL_PHOTOS_NEEDED)
    if not photo_allocation:
        print("无法分配照片数量，程序退出。")
        return
    
    # 5. 处理照片抽取和保存
    print("5. 处理照片抽取和保存...")
    process_department_photos(dept_with_videos, photo_allocation, hospital_codes)
    
    print("照片抽取完成！")

if __name__ == "__main__":
    main()