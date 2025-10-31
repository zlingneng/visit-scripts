import pandas as pd
import numpy as np

# 配置参数
input_file_path = r'/Users/a000/药店规划/遵义药店区域划分结果_20250807_2210.xlsx'
input_sheet_name = '区域划分结果'
output_file_path = r'/Users/a000/药店规划/遵义拜访时间.xlsx'
output_sheet_name = '拜访时间安排'

# 读取Excel文件
print("正在读取数据...")
df = pd.read_excel(input_file_path, sheet_name=input_sheet_name)
print(f"读取到 {len(df)} 条记录，{len(df['区域编号'].unique())} 个区域")

# 创建拜访时间列
df['拜访时间'] = pd.NaT

updated_group_dfs = []

# 按照区域进行分组
groups = df.groupby('区域编号')

print("正在计算拜访时间...")
# 遍历每个区域分组
for region, group_data in groups:
    # 复制数据避免修改原始数据
    group_data = group_data.copy()
    
    # 按区域内顺序排序
    group_data = group_data.sort_values('区域内顺序').reset_index(drop=True)
    
    # 随机生成每个区域的开始时间（9:00-9:15之间）
    start_time_minutes = np.random.randint(0, 16)
    start_time = pd.to_datetime('2024-01-01 09:00:00') + pd.Timedelta(minutes=start_time_minutes)
    
    # 设置第一个地点的拜访时间
    group_data.loc[0, '拜访时间'] = start_time

    
    # 循环遍历计算该区域内除第一个地点外其他地点的拜访时间
    for i in range(1, len(group_data)):
        prev_visit_time = group_data.loc[i - 1, '拜访时间']
        
        # 随机生成13到18分钟的基础停留时间（单位换算成小时）
        base_stay_time_minutes = np.random.randint(13, 19)
        base_stay_time = pd.Timedelta(minutes=base_stay_time_minutes) / pd.Timedelta(hours=1)

        # 随机生成步行速度，单位是米/分钟，范围是40到70米/分钟
        walking_speed = np.random.randint(40, 71)
        
        # 获取距离数据（单位米），并计算根据距离和步行速度得到的移动时间（单位换算成小时）
        distance = group_data.loc[i-1, '距离 米']
        if pd.isna(distance):
            distance = 0  # 如果距离为空，设为0
        distance_based_stay_time = (distance / walking_speed) / 60
        
        # 总的停留时间（单位为小时）
        prev_stay_time = base_stay_time + distance_based_stay_time

        # 判断是否需要增加1小时的午餐时间
        noon_time = pd.to_datetime('2024-01-01 12:00:00')
        if prev_visit_time < noon_time and (prev_visit_time + pd.Timedelta(hours=prev_stay_time)) > noon_time:
            prev_stay_time += 1
            
        group_data.loc[i, '拜访时间'] = prev_visit_time + pd.Timedelta(hours=prev_stay_time)
    
    updated_group_dfs.append(group_data)

# 将所有更新后的区域数据合并到一个DataFrame中
print("正在合并数据...")
combined_df = pd.concat(updated_group_dfs, ignore_index=True)

# 按区域编号和区域内顺序排序
combined_df = combined_df.sort_values(['区域编号', '区域内顺序']).reset_index(drop=True)

# 保存到Excel文件
print(f"正在保存到 {output_file_path}...")
with pd.ExcelWriter(output_file_path, engine='openpyxl') as writer:
    # 保存原始数据到第一个sheet
    df_original = pd.read_excel(input_file_path, sheet_name=input_sheet_name)
    df_original.to_excel(writer, sheet_name='原始数据', index=False)
    
    # 保存带拜访时间的数据到第二个sheet
    combined_df.to_excel(writer, sheet_name=output_sheet_name, index=False)

print(f"\n处理完成！")
print(f"- 总共处理了 {len(combined_df)} 条记录")
print(f"- 涉及 {len(combined_df['区域编号'].unique())} 个区域")
print(f"- 结果已保存到: {output_file_path}")
print(f"- 包含两个sheet页: '原始数据' 和 '{output_sheet_name}'")

