#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改指定目录下所有文件和文件夹的创建日期和修改日期
"""

import os
import subprocess
import datetime
import random
import argparse

# 配置参数
CONFIG = {
    'target_dir': '/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-遵义安顺/贵州医生拜访2512-遵义安顺-送审',
    'target_date': '20251211',  # 目标日期，格式：YYYYMMDD
    'target_hour': 23,  # 目标小时，0-23
    'time_window': 30,  # 时间窗口，前后30分钟
}

def generate_random_time():
    """生成目标时间前后30分钟内的随机时间"""
    # 解析目标日期
    year = int(CONFIG['target_date'][:4])
    month = int(CONFIG['target_date'][4:6])
    day = int(CONFIG['target_date'][6:8])
    
    # 生成基础时间
    base_time = datetime.datetime(year, month, day, CONFIG['target_hour'], 0, 0)
    
    # 生成前后30分钟内的随机分钟数
    random_minutes = random.randint(-CONFIG['time_window'], CONFIG['time_window'])
    
    # 计算最终时间
    target_time = base_time + datetime.timedelta(minutes=random_minutes)
    
    return target_time

def modify_file_time(file_path):
    """修改文件或文件夹的创建时间和修改时间"""
    # 生成随机时间
    target_time = generate_random_time()
    
    # 格式化时间为shell命令需要的格式
    time_str = target_time.strftime('%Y%m%d%H%M')
    
    try:
        # 使用touch命令修改文件的访问时间和修改时间
        # -t 参数指定时间，-a 修改访问时间，-m 修改修改时间
        subprocess.run(['touch', '-t', time_str, '-a', '-m', file_path], check=True)
        
        # 在macOS上，修改创建时间需要使用SetFile命令（需要安装Xcode命令行工具）
        # SetFile -d "MM/dd/yyyy hh:mm:ss" file
        create_time_str = target_time.strftime('%m/%d/%Y %H:%M:%S')
        subprocess.run(['SetFile', '-d', create_time_str, file_path], check=True)
        
        print(f"Successfully modified: {file_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error modifying {file_path}: {e}")
        return False

def main():
    """主函数"""
    # 遍历目标目录
    for root, dirs, files in os.walk(CONFIG['target_dir']):
        # 先修改当前目录下的文件
        for file in files:
            file_path = os.path.join(root, file)
            modify_file_time(file_path)
        
        # 再修改当前目录
        modify_file_time(root)
    
    print("\nAll files and directories have been processed!")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Modify file and directory dates')
    parser.add_argument('--dir', type=str, help='Target directory')
    parser.add_argument('--date', type=str, help='Target date (YYYYMMDD)')
    parser.add_argument('--hour', type=int, help='Target hour (0-23)')
    
    args = parser.parse_args()
    
    # 更新配置
    if args.dir:
        CONFIG['target_dir'] = args.dir
    if args.date:
        CONFIG['target_date'] = args.date
    if args.hour is not None:
        CONFIG['target_hour'] = args.hour
    
    main()
