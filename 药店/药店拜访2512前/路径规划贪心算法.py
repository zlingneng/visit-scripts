#贪心算法
import pandas as pd
import numpy as np


def calculate_distance(point1, point2):
    """
    计算两点之间的欧式距离（这里简单以欧式距离来近似表示经纬度对应的实际距离）
    """
    return np.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)


def greedy_route_planning(df):
    """
    使用贪心算法规划拜访路线，返回带有拜访顺序的DataFrame
    """
    unvisited_indices = set(df.index)
    start_index = next(iter(unvisited_indices))  # 选择第一个点作为起始点
    route_order = [start_index]
    unvisited_indices.remove(start_index)
    current_index = start_index
    order = 1
    df['order'] = np.nan  # 新增拜访顺序列，初始化为空值
    df.loc[start_index, 'order'] = order
    order += 1
    while unvisited_indices:
        min_distance = float('inf')
        next_index = None
        current_point = df.loc[current_index, ['纬度', '经度']].values
        for index in unvisited_indices:
            target_point = df.loc[index, ['纬度', '经度']].values
            distance = calculate_distance(current_point, target_point)
            if distance < min_distance:
                min_distance = distance
                next_index = index
        route_order.append(next_index)
        unvisited_indices.remove(next_index)
        current_index = next_index
        df.loc[current_index, 'order'] = order
        order += 1
    return df.sort_index()


# 读取输入的Excel文件
input_file_path = r'C:\Users\zm\Documents\jisheng\拜访\药店 六盘水 遵义 安顺等\遵义\遵义区域划分.xlsx'
data = pd.read_excel(input_file_path, sheet_name='遵义区域划分')


# input_file_path = 'your_input_file.xlsx'  # 替换为你的输入文件路径
# data = pd.read_excel(input_file_path)

# 按照你的要求，假设存在某个字段用于区分不同的集合，这里假设字段名为 'group'
groups = data['区域'].unique()
result_dfs = []
for group in groups:
    group_data = data[data['区域'] == group].copy()
    result_df = greedy_route_planning(group_data)
    result_dfs.append(result_df)

# 合并各个集合的结果DataFrame
final_result = pd.concat(result_dfs)

# 输出结果到新的Excel文件
output_file_path = r'C:\Users\zm\Documents\jisheng\拜访\药店 六盘水 遵义 安顺等\遵义\遵义区域内规划-全.xlsx'  # 替换为你想要的输出文件路径
final_result.to_excel(output_file_path, index=False)