import csv
import requests
import json
import logging
import openpyxl
import pandas as pd
from datetime import datetime
import os
import time

# 配置参数
excel_file_path = '/Users/a000/Documents/济生/药店拜访25/贵州药店查询结果_20251213.xlsx'  # 输入文件

# 城市和区域过滤配置（留空表示不过滤）
filter_city = "贵阳市"  # 例如: "贵阳市"，留空不过滤城市
filter_area = "南明区"  # 例如: "南明区"，留空不过滤区域

# 从指定uid开始查询（留空表示从头开始）
start_from_uid = "3b7f1c27eb9179cd04026fbc"  # 例如: "b7e5f1234567890"，留空则从头开始处理

# 获取输入文件所在目录
input_dir = os.path.dirname(excel_file_path)

# 生成输出文件和日志文件路径（与输入文件同一目录）
out_file_path = f'{input_dir}/附近药店数据_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'  # 输出文件
log_file_path = f'{input_dir}/附近药店搜索_{datetime.now().strftime("%Y%m%d_%H%M")}.log'  # 日志文件

# 设置百度地图API密钥等相关参数
ak = "9quP8V19nrZZdtTPu3Dgc66kvPSnV0rf"
radius = "3000"
query = "药店"
page_size = 20
api_count = 0  # 当前已使用的API次数
max_api_calls = 100  # 最大API调用次数
request_delay = 0.5  # API调用之间的延迟时间（秒），可根据需要调整

# 设置日志
logging.basicConfig(
    filename=log_file_path, 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 构建请求URL的函数
def build_url(page_num, location):
    return f"https://api.map.baidu.com/place/v2/search?query={query}&scope=2&location={location}&radius={radius}&output=json&ak={ak}&page_size={page_size}&page_num={page_num}"

# 获取所有药店数据并返回数据列表
def get_all_pharmacy_data(api_count, location, source_name):
    page_num = 0
    all_pois_count = 0
    data_list = []  # 存储所有数据
    
    while api_count < max_api_calls:
        url = build_url(page_num, location)
        try:
            response = requests.get(url, timeout=10)
            api_count += 1
            logging.info(f"API调用 {api_count}: {url}")
            
            # 添加请求延迟，避免请求过快
            time.sleep(request_delay)
            
            data = response.json()
            if data["status"] != 0:
                logging.warning(f"API返回错误状态: {data.get('message', '未知错误')}")
                break
                
            pois = data["results"]
            if not pois:
                break
                
            for poi in pois:
                uid = poi["uid"]
                street_id = poi.get("street_id", "")
                name = poi["name"]
                city = poi["city"]
                area = poi["area"]
                address = poi["address"]
                location_data = poi["location"]
                lat = location_data["lat"]
                lng = location_data["lng"]
                detail_url = poi["detail_info"].get("detail_url", "")
                shop_hours = poi["detail_info"].get("shop_hours", "")
                image_num = poi["detail_info"].get("image_num", "")
                navi_location = poi["detail_info"].get("navi_location", {})
                lat2 = navi_location.get("lat", "")
                lng2 = navi_location.get("lng", "")

                data_row = {
                    '源药店': source_name,
                    '源坐标': location,
                    'uid': uid,
                    'street_id': street_id,
                    '名称': name,
                    '城市': city,
                    '区域': area,
                    '地址': address,
                    '经纬度': f"{lat},{lng}",
                    '导航经纬度': f"{lat2},{lng2}" if lat2 and lng2 else "",
                    '营业时间': shop_hours,
                    '图片数': image_num,
                    '详情链接': detail_url
                }
                data_list.append(data_row)

            all_pois_count += len(pois)
            page_num += 1

            total = data.get("total", 0)
            logging.info(f"已获取: {all_pois_count}, 总计: {total}, API调用次数: {api_count}")
            
            if all_pois_count >= total:
                break
                
        except Exception as e:
            logging.error(f"请求出错: {str(e)}")
            break
            
        # 检查API调用次数
        if api_count >= max_api_calls:
            logging.warning(f"已达到最大API调用次数限制: {max_api_calls}")
            break

    return data_list, api_count

# 从Excel读取药店数据
def read_pharmacy_data_from_excel(file_path):
    df = pd.read_excel(file_path)
    pharmacy_data = []
    
    # 检查是否存在城市和区域列
    has_city_column = '城市' in df.columns
    has_area_column = '区' in df.columns  # 实际输入文件中的列名为"区"而不是"区域"
    has_uid_column = 'uid' in df.columns  # 检查是否有uid列
    
    # 记录过滤信息
    if filter_city or filter_area:
        logging.info(f"开始过滤数据 - 城市: {filter_city or '不限'}, 区域: {filter_area or '不限'}")
        print(f"开始过滤数据 - 城市: {filter_city or '不限'}, 区域: {filter_area or '不限'}")
    
    for index, row in df.iterrows():
        name = row['名称']
        location_str = row['经纬度']
        
        # 如果有uid列，获取uid值
        uid = str(row.get('uid', '')) if has_uid_column and pd.notna(row.get('uid', '')) else ''
        
        # 过滤城市和区域
        if filter_city or filter_area:
            # 检查城市列
            city_match = True
            if filter_city and has_city_column:
                city_value = str(row.get('城市', '')) if pd.notna(row.get('城市', '')) else ''
                city_match = filter_city in city_value
            
            # 检查区域列
            area_match = True
            if filter_area and has_area_column:
                area_value = str(row.get('区', '')) if pd.notna(row.get('区', '')) else ''
                area_match = filter_area in area_value
            
            # 如果不匹配过滤条件，则跳过
            if not (city_match and area_match):
                continue
        
        # 解析经纬度
        if pd.notna(location_str) and ',' in str(location_str):
            try:
                lat, lng = str(location_str).split(',')
                location = f"{lat.strip()},{lng.strip()}"
                pharmacy_data.append({
                    'name': name,
                    'location': location,
                    'uid': uid  # 添加uid字段
                })
            except:
                logging.warning(f"无法解析坐标: {location_str}")
                continue
    
    if filter_city or filter_area:
        logging.info(f"过滤完成，共获取 {len(pharmacy_data)} 个符合条件的药店坐标")
        print(f"过滤完成，共获取 {len(pharmacy_data)} 个符合条件的药店坐标")
    
    return pharmacy_data

# 保存数据到Excel文件
def save_to_excel(data_list, output_path):
    if not data_list:
        print("没有数据可保存")
        return
        
    df = pd.DataFrame(data_list)
    
    # 去重：基于所有列的完全重复行
    original_count = len(df)
    df = df.drop_duplicates()
    deduplicated_count = len(df)
    removed_count = original_count - deduplicated_count
    
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"数据已保存到: {output_path}")
    print(f"原始记录数: {original_count}")
    print(f"去重后记录数: {deduplicated_count}")
    print(f"移除重复记录数: {removed_count}")

