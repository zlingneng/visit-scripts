import pandas as pd
import os
from pathlib import Path
import re
import shutil

def process_visit_numbers():
    """
    处理拜访编号：
    1. 读取Excel文件中的拜访计划表
    2. 获取图片文件夹中的文件名
    3. 建立文件名与原拜访编号的对应关系
    4. 按数值排序文件名并重新编号
    5. 在Excel中添加拜访编号列
    """
    
    # 文件路径
    excel_path = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-遵义安顺/贵州医生拜访2512-遵义安顺.xlsx"
    image_folder = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-遵义安顺/照片"
    new_image_folder = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-遵义安顺/照片2"
    
    try:
        # 读取Excel文件的拜访计划表 - 使用xlrd引擎
        print("正在读取Excel文件...")
        try:
            df = pd.read_excel(excel_path, sheet_name='拜访计划', engine='openpyxl')
        except Exception as e:
            print(f"使用openpyxl引擎读取失败，尝试使用默认引擎: {str(e)}")
            df = pd.read_excel(excel_path, sheet_name='拜访计划')
        
        print(f"读取到 {len(df)} 行数据")
        print("表格列名：", df.columns.tolist())
        
        # 显示前几行数据以便确认结构
        print("\n前5行数据：")
        print(df.head())
        
        # 获取图片文件夹中的文件
        print(f"\n正在扫描图片文件夹: {image_folder}")
        if not os.path.exists(image_folder):
            print(f"错误：文件夹 {image_folder} 不存在")
            return
            
        # 获取所有文件（不包括文件夹）
        files = []
        for file in os.listdir(image_folder):
            file_path = os.path.join(image_folder, file)
            if os.path.isfile(file_path):
                # 获取不带后缀的文件名
                filename_without_ext = os.path.splitext(file)[0]
                files.append(filename_without_ext)
        
        print(f"找到 {len(files)} 个文件")
        print("文件名（不含后缀）：", files)
        
        # 将现有的拜访编号作为原拜访编号处理
        print("\n将现有拜访编号作为原拜访编号...")
        df['原拜访编号'] = df['原序号'].copy()
        
        # 建立文件名与原拜访编号的对应关系
        print("\n建立对应关系...")
        file_to_original = {}
        original_visit_numbers = df['原拜访编号'].dropna().astype(str).tolist()
        
        print("原拜访编号：", original_visit_numbers)
        
        # 尝试匹配文件名和原拜访编号
        for file_name in files:
            for original_num in original_visit_numbers:
                if str(file_name) == str(original_num):
                    file_to_original[file_name] = original_num
                    break
        
        print("匹配到的对应关系：", file_to_original)
        
        # 按数值排序文件名
        def extract_number(filename):
            """从文件名中提取数字用于排序"""
            numbers = re.findall(r'\d+', str(filename))
            return int(numbers[0]) if numbers else 0
        
        # 只对匹配到的文件进行排序
        matched_files = list(file_to_original.keys())
        sorted_files = sorted(matched_files, key=extract_number)
        
        print("排序后的文件名：", sorted_files)
        
        # 创建新编号映射（从1开始）
        new_number_mapping = {}
        for i, file_name in enumerate(sorted_files, 1):
            original_num = file_to_original[file_name]
            new_number_mapping[original_num] = i
        
        print("新编号映射：", new_number_mapping)
        
        # 更新拜访编号列
        df['拜访编号'] = df['原拜访编号'].astype(str).map(new_number_mapping)
        
        # 显示结果
        print("\n处理结果：")
        result_columns = ['原拜访编号', '拜访编号'] + [col for col in df.columns if col not in ['原拜访编号', '拜访编号']]
        print(df[result_columns].head(10))
        
        # 保存修改后的Excel文件 - 使用更安全的方式
        print("\n正在保存文件...")
        # 创建备份文件
        backup_path = excel_path.replace('.xlsx', '_backup.xlsx')
        shutil.copy2(excel_path, backup_path)
        print(f"已创建备份文件: {backup_path}")
        
        # 将数据保存为新的Excel文件
        output_path = excel_path.replace('.xlsx', '_updated.xlsx')
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='拜访计划', index=False)
        
        print(f"处理完成！已将更新后的数据保存到: {output_path}")
        print("注意：原始Excel文件保持不变，因为可能存在格式问题导致无法直接修改")
        
        # 复制文件到新文件夹并重命名
        print(f"\n正在复制文件到新文件夹: {new_image_folder}")
        
        # 创建新文件夹（如果不存在）
        os.makedirs(new_image_folder, exist_ok=True)
        
        # 获取原始文件的完整路径和扩展名
        original_files_info = {}
        for file in os.listdir(image_folder):
            file_path = os.path.join(image_folder, file)
            if os.path.isfile(file_path):
                filename_without_ext = os.path.splitext(file)[0]
                file_ext = os.path.splitext(file)[1]
                original_files_info[filename_without_ext] = {
                    'full_path': file_path,
                    'extension': file_ext
                }
        
        # 复制并重命名文件
        copied_files = 0
        for original_num, new_num in new_number_mapping.items():
            if str(original_num) in original_files_info:
                source_file = original_files_info[str(original_num)]['full_path']
                file_ext = original_files_info[str(original_num)]['extension']
                new_filename = f"{new_num}{file_ext}"
                destination_file = os.path.join(new_image_folder, new_filename)
                
                try:
                    shutil.copy2(source_file, destination_file)
                    print(f"复制: {os.path.basename(source_file)} -> {new_filename}")
                    copied_files += 1
                except Exception as e:
                    print(f"复制文件失败 {source_file}: {str(e)}")
        
        print(f"\n文件复制完成！共复制了 {copied_files} 个文件")
        
        # 统计信息
        total_rows = len(df)
        assigned_rows = df['拜访编号'].notna().sum()
        print(f"\n统计信息：")
        print(f"总行数: {total_rows}")
        print(f"已分配拜访编号的行数: {assigned_rows}")
        print(f"未分配拜访编号的行数: {total_rows - assigned_rows}")
        print(f"复制到新文件夹的文件数: {copied_files}")
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    process_visit_numbers()