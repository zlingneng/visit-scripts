import numpy as np
import pandas as pd
import collections
from sklearn.neighbors import KDTree
from datetime import datetime

# 将threshold定义为全局变量，你需要根据实际情况调整其具体值
threshold = 0.01
# 用于缓存距离计算结果的字典，键为元组形式的点对索引，值为距离
distance_cache = collections.defaultdict(lambda: float('inf'))


def greedy_algorithm(data, x_column_name, y_column_name, id_column_name):
    regions = []
    remaining_points = list(range(len(data)))
    print("贪心算法开始执行，正在生成数据区域...")
    
    # 创建结果列表，用于存储每个点的区域和顺序信息
    result_data = []
    
    # 初始化网格系统
    grid_system = initialize_grid(data, x_column_name, y_column_name, remaining_points)
    
    region_count = 1
    while len(regions) < 80 and remaining_points:
        print(f"开始生成第 {len(regions) + 1} 个数据区域，当前还剩余 {len(remaining_points)} 个数据点待处理...")
        # 优化起始点选择，简单判断下剩余点数量，若太少提前结束
        if len(remaining_points) < 16:
            print("剩余数据点不足，提前结束数据区域生成循环。")
            break
        
        # 随机确定本区域的最大点数（16-19之间）
        max_points_in_region = np.random.randint(16, 20)
        
        # 选择起始点，使用网格密度估算
        start_index = select_start_index_grid(data, x_column_name, y_column_name, remaining_points, grid_system)
        region = []
        region.append(data.iloc[start_index][id_column_name])  # 加入起始点的id
        remaining_points.remove(start_index)
        
        # 更新网格系统
        update_grid(grid_system, data, x_column_name, y_column_name, start_index, remove=True)
        
        print(f"已选择起始点，其ID为 {data.iloc[start_index][id_column_name]}，本区域最大点数: {max_points_in_region}")
        
        # 添加起始点到结果数据
        point_data = data.iloc[start_index].to_dict()
        point_data['区域编号'] = region_count
        point_data['区域内顺序'] = 1
        result_data.append(point_data)
        
        # 构建数据区域，添加连续找不到合适点的提前结束逻辑
        consecutive_fail_count = 0
        point_count = 2  # 起始点已经是1，所以从2开始
        while len(region) < max_points_in_region and remaining_points:
            nearest_index = find_nearest_unused(start_index, region, data, x_column_name, y_column_name, remaining_points)
            if nearest_index is not None:
                region.append(data.iloc[nearest_index][id_column_name])  # 加入对应点的id
                remaining_points.remove(nearest_index)
                
                # 更新网格系统
                update_grid(grid_system, data, x_column_name, y_column_name, nearest_index, remove=True)
                
                consecutive_fail_count = 0
                print(f"成功向当前区域添加一个点，当前区域已包含 {len(region)} 个点。")
                
                # 添加当前点到结果数据
                point_data = data.iloc[nearest_index].to_dict()
                point_data['区域编号'] = region_count
                point_data['区域内顺序'] = point_count
                result_data.append(point_data)
                point_count += 1
            else:
                consecutive_fail_count += 1
                if consecutive_fail_count >= 10:  # 连续10次找不到合适点就结束该区域构建
                    print("连续多次未找到合适点，结束当前数据区域构建。")
                    break
        regions.append(region)
        print(f"已完成第 {len(regions)} 个数据区域构建，该区域包含 {len(region)} 个点。")
        region_count += 1
    
    print("贪心算法执行完毕，数据区域生成完成。")
    return regions, result_data


