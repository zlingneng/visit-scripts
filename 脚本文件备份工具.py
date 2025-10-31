#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本文件备份工具
自动将指定的脚本文件复制到备份目录中，按照药店和医院分类整理
"""

import os
import shutil
from pathlib import Path

# 配置区域
BACKUP_BASE_DIR = '/Users/a000/拜访脚本备份'
PHARMACY_DIR = os.path.join(BACKUP_BASE_DIR, '药店')
HOSPITAL_DIR = os.path.join(BACKUP_BASE_DIR, '医院')

# 药店相关脚本文件列表
PHARMACY_FILES = [
    '/Users/a000/药店规划/找区域.py',
    '/Users/a000/药店规划/遵义附近药店搜索.py',
    '/Users/a000/药店规划/区域划分.py',
    '/Users/a000/药店规划/路径规划贪心算法.py',
    '/Users/a000/药店规划/拜访时间.py',
    '/Users/a000/药店拜访/process_pharmacy_data_v2.py',
    '/Users/a000/药店拜访/rename_pharmacy_files.py',
    '/Users/a000/拜访规划/tupiandama250623药店.py',
    '/Users/a000/药店拜访/pharmacy_visit_planner_enhanced.py'
]

# 医院相关脚本文件列表
HOSPITAL_FILES = [
    '/Users/a000/拜访规划/haodf_hospital_scraper.py',
    '/Users/a000/拜访规划/guizhou_hospital_doctor_scraper.py',
    '/Users/a000/拜访测试/improved_visit_planner_unified.py',
    '/Users/a000/拜访测试/improved_visit_planner_unified_day.py',
    '/Users/a000/拜访测试/improved_visit_planner.py',
    '/Users/a000/图片处理/医院拜访照片抽取工具.py',
    '/Users/a000/图片处理/图片椭圆变形工具.py',
    '/Users/a000/图片处理/图片视角随机变形工具.py',
    '/Users/a000/图片处理/照片相似度比对工具-支持单文件.py',
    '/Users/a000/图片处理/照片相似度比对工具.py',
    '/Users/a000/图片处理/照片重命名工具.py',
    '/Users/a000/图片处理/拜访编号处理脚本.py',
    '/Users/a000/图片处理/生成拜访数据脚本.py',
    '/Users/a000/拜访规划/tupiandama250623.py',
    '/Users/a000/图片处理/照片尺寸调整工具.py',
    '/Users/a000/图片处理/照片压缩工具.py'
]

def create_backup_directories():
    """创建备份目录"""
    os.makedirs(PHARMACY_DIR, exist_ok=True)
    os.makedirs(HOSPITAL_DIR, exist_ok=True)
    print(f"已创建备份目录：")
    print(f"  药店目录: {PHARMACY_DIR}")
    print(f"  医院目录: {HOSPITAL_DIR}")

def copy_files(file_list, target_dir, category_name):
    """复制文件到目标目录"""
    print(f"\n开始复制{category_name}相关文件...")
    success_count = 0
    failed_files = []
    
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                shutil.copy2(file_path, target_dir)
                filename = os.path.basename(file_path)
                print(f"  ✓ 已复制: {filename}")
                success_count += 1
            else:
                print(f"  ✗ 文件不存在: {file_path}")
                failed_files.append(file_path)
        except Exception as e:
            print(f"  ✗ 复制失败: {file_path} - {str(e)}")
            failed_files.append(file_path)
    
    print(f"\n{category_name}文件复制完成: 成功 {success_count} 个，失败 {len(failed_files)} 个")
    if failed_files:
        print("失败的文件:")
        for file_path in failed_files:
            print(f"  - {file_path}")
    
    return success_count, failed_files

def list_backup_contents():
    """列出备份目录内容"""
    print("\n=== 备份目录内容 ===")
    
    for dir_name, dir_path in [("药店", PHARMACY_DIR), ("医院", HOSPITAL_DIR)]:
        print(f"\n{dir_name}文件夹 ({dir_path}):")
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            if files:
                for i, file in enumerate(sorted(files), 1):
                    if file.endswith('.py'):
                        print(f"  {i:2d}. {file}")
            else:
                print("  (空文件夹)")
        else:
            print("  (目录不存在)")

def copy_backup_script():
    """复制备份脚本本身到备份目录根目录"""
    script_path = '/Users/a000/拜访脚本备份/脚本文件备份工具.py'
    target_path = os.path.join(BACKUP_BASE_DIR, '脚本文件备份工具.py')
    
    try:
        if os.path.exists(script_path):
            shutil.copy2(script_path, target_path)
            print(f"\n✓ 已复制备份脚本到: {target_path}")
            return True
        else:
            print(f"\n✗ 备份脚本不存在: {script_path}")
            return False
    except Exception as e:
        print(f"\n✗ 复制备份脚本失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("=== 脚本文件备份工具 ===")
    print(f"备份目标目录: {BACKUP_BASE_DIR}")
    
    # 创建备份目录
    create_backup_directories()
    
    # 复制药店相关文件
    pharmacy_success, pharmacy_failed = copy_files(PHARMACY_FILES, PHARMACY_DIR, "药店")
    
    # 复制医院相关文件
    hospital_success, hospital_failed = copy_files(HOSPITAL_FILES, HOSPITAL_DIR, "医院")
    
    # 复制备份脚本本身
    script_copied = copy_backup_script()
    
    # 显示备份结果
    print("\n=== 备份完成 ===")
    print(f"总计复制成功: {pharmacy_success + hospital_success} 个文件")
    print(f"总计复制失败: {len(pharmacy_failed) + len(hospital_failed)} 个文件")
    if script_copied:
        print("备份脚本已复制到备份目录根目录")
    
    # 列出备份目录内容
    list_backup_contents()
    
    print("\n备份操作完成！")

if __name__ == "__main__":
    main()