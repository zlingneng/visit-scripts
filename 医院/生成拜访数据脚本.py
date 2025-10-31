import pandas as pd
import random
import os
from datetime import datetime

def generate_visit_data():
    """
    根据贵州医生拜访2502-zdf.xlsx的拜访计划数据，生成新的Excel文件
    """
    
    # 读取主要数据源文件
    source_file = '/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/贵州医生拜访2510-何勇-蔡林川-周星贤.xlsx'
    
    try:
        # 读取源数据 - 拜访计划工作表
        df_source = pd.read_excel(source_file, sheet_name='拜访计划')
        print(f"源数据行数: {len(df_source)}")
        print(f"源数据列名: {list(df_source.columns)}")
        
        # 使用固定的预设值
        content_column_data = [
            '传递产品信息-了解并支持',
            '介绍产品疗效-客户认可产品疗效',
            '传递产品信息-客户认可产品疗效',
            '推广产品-客户认可产品',
            '功效推广-客户认可功效'
        ]
        print(f"预设数据数量: {len(content_column_data)}")
        print(f"预设数据: {content_column_data}")
        
        # 创建新的数据框
        new_data = []
        
        for index, row in df_source.iterrows():
            # 保留所有行，包括拜访编号为空的数据
            # 从预设值中随机选择一个值
            random_value = random.choice(content_column_data)
            
            # 分割拜访目的及效果和客户反馈
            if '-' in str(random_value):
                parts = str(random_value).split('-', 1)
                visit_purpose = parts[0].strip()
                customer_feedback = parts[1].strip()
            else:
                visit_purpose = str(random_value)
                customer_feedback = ''
            
            # 处理日期格式转换
            visit_date = ''
            if pd.notna(row.get('日期', '')):
                try:
                    # 尝试解析日期
                    if isinstance(row['日期'], str):
                        # 如果是字符串，尝试解析
                        date_obj = pd.to_datetime(row['日期'])
                    else:
                        # 如果已经是日期对象
                        date_obj = row['日期']
                    visit_date = date_obj.strftime('%Y/%m/%d')
                except:
                    visit_date = str(row.get('日期', ''))
            
            # 处理医生名称，改为 姓+医生
            doctor_name = ''
            if pd.notna(row.get('医生名称', '')):
                original_name = str(row['医生名称']).strip()
                if original_name:
                    # 取第一个字作为姓
                    surname = original_name[0]
                    doctor_name = f"{surname}医生"
            
            # 处理拜访时间，只有拜访编号非空时才保留拜访时间
            visit_time = ''
            if pd.notna(row.get('拜访编号', '')) and str(row.get('拜访编号', '')).strip() != '':
                visit_time = row.get('拜访开始时间', '')
            
            # 构建新行数据
            new_row = {
                '拜访编号': row.get('拜访编号', ''),
                '终端名称': row.get('医院名称', ''),
                '医院/商业/药店': '医院',
                '终端等级（三级/二级/一级/其他）': '三级',
                '地址': row.get('地址', ''),
                '拜访日期（yyyy.mm.dd）': visit_date,
                '拜访时间': visit_time,
                '拜访科室/部门': row.get('科室', ''),
                '拜访对象': doctor_name,
                '拜访人员': row.get('拜访人', ''),
                '拜访目的及效果': visit_purpose,
                '客户反馈': customer_feedback
            }
            
            new_data.append(new_row)
        
        # 创建新的DataFrame
        df_new = pd.DataFrame(new_data)
        
        # 输出文件路径 - 在输入文件同文件夹中，原文件名加上'-整理'后缀
        input_dir = os.path.dirname(source_file)
        input_filename = os.path.basename(source_file)
        name_without_ext = os.path.splitext(input_filename)[0]
        output_filename = f"{name_without_ext}-整理.xlsx"
        output_file = os.path.join(input_dir, output_filename)
        
        # 保存到Excel文件
        df_new.to_excel(output_file, index=False, sheet_name='拜访数据')
        
        print(f"\n数据处理完成！")
        print(f"生成的数据行数: {len(df_new)}")
        print(f"输出文件: {output_file}")
        print(f"\n前5行数据预览:")
        print(df_new.head())
        
        return output_file
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = generate_visit_data()
    if result:
        print(f"\n✅ 成功生成文件: {result}")
    else:
        print("\n❌ 文件生成失败")