def initialize_grid(data, x_column_name, y_column_name, remaining_points):
    """
    初始化网格系统，用于快速密度估算
    网格大小基于数据的地理范围和threshold值
    """
    # 计算数据的地理边界
    min_lat = data[x_column_name].min()
    max_lat = data[x_column_name].max()
    min_lng = data[y_column_name].min()
    max_lng = data[y_column_name].max()
    
    # 根据threshold确定网格大小，网格大小约为threshold的2倍
    grid_size = threshold * 2
    
    # 计算网格数量
    grid_rows = int((max_lat - min_lat) / grid_size) + 1
    grid_cols = int((max_lng - min_lng) / grid_size) + 1
    
    # 初始化网格，存储每个网格内的点索引
    grid = [[[] for _ in range(grid_cols)] for _ in range(grid_rows)]
    
    # 将所有点分配到对应网格
    for point_idx in remaining_points:
        lat = data.iloc[point_idx][x_column_name]
        lng = data.iloc[point_idx][y_column_name]
        
        row = int((lat - min_lat) / grid_size)
        col = int((lng - min_lng) / grid_size)
        
        # 确保索引在有效范围内
        row = min(row, grid_rows - 1)
        col = min(col, grid_cols - 1)
        
        grid[row][col].append(point_idx)
    
    return {
        'grid': grid,
        'min_lat': min_lat,
        'min_lng': min_lng,
        'grid_size': grid_size,
        'grid_rows': grid_rows,
        'grid_cols': grid_cols
    }


def select_start_index_grid(data, x_column_name, y_column_name, remaining_points, grid_system):
    """
    使用网格系统选择密度最高区域的起始点
    """
    if len(remaining_points) <= 1:
        return remaining_points[0] if remaining_points else None
    
    grid = grid_system['grid']
    max_density = 0
    best_candidates = []
    
    # 遍历所有网格，找到密度最高的网格
    for row in range(grid_system['grid_rows']):
        for col in range(grid_system['grid_cols']):
            if grid[row][col]:  # 如果网格内有点
                # 计算该网格及其邻近网格的总点数作为密度指标
                density = calculate_grid_density(grid, row, col, grid_system['grid_rows'], grid_system['grid_cols'])
                
                if density > max_density:
                    max_density = density
                    best_candidates = grid[row][col].copy()
                elif density == max_density:
                    best_candidates.extend(grid[row][col])
    
    # 从最佳候选点中随机选择
    if best_candidates:
        # 确保候选点都在remaining_points中
        valid_candidates = [idx for idx in best_candidates if idx in remaining_points]
        if valid_candidates:
            return np.random.choice(valid_candidates)
    
    # 如果没有找到合适的候选点，随机选择
    return np.random.choice(remaining_points)


def calculate_grid_density(grid, row, col, grid_rows, grid_cols):
    """
    计算指定网格及其邻近网格的点密度
    """
    density = 0
    # 检查3x3邻域
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < grid_rows and 0 <= nc < grid_cols:
                density += len(grid[nr][nc])
    return density


def update_grid(grid_system, data, x_column_name, y_column_name, point_idx, remove=True):
    """
    更新网格系统，添加或移除点
    """
    lat = data.iloc[point_idx][x_column_name]
    lng = data.iloc[point_idx][y_column_name]
    
    row = int((lat - grid_system['min_lat']) / grid_system['grid_size'])
    col = int((lng - grid_system['min_lng']) / grid_system['grid_size'])
    
    # 确保索引在有效范围内
    row = min(row, grid_system['grid_rows'] - 1)
    col = min(col, grid_system['grid_cols'] - 1)
    
    if remove:
        if point_idx in grid_system['grid'][row][col]:
            grid_system['grid'][row][col].remove(point_idx)
    else:
        grid_system['grid'][row][col].append(point_idx)


