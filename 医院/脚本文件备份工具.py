#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本文件备份工具
自动将指定的脚本文件复制到备份目录中，按照药店和医院分类整理
"""

import os
import shutil
import re
from pathlib import Path

# 配置区域
BACKUP_BASE_DIR = '/Users/a000/拜访脚本备份'
PHARMACY_DIR = os.path.join(BACKUP_BASE_DIR, '药店')
HOSPITAL_DIR = os.path.join(BACKUP_BASE_DIR, '医院')



def extract_file_paths_from_comments(script_content, section_marker):
    """
    从脚本注释中提取文件路径列表
    
    Args:
        script_content (str): 脚本文件内容
        section_marker (str): 区域标记名称 (如 "PHARMACY_FILES")
    
    Returns:
        list or None: 提取到的文件路径列表，如果未找到则返回None
    """
    # 构造开始和结束标记
    start_marker = f"# {{{section_marker}_START}}"
    end_marker = f"# {{{section_marker}_END}}"
    
    # 查找开始和结束位置
    start_pos = script_content.find(start_marker)
    if start_pos == -1:
        return None
    
    end_pos = script_content.find(end_marker, start_pos + len(start_marker))
    if end_pos == -1:
        return None
    
    # 提取标记之间的内容
    section_content = script_content[start_pos + len(start_marker):end_pos]
    
    # 使用正则表达式提取所有文件路径
    # 匹配带引号的文件路径或不带引号但带注释符号的文件路径
    # 先尝试匹配带引号的路径
    quoted_pattern = r"['\"]([^'\"]+\.(py|txt|csv|json))['\"]"
    quoted_paths = re.findall(quoted_pattern, section_content)
    quoted_paths = [path[0] for path in quoted_paths]
    
    # 再匹配不带引号但带注释符号的路径（以#开头，后面跟着空格和文件路径）
    unquoted_pattern = r"#\s*(/[^\s]*\.(py|txt|csv|json))"
    unquoted_paths = re.findall(unquoted_pattern, section_content)
    unquoted_paths = [path[0] for path in unquoted_paths]
    
    # 合并两种路径
    file_paths = quoted_paths + unquoted_paths
    
    return file_paths if file_paths else None

def load_file_paths_from_txt(file_path):
    """
    从文本文件中加载文件路径列表
    支持解析多种路径格式：
    1. 普通路径: /path/to/file.py
    2. 带注释的路径: /path/to/file.py 这是注释
    3. 带引号的路径: "/path/to/file.py" 或 '/path/to/file.py'
    4. 带引号和注释的路径: "/path/to/file.py" 这是注释
    
    Args:
        file_path (str): 文本文件路径
        
    Returns:
        list: 文件路径列表
    """
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            paths = []
            for line in f.readlines():
                line = line.strip()
                # 跳过空行
                if not line:
                    continue
                
                # 使用正则表达式解析带引号的路径
                # 匹配以单引号或双引号开头的路径
                quoted_pattern = r'^[\'\"](/[^\'\"]+\.(py|txt|csv|json))[\'\"]'
                quoted_match = re.match(quoted_pattern, line)
                
                if quoted_match:
                    # 提取引号内的路径
                    path = quoted_match.group(1)
                    paths.append(path)
                else:
                    # 处理不带引号的路径（保持原有逻辑）
                    # 提取路径部分（第一个空格前的部分）
                    # 支持带注释的路径格式: /path/to/file.py 注释内容
                    path_parts = line.split(' ', 1)
                    if path_parts:
                        path = path_parts[0].strip()
                        # 验证是否为有效的文件路径（以/开头且包含有效扩展名）
                        if path.startswith('/') and any(path.endswith(ext) for ext in ['.py', '.txt', '.csv', '.json']):
                            paths.append(path)
            return paths
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return []

def load_file_lists():
    """从文本文件加载文件列表"""
    # 优先从文本文件加载路径
    pharmacy_txt_path = os.path.join(BACKUP_BASE_DIR, '药店文件路径.txt')
    hospital_txt_path = os.path.join(BACKUP_BASE_DIR, '医院文件路径.txt')
    
    pharmacy_files = load_file_paths_from_txt(pharmacy_txt_path)
    hospital_files = load_file_paths_from_txt(hospital_txt_path)
    
    # 如果文本文件没有路径，则尝试从脚本注释区域提取文件路径
    if not pharmacy_files or not hospital_files:
        # 读取当前脚本文件内容
        script_path = __file__
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # 尝试从注释区域提取文件列表
        pharmacy_files_from_comments = extract_file_paths_from_comments(script_content, "PHARMACY_FILES")
        hospital_files_from_comments = extract_file_paths_from_comments(script_content, "HOSPITAL_FILES")
        
        # 如果从注释区域提取到了路径，则使用这些路径
        if pharmacy_files_from_comments:
            pharmacy_files = pharmacy_files_from_comments
        
        if hospital_files_from_comments:
            hospital_files = hospital_files_from_comments
    
    # 如果仍然没有路径，则使用默认列表
    if not pharmacy_files:
        pharmacy_files = [
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
    
    if not hospital_files:
        hospital_files = [
            '/Users/a000/拜访规划/tupiandama250627-科室.py',
            '/Users/a000/拜访规划/tupiandama250627-大门.py',
            '/Users/a000/拜访规划/haodf_hospital_scraper.py',
            '/Users/a000/拜访规划/guizhou_hospital_dept_scraper.py',
            '/Users/a000/拜访规划/guizhou_hospital_doctor_scraper.py',
            '/Users/a000/拜访测试/improved_visit_planner_unified.py',
            '/Users/a000/拜访测试/improved_visit_planner_unified_day.py',
            '/Users/a000/图片处理/医院拜访照片抽取工具.py',
            '/Users/a000/图片处理/图片视角随机变形工具.py',
            '/Users/a000/图片处理/照片相似度比对工具-支持单文件.py',
            '/Users/a000/图片处理/照片相似度比对工具.py',
            '/Users/a000/图片处理/照片重命名工具.py',
            '/Users/a000/图片处理/创建医院科室文件夹.py',
            '/Users/a000/图片处理/department_photo_extractor.py',
            '/Users/a000/图片处理/科室照片重命名工具.py',
            '/Users/a000/图片处理/拜访编号处理脚本_安全版.py',
            '/Users/a000/图片处理/生成拜访数据脚本.py',
            '/Users/a000/拜访规划/tupiandama250623.py',
            '/Users/a000/图片处理/照片尺寸调整工具.py',
            '/Users/a000/图片处理/照片压缩工具.py'
        ]
    
    return pharmacy_files, hospital_files

# 从注释区域加载文件列表
PHARMACY_FILES, HOSPITAL_FILES = load_file_lists()

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