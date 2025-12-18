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
excel_file_path = '/Users/a000/Documents/济生/药店拜访25/福建/福建药店查询结果_20251215.xlsx'  # 输入文件

# 获取输入文件所在目录
input_dir = os.path.dirname(excel_file_path)

# 生成输出文件和日志文件路径（与输入文件同一目录）
out_file_path = f'{input_dir}/附近药店数据_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'  # 输出文件
log_file_path = f'{input_dir}/附近药店搜索_{datetime.now().strftime("%Y%m%d_%H%M")}.log'  # 日志文件

# 设置百度地图API密钥等相关参数
ak = "9quP8V19nrZZdtTPu3Dgc66kvPSnV0rf"
radius = "1000"
query = "药店"
page_size = 20
api_count = 15490  # 当前已使用的API次数
max_api_calls = 50000  # 最大API调用次数
request_delay = 0.1  # API调用之间的延迟时间（秒），可根据需要调整

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
    
    for index, row in df.iterrows():
        name = row['名称']
        location_str = row['经纬度']
        
        # 解析经纬度
        if pd.notna(location_str) and ',' in str(location_str):
            try:
                lat, lng = str(location_str).split(',')
                location = f"{lat.strip()},{lng.strip()}"
                pharmacy_data.append({
                    'name': name,
                    'location': location
                })
            except:
                logging.warning(f"无法解析坐标: {location_str}")
                continue
    
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
    
    all_results = []
    processed_count = 0
    
    for pharmacy in pharmacy_data:
        if api_count >= max_api_calls:
            print(f"已达到API调用次数限制，停止处理")
            break
            
        print(f"正在处理第 {processed_count + 1}/{len(pharmacy_data)} 个药店: {pharmacy['name']}")
        
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
    print(f"总共处理了 {processed_count} 个药店")
    print(f"获得 {len(all_results)} 条附近药店数据")
    print(f"最终API调用次数: {api_count}")
    print(f"数据保存到: {out_file_path}")
    print(f"日志保存到: {log_file_path}")