import pandas as pd
import os
import shutil
from pathlib import Path

def process_files_and_excel():
    """
    处理文件重命名任务：
    1. 读取Excel文件中的拜访计划
    2. 根据拜访编号匹配文件名
    3. 生成新编号并更新Excel
    4. 重命名文件并复制到新目录
    """
    
    # 文件路径配置
    source_dir = "/Users/a000/Documents/济生/医院拜访25/2503/张丹凤2503/贵州医生拜访2503-张丹凤2/照片3的副本"
    target_dir = "/Users/a000/Documents/济生/医院拜访25/2503/张丹凤2503/贵州医生拜访2503-张丹凤2/未命名文件夹"
    excel_path = "/Users/a000/Documents/济生/医院拜访25/2503/张丹凤2503/贵州医生拜访2503-张丹凤2/贵州医生拜访2503-张丹凤-送审2.xlsx"
    
    try:
        # 创建目标目录
        os.makedirs(target_dir, exist_ok=True)
        print(f"目标目录已创建: {target_dir}")
        
        # 读取Excel文件
        print("正在读取Excel文件...")
        df = pd.read_excel(excel_path, sheet_name='拜访数据')
        print(f"Excel文件读取成功，共{len(df)}行数据")
        print("Excel列名:", df.columns.tolist())
        
        # 检查必要的列是否存在
        if '拜访编号' not in df.columns:
            print("错误：Excel文件中未找到'拜访编号'列")
            return
        
        # 添加新编号列（如果不存在）
        if '新编号' not in df.columns:
            df['新编号'] = None
        
        # 确保新编号列为object类型，可以存储字符串和数字
        df['新编号'] = df['新编号'].astype('object')
        
        # 获取源目录中的所有文件
        print("正在扫描源目录文件...")
        if not os.path.exists(source_dir):
            print(f"错误：源目录不存在 {source_dir}")
            return
            
        source_files = [f for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]
        print(f"源目录中找到{len(source_files)}个文件")
        
        # 创建文件名到拜访编号的映射
        file_mapping = {}
        for file in source_files:
            filename_without_ext = os.path.splitext(file)[0]
            file_mapping[filename_without_ext] = file
        
        print("文件名列表（不含扩展名）:", list(file_mapping.keys()))
        
        # 生成新编号
        new_number = 1
        matched_files = []
        
        for index, row in df.iterrows():
            visit_number_raw = row['拜访编号']
            
            # 处理拜访编号，将浮点数转换为整数字符串
            if pd.notna(visit_number_raw) and visit_number_raw != '':
                try:
                    # 如果是浮点数，转换为整数再转为字符串
                    if isinstance(visit_number_raw, float):
                        visit_number = str(int(visit_number_raw))
                    else:
                        visit_number = str(visit_number_raw).strip()
                except (ValueError, TypeError):
                    visit_number = ''
            else:
                visit_number = ''
            
            if visit_number and visit_number != 'nan':
                # 拜访编号有值，分配新编号
                df.loc[index, '新编号'] = new_number
                
                # 查找对应的文件
                if visit_number in file_mapping:
                    matched_files.append({
                        'original_file': file_mapping[visit_number],
                        'new_number': new_number,
                        'visit_number': visit_number
                    })
                    print(f"匹配成功: 拜访编号{visit_number} -> 新编号{new_number} -> 文件{file_mapping[visit_number]}")
                else:
                    print(f"警告: 拜访编号{visit_number}未找到对应文件")
                
                new_number += 1
            else:
                # 拜访编号为空，新编号也为空
                df.loc[index, '新编号'] = None
        
        # 保存更新后的Excel文件
        print("正在保存更新后的Excel文件...")
        df.to_excel(excel_path, sheet_name='拜访计划', index=False)
        print("Excel文件已更新")
        
        # 复制并重命名文件
        print("正在复制和重命名文件...")
        for file_info in matched_files:
            original_path = os.path.join(source_dir, file_info['original_file'])
            file_ext = os.path.splitext(file_info['original_file'])[1]
            new_filename = f"{file_info['new_number']}{file_ext}"
            new_path = os.path.join(target_dir, new_filename)
            
            try:
                shutil.copy2(original_path, new_path)
                print(f"文件已复制: {file_info['original_file']} -> {new_filename}")
            except Exception as e:
                print(f"复制文件失败: {file_info['original_file']} -> {new_filename}, 错误: {e}")
        
        print(f"\n任务完成！")
        print(f"- 处理了{len(matched_files)}个文件")
        print(f"- 文件已保存到: {target_dir}")
        print(f"- Excel文件已更新: {excel_path}")
        
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    process_files_and_excel()