if __name__ == "__main__":
    print(f"开始处理药店附近搜索...")
    print(f"当前API调用次数: {api_count}")
    print(f"最大API调用次数: {max_api_calls}")
    
    # 读取药店数据
    pharmacy_data = read_pharmacy_data_from_excel(excel_file_path)
    print(f"从Excel文件读取到 {len(pharmacy_data)} 个药店坐标")
    
    # 如果指定了起始uid，则找到该uid的位置并跳过之前的数据
    start_index = 0
    if start_from_uid:
        print(f"从uid为 '{start_from_uid}' 的药店开始处理...")
        for i, pharmacy in enumerate(pharmacy_data):
            if pharmacy.get('uid', '') == start_from_uid:
                start_index = i + 1  # 跳过当前uid，从下一个开始
                print(f"找到起始uid，从第 {start_index + 1} 个药店开始处理")
                break
        if start_index == 0:
            print(f"警告: 在数据中未找到指定的起始uid '{start_from_uid}'，将从头开始处理")
            start_index = 0
    
    all_results = []
    processed_count = start_index  # 初始化为起始索引
    
    for i in range(start_index, len(pharmacy_data)):
        pharmacy = pharmacy_data[i]
        if api_count >= max_api_calls:
            print(f"已达到API调用次数限制，停止处理")
            break
            
        print(f"正在处理第 {i + 1}/{len(pharmacy_data)} 个药店: {pharmacy['name']}")
        
        # 获取附近药店数据
        nearby_data, api_count = get_all_pharmacy_data(api_count, pharmacy['location'], pharmacy['name'])
        all_results.extend(nearby_data)
        
        processed_count += 1
        print(f"已处理 {processed_count} 个药店，获得 {len(nearby_data)} 条附近药店数据，累计API调用: {api_count}")
        
        # 每处理200个药店保存一次（防止数据丢失）
        if processed_count % 200 == 0:
            temp_file = f'{input_dir}/附近药店数据_临时_{processed_count}.xlsx'
            save_to_excel(all_results, temp_file)
            print(f"临时保存到: {temp_file}")
    
    # 最终保存
    save_to_excel(all_results, out_file_path)
    
    print(f"\n处理完成!")
    print(f"总共处理了 {processed_count - start_index} 个药店 (从第 {start_index + 1} 个开始)")
    print(f"获得 {len(all_results)} 条附近药店数据")
    print(f"最终API调用次数: {api_count}")
    print(f"数据保存到: {out_file_path}")
    print(f"日志保存到: {log_file_path}")