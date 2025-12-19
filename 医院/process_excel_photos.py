#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理Excel数据并复制改名照片文件
1. 在Excel中新增"新列a"，对拜访编号有值的行从1开始顺序编号
2. 将照片编号对应的照片复制到新文件夹，文件名改为新列a的值
"""

import pandas as pd
import os
import shutil

# ==================== 配置区域 ====================
# Excel文件路径
EXCEL_FILE = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访251201-20张令能余荷英/贵州医生拜访251201-20张令能余荷英/贵州医生拜访251201-20张令能余荷英.xlsx"
# Sheet名称
SHEET_NAME = "Sheet1"
# 根据输入文件路径自动推导其他路径
base_dir = os.path.dirname(EXCEL_FILE)
file_prefix = os.path.splitext(os.path.basename(EXCEL_FILE))[0]

# 照片文件夹路径
PHOTO_FOLDER = os.path.join(base_dir, "照片")
# 新照片文件夹路径
NEW_PHOTO_FOLDER = os.path.join(base_dir, "照片4")
# 输出Excel文件路径
OUTPUT_EXCEL = os.path.join(base_dir, f"{file_prefix}_处理后.xlsx")
# =================================================

def main():
    print("=" * 60)
    print("开始处理...")
    print("=" * 60)
    
    # 1. 读取Excel数据
    print("\n1. 读取Excel数据...")
    df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)
    print(f"   读取成功，共 {len(df)} 行")
    
    # 2. 新增"新列a"
    print("\n2. 新增'新列a'列...")
    # 初始化新列a为空
    df['新列a'] = None
    
    # 对拜访编号有值的行，从1开始顺序编号
    counter = 1
    for idx in df.index:
        if pd.notna(df.loc[idx, '拜访编号']):
            df.loc[idx, '新列a'] = counter
            counter += 1
    
    print(f"   共标记了 {counter - 1} 行")
    
    # 3. 创建新照片文件夹
    print("\n3. 创建新照片文件夹...")
    if not os.path.exists(NEW_PHOTO_FOLDER):
        os.makedirs(NEW_PHOTO_FOLDER)
        print(f"   创建文件夹: {NEW_PHOTO_FOLDER}")
    else:
        print(f"   文件夹已存在: {NEW_PHOTO_FOLDER}")
    
    # 4. 获取照片文件夹中的所有文件
    print("\n4. 扫描照片文件夹...")
    photo_files = {}
    for f in os.listdir(PHOTO_FOLDER):
        # 获取不带扩展名的文件名
        name_without_ext = os.path.splitext(f)[0]
        ext = os.path.splitext(f)[1]
        photo_files[name_without_ext] = (f, ext)
    print(f"   共找到 {len(photo_files)} 个文件")
    
    # 5. 复制并改名照片
    print("\n5. 复制并改名照片...")
    success_count = 0
    fail_count = 0
    fail_list = []
    
    for idx in df.index:
        new_a = df.loc[idx, '新列a']
        if pd.notna(new_a):
            photo_id = df.loc[idx, '照片编号']
            if pd.notna(photo_id):
                # 照片编号作为文件名查找
                photo_id_str = str(photo_id).strip()
                
                if photo_id_str in photo_files:
                    orig_filename, ext = photo_files[photo_id_str]
                    orig_path = os.path.join(PHOTO_FOLDER, orig_filename)
                    new_filename = f"{int(new_a)}{ext}"
                    new_path = os.path.join(NEW_PHOTO_FOLDER, new_filename)
                    
                    try:
                        shutil.copy2(orig_path, new_path)
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        fail_list.append((photo_id_str, str(e)))
                else:
                    fail_count += 1
                    fail_list.append((photo_id_str, "文件不存在"))
    
    print(f"   成功复制: {success_count} 个")
    print(f"   失败: {fail_count} 个")
    
    if fail_list and len(fail_list) <= 20:
        print("\n   失败详情:")
        for photo_id, reason in fail_list:
            print(f"     - 照片编号 '{photo_id}': {reason}")
    elif fail_list:
        print(f"\n   失败详情(显示前20条):")
        for photo_id, reason in fail_list[:20]:
            print(f"     - 照片编号 '{photo_id}': {reason}")
        print(f"     ... 还有 {len(fail_list) - 20} 条")
    
    # 6. 保存Excel
    print("\n6. 保存Excel文件...")
    df.to_excel(OUTPUT_EXCEL, index=False, sheet_name=SHEET_NAME)
    print(f"   保存到: {OUTPUT_EXCEL}")
    
    # 7. 显示结果预览
    print("\n7. 结果预览(前20行有值的记录):")
    preview = df[df['新列a'].notna()][['拜访编号', '终端名称', '照片编号', '新列a']].head(20)
    print(preview.to_string())
    
    print("\n" + "=" * 60)
    print("处理完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
