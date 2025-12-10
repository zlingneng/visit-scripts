import pandas as pd
import os
from collections import defaultdict

# ==================== 配置部分 ====================
# Excel文件路径
EXCEL_FILE = '/Users/a000/Documents/济生/医院拜访25/2510/张丹凤2510/贵州医生拜访2510-张丹凤-胡乐凤.xlsx'

# 目标文件夹路径
TARGET_DIR = '/Users/a000/Documents/济生/医院拜访25/2510/张丹凤2510/科室照片'

# ==================== 脚本主体 ====================

def create_hospital_department_folders():
    # 读取Excel文件
    df = pd.read_excel(EXCEL_FILE)
    
    # 创建医院到科室的映射
    hospital_departments = defaultdict(set)
    
    # 遍历数据，建立医院和科室的映射关系
    for index, row in df.iterrows():
        hospital_name = row['医院名称']
        department_name = row['科室']
        
        # 只有当医院名称和科室名称都存在时才添加
        if pd.notna(hospital_name) and pd.notna(department_name):
            hospital_departments[hospital_name].add(department_name)
    
    # 创建目标目录（如果不存在）
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 创建文件夹结构
    for hospital, departments in hospital_departments.items():
        # 清理医院名称中的特殊字符，避免文件夹命名问题
        clean_hospital_name = "".join(c for c in hospital if c.isalnum() or c in "()-_ ")
        hospital_dir = os.path.join(TARGET_DIR, clean_hospital_name.strip())
        
        # 创建医院文件夹
        os.makedirs(hospital_dir, exist_ok=True)
        print(f"创建医院文件夹: {hospital_dir}")
        
        # 为该医院创建科室子文件夹
        for department in departments:
            if pd.notna(department):  # 确保科室名称不为空
                # 清理科室名称中的特殊字符
                clean_department_name = "".join(c for c in department if c.isalnum() or c in "()-_ ")
                department_dir = os.path.join(hospital_dir, clean_department_name.strip())
                
                # 创建科室文件夹
                os.makedirs(department_dir, exist_ok=True)
                print(f"  创建科室文件夹: {department_dir}")
    
    print(f"\n文件夹创建完成！总共处理了 {len(hospital_departments)} 家医院。")

if __name__ == "__main__":
    create_hospital_department_folders()