def select_start_index(data, x_column_name, y_column_name, remaining_points):
    """
    优化的起始点选择策略：使用采样和快速估算来选择密度较高的点
    避免精确计算所有点的密度，提高运算效率
    """
    if len(remaining_points) <= 1:
        return remaining_points[0] if remaining_points else None
    
    # 如果剩余点数较少，直接随机选择
    if len(remaining_points) <= 50:
        return np.random.choice(remaining_points)
    
    # 采样策略：只对部分点进行密度估算
    sample_size = min(100, len(remaining_points) // 5)  # 采样数量
    sampled_points = np.random.choice(remaining_points, size=sample_size, replace=False)
    
    # 快速密度估算：只计算最近的几个邻居
    density_scores = []
    for point_idx in sampled_points:
        # 简化密度计算：只统计最近的10个点
        density = fast_density_estimate(point_idx, data, x_column_name, y_column_name, remaining_points)
        density_scores.append((point_idx, density))
    
    # 选择密度最高的几个候选点
    density_scores.sort(key=lambda x: x[1], reverse=True)
    top_candidates = density_scores[:min(5, len(density_scores))]  # 取前5个
    
    # 从候选点中随机选择
    selected_point = np.random.choice([idx for idx, _ in top_candidates])
    return selected_point


def fast_density_estimate(index, data, x_column_name, y_column_name, remaining_points):
    """
    快速密度估算：只计算最近的几个邻居点，避免遍历所有剩余点
    """
    if len(remaining_points) <= 10:
        return len(remaining_points)
    
    point = np.array([data.iloc[index][x_column_name], data.iloc[index][y_column_name]])
    
    # 随机采样一部分点进行距离计算
    sample_size = min(50, len(remaining_points))
    sampled_indices = np.random.choice(remaining_points, size=sample_size, replace=False)
    
    nearby_count = 0
    for i in sampled_indices:
        if i == index:
            continue
        other_point = np.array([data.iloc[i][x_column_name], data.iloc[i][y_column_name]])
        # 使用曼哈顿距离代替欧几里得距离，计算更快
        dist = abs(other_point[0] - point[0]) + abs(other_point[1] - point[1])
        if dist < threshold * 1.5:  # 稍微放宽阈值
            nearby_count += 1
    
    # 根据采样比例估算总密度
    estimated_density = nearby_count * len(remaining_points) / sample_size
    return estimated_density


def count_nearby_points(index, data, x_column_name, y_column_name, remaining_points):
    point = np.array([data.iloc[index][x_column_name], data.iloc[index][y_column_name]])
    count = 0
    for i in remaining_points:
        other_point = np.array([data.iloc[i][x_column_name], data.iloc[i][y_column_name]])
        # 先从缓存中获取距离，如果距离小于阈值则直接使用缓存结果
        pair_key = tuple(sorted([index, i]))
        dist = distance_cache[pair_key]
        if dist < threshold:
            count += 1
            continue
        # 如果缓存中距离大于等于阈值，重新计算距离并更新缓存
        dist = np.linalg.norm(other_point - point)
        distance_cache[pair_key] = dist
        if dist < threshold:
            count += 1
    return count


def find_nearest_unused(start_index, region, data, x_column_name, y_column_name, remaining_points):
    start_point = np.array([data.iloc[start_index][x_column_name], data.iloc[start_index][y_column_name]])
    # 构建KD树，只传入剩余点的坐标数据
    kdtree = KDTree(np.array([[data.iloc[i][x_column_name], data.iloc[i][y_column_name]] for i in remaining_points]))
    # 查询距离起始点的所有点距离及索引，不使用distance_upper_bound参数
    distances, indices = kdtree.query([start_point], k=len(remaining_points), return_distance=True)
    # 筛选出距离在阈值范围内的点索引
    valid_indices = [i for i, dist in zip(indices[0], distances[0]) if dist < threshold]
    if valid_indices:
        # 从符合条件的点中选择距离最近的那个点的索引
        nearest_index = valid_indices[np.argmin([distances[0][i] for i in valid_indices])]
        return remaining_points[nearest_index]
    return None


# 从Excel文件中读取数据
input_df = pd.read_excel(r'/Users/a000/药店规划/遵义附近药店数据_20250807_1402.xlsx', sheet_name='汇总去重-去无照片-改地址-重名-兽医草药中药')
# 根据实际情况指定列名
x_column_name = '纬度'
y_column_name = '经度'
id_column_name = 'uid'
data = input_df.copy()

# 运行贪心算法
result_regions, result_data = greedy_algorithm(data, x_column_name, y_column_name, id_column_name)

# 将结果转换为DataFrame并保存为Excel文件
result_df = pd.DataFrame(result_data)

# 生成输出文件名（包含时间戳）
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_filename = f'/Users/a000/药店规划/遵义药店区域划分结果_{timestamp}.xlsx'

# 保存到Excel文件
result_df.to_excel(output_filename, index=False, sheet_name='区域划分结果')
print(f"区域划分结果已保存到: {output_filename}")
print(f"共划分了 {len(result_regions)} 个区域，包含 {len(result_df)} 个药店")

# 显示每个区域的统计信息
region_stats = result_df.groupby('区域编号').size().reset_index(name='药店数量')
print("\n各区域药店数量统计:")
print(region_stats.to_string(index=False))