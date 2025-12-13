import requests
import openpyxl
import time
import json
import logging
import os

# 设置百度地图API密钥
ak = "9quP8V19nrZZdtTPu3Dgc66kvPSnV0rf"
# 设置检索关键字为药店
query = "药店"
# 设置每页返回的POI数量，最大为20条
page_size = 20

# API调用计数器和限制
api_count = 10257  # 当前已使用的API次数
max_api_calls = 20000  # 最大API调用次数限制

# 遵义市所有区县列表
zunyi_regions = [
    "红花岗区", "汇川区", "播州区", "新蒲新区",  # 3个区 + 新蒲新区
    "桐梓县", "绥阳县", "正安县", "凤冈县", "湄潭县", "余庆县", "习水县",  # 7个县
    "道真仡佬族苗族自治县", "务川仡佬族苗族自治县",  # 2个民族自治县
    "仁怀市", "赤水市"  # 2个市
]

# 设置日志文件路径（使用当前目录）
log_file_path = os.path.join(os.getcwd(), '遵义市药店查询.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   encoding='utf-8')


# 构建请求URL的函数
def build_url(page_num, region):
    return f"https://api.map.baidu.com/place/v2/search?query={query}&region={region}&scope=2&output=json&ak={ak}&page_size={page_size}&page_num={page_num}"

# 获取单个区县的药店数据并保存到Excel文件的函数
def get_region_pharmacy_data_and_save(api_count, region, sheet, workbook, out_file_path):
    page_num = 0
    all_pois_count = 0  # 用于累计所有页获取到的pois数量
    region_pois_count = 0  # 当前区县获取到的药店数量

    print(f"正在查询 {region} 的药店数据...")
    logging.info(f"开始查询区域: {region}")

    while True:
        # 检查API调用次数限制
        if api_count >= max_api_calls:
            print(f"已达到API调用次数限制 ({max_api_calls} 次)，停止查询")
            logging.warning(f"已达到API调用次数限制 ({max_api_calls} 次)，停止查询")
            return api_count, region_pois_count, True  # 返回True表示达到限制

        url = build_url(page_num, region)
        try:
            response = requests.get(url, timeout=10)
            api_count += 1
            logging.info(f"API调用 {api_count}: {url}")
            
            data = response.json()
            if data["status"] != 0:
                print(f"请求失败，错误信息：{data.get('message', '未知错误')}")
                logging.error(f"请求失败，区域: {region}, 错误: {data.get('message', '未知错误')}")
                break
                
            pois = data.get("results", [])
            if not pois:
                break
                
            for poi in pois:
                uid = poi.get("uid", "")
                street_id = poi.get("street_id", "")
                name = poi.get("name", "")
                city = poi.get("city", "")
                area = poi.get("area", "")
                address = poi.get("address", "")
                location_data = poi.get("location", {})
                lat = location_data.get("lat", "")
                lng = location_data.get("lng", "")
                detail_info = poi.get("detail_info", {})
                detail_url = detail_info.get("detail_url", "")
                shop_hours = detail_info.get("shop_hours", "")
                image_num = detail_info.get("image_num", "")
                navi_location = detail_info.get("navi_location", {})
                lat2 = navi_location.get("lat", "")
                lng2 = navi_location.get("lng", "")

                # 将获取到的数据整理为元组形式，方便后续添加到Excel表格中
                data_tuple = (region, uid, street_id, name, city, area, address, 
                             f"{lat},{lng}", f"{lat2},{lng2}", shop_hours, image_num, detail_url)
                sheet.append(data_tuple)
                region_pois_count += 1

            # 每处理完一页数据就保存一次文件
            workbook.save(out_file_path)

            total = data.get("total", 0)
            all_pois_count += len(pois)  # 累计当前页的pois数量
            
            print(f"  {region}: 已获取 {all_pois_count}/{total} 条数据 (API调用: {api_count})")
            logging.info(f"区域 {region}: 已获取 {all_pois_count}/{total} 条数据, API调用次数: {api_count}")
            
            if all_pois_count >= total:
                break
                
            page_num += 1
            time.sleep(0.5)  # 适当延迟，避免请求过快
            
        except requests.exceptions.RequestException as e:
            print(f"网络请求异常: {e}")
            logging.error(f"网络请求异常，区域: {region}, 错误: {e}")
            break
        except Exception as e:
            print(f"处理数据时发生异常: {e}")
            logging.error(f"处理数据异常，区域: {region}, 错误: {e}")
            break

    print(f"  {region} 查询完成，共获取 {region_pois_count} 条药店数据")
    logging.info(f"区域 {region} 查询完成，共获取 {region_pois_count} 条药店数据")
    return api_count, region_pois_count, False  # 返回False表示未达到限制

if __name__ == "__main__":
    # 输出文件路径（使用当前目录）
    out_file_path = os.path.join(os.getcwd(), '遵义市所有区县药店数据.xlsx')
    
    # 创建Excel文件并设置表头
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["区域", "uid", "street_id", "名称", "城市", "区", "地址", "经纬度", "导航经纬度", "营业时间", "图片数", "链接"])
    wb.save(out_file_path)
    
    print(f"开始查询遵义市所有区县的药店数据...")
    print(f"当前API已使用次数: {api_count}, 限制: {max_api_calls}")
    print(f"数据将保存到: {out_file_path}")
    logging.info(f"开始批量查询，当前API使用次数: {api_count}, 限制: {max_api_calls}")
    
    total_pharmacies = 0  # 总药店数量
    completed_regions = []  # 已完成查询的区县
    failed_regions = []  # 查询失败的区县
    
    # 遍历所有区县进行查询
    for i, region in enumerate(zunyi_regions, 1):
        print(f"\n[{i}/{len(zunyi_regions)}] 开始查询: {region}")
        
        try:
            api_count, region_count, limit_reached = get_region_pharmacy_data_and_save(
                api_count, region, ws, wb, out_file_path
            )
            
            total_pharmacies += region_count
            completed_regions.append((region, region_count))
            
            if limit_reached:
                print(f"\n*** 已达到API调用次数限制，停止查询 ***")
                print(f"已完成查询的区县: {len(completed_regions)}/{len(zunyi_regions)}")
                break
                
        except Exception as e:
            print(f"查询 {region} 时发生异常: {e}")
            logging.error(f"查询 {region} 时发生异常: {e}")
            failed_regions.append(region)
            continue
    
    # 输出汇总信息
    print(f"\n=== 查询完成汇总 ===")
    print(f"总API调用次数: {api_count}")
    print(f"总药店数量: {total_pharmacies}")
    print(f"成功查询区县数: {len(completed_regions)}")
    print(f"失败区县数: {len(failed_regions)}")
    
    if completed_regions:
        print(f"\n各区县药店数量:")
        for region, count in completed_regions:
            print(f"  {region}: {count} 家")
    
    if failed_regions:
        print(f"\n查询失败的区县: {', '.join(failed_regions)}")
    
    print(f"\n数据已保存到: {out_file_path}")
    
    # 记录最终汇总日志
    logging.info(f"查询完成汇总 - 总API调用: {api_count}, 总药店数: {total_pharmacies}, 成功区县: {len(completed_regions)}, 失败区县: {len(failed_regions)}")
    
    print("\n数据获取及保存完成。")