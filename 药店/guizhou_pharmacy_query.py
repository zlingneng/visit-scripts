import requests
import xlrd
import openpyxl
import time
import json
import logging
import os
from datetime import datetime

# ===================== 配置项 =====================
# 设置百度地图API密钥
AK = "9quP8V19nrZZdtTPu3Dgc66kvPSnV0rf"
# 设置检索关键字
QUERY = "药店"
# 设置每页返回的POI数量，最大为20条
PAGE_SIZE = 20

# API调用计数器和限制
API_COUNT = 15021  # 当前已使用的API次数（可配置）
MAX_API_CALLS = 30000  # 最大API调用次数限制（可配置）
REQUEST_DELAY = 0.5  # 每两次API请求之间的延迟时间（秒），可配置

# 区划表配置
DIVISION_FILE_PATH = '/Users/a000/Documents/济生/药店拜访25/附件2贵州省乡级以上政区名称及行政区划代码表.xls'

# 输出配置
TARGET_CITIES = ["贵州省"]  # 目标城市列表，支持配置多个市（如["贵阳市", "遵义市"]）或全省（["贵州省"]）
OUTPUT_DIR = os.path.dirname(DIVISION_FILE_PATH)  # 输出到区划表格的同级别文件夹
DATE_SUFFIX = datetime.now().strftime("%Y%m%d")  # 日期后缀

# 生成输出文件名
if len(TARGET_CITIES) == 1 and TARGET_CITIES[0] == "贵州省":
    # 全省查询
    output_prefix = "贵州"
elif len(TARGET_CITIES) == 1:
    # 单个城市查询
    output_prefix = TARGET_CITIES[0].replace('市', '')
else:
    # 多个城市查询
    output_prefix = "_".join([city.replace('市', '') for city in TARGET_CITIES])

OUTPUT_FILE_NAME = f"{output_prefix}药店查询结果_{DATE_SUFFIX}.xlsx"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILE_NAME)

# 日志配置
LOG_FILE_NAME = f"{output_prefix}药店查询日志_{DATE_SUFFIX}.log"
LOG_FILE_PATH = os.path.join(OUTPUT_DIR, LOG_FILE_NAME)
# =================================================


# 配置日志
logging.basicConfig(filename=LOG_FILE_PATH, level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   encoding='utf-8')


# 构建请求URL的函数
def build_url(page_num, region):
    return f"https://api.map.baidu.com/place/v2/search?query={QUERY}&region={region}&scope=2&output=json&ak={AK}&page_size={PAGE_SIZE}&page_num={page_num}"

# 获取单个区县的药店数据并保存到Excel文件的函数
def get_region_pharmacy_data_and_save(api_count, region, sheet, workbook):
    page_num = 0
    all_pois_count = 0  # 用于累计所有页获取到的pois数量
    region_pois_count = 0  # 当前区县获取到的药店数量

    print(f"正在查询 {region} 的药店数据...")
    logging.info(f"开始查询区域: {region}")

    while True:
        # 检查API调用次数限制
        if api_count >= MAX_API_CALLS:
            print(f"已达到API调用次数限制 ({MAX_API_CALLS} 次)，停止查询")
            logging.warning(f"已达到API调用次数限制 ({MAX_API_CALLS} 次)，停止查询")
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
            workbook.save(OUTPUT_FILE_PATH)

            total = data.get("total", 0)
            all_pois_count += len(pois)  # 累计当前页的pois数量
            
            print(f"  {region}: 已获取 {all_pois_count}/{total} 条数据 (API调用: {api_count})")
            logging.info(f"区域 {region}: 已获取 {all_pois_count}/{total} 条数据, API调用次数: {api_count}")
            
            if all_pois_count >= total:
                break
                
            page_num += 1
            time.sleep(REQUEST_DELAY)  # 适当延迟，避免请求过快
            
        except requests.exceptions.RequestException as e:
            print(f"网络请求异常: {e}")
            logging.error(f"网络请求异常，区域: {region}, 错误: {e}")
            break
        except Exception as e:
            print(f"处理数据时发生异常: {e}")
            logging.error(f"处理数据异常，区域: {region}, 错误: {e}")
            import traceback
            traceback.print_exc()
            break

    print(f"  {region} 查询完成，共获取 {region_pois_count} 条药店数据")
    logging.info(f"区域 {region} 查询完成，共获取 {region_pois_count} 条药店数据")
    return api_count, region_pois_count, False  # 返回False表示未达到限制

# 从区划表中读取行政区划数据
def read_divisions():
    """读取区划表，返回符合目标城市的所有行政区划"""
    try:
        print(f"正在读取区划表: {DIVISION_FILE_PATH}")
        logging.info(f"开始读取区划表: {DIVISION_FILE_PATH}")
        
        # 打开区划表
        wb = xlrd.open_workbook(DIVISION_FILE_PATH)
        # 使用名称为Sheet2的工作表
        sheet = wb.sheet_by_name('Sheet2')
        
        divisions = []
        
        # 从第2行开始读取数据（第1行是表头）
        for i in range(1, sheet.nrows):
            row = sheet.row_values(i)
            if len(row) < 2:
                continue
                
            city = str(row[0]).strip()
            county = str(row[1]).strip()
            
            # 跳过空行
            if not city or not county:
                continue
                
            # 构建完整的行政区划名称
            full_region = f"{city}{county}"
            
            # 判断是否符合目标城市
            if "贵州省" in TARGET_CITIES:
                # 如果是全省查询，直接添加
                divisions.append(full_region)
            else:
                # 如果是特定市查询，只添加目标城市下的行政区划
                if any(target_city in city for target_city in TARGET_CITIES):
                    divisions.append(full_region)
        
        # 去重并排序
        divisions = list(set(divisions))
        divisions.sort()
        
        print(f"\n成功读取 {len(divisions)} 个行政区划")
        logging.info(f"成功读取 {len(divisions)} 个行政区划")
        
        return divisions
        
    except Exception as e:
        print(f"读取区划表时出错: {e}")
        logging.error(f"读取区划表时出错: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # 初始化日志
    logging.basicConfig(filename=LOG_FILE_PATH, level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s',
                       encoding='utf-8')
    
    print("=" * 60)
    print("贵州省药店查询系统")
    print("=" * 60)
    print(f"目标城市: {', '.join(TARGET_CITIES)}")
    print(f"API初始使用量: {API_COUNT}")
    print(f"API最大限制: {MAX_API_CALLS}")
    print(f"区划表路径: {DIVISION_FILE_PATH}")
    print(f"输出文件: {OUTPUT_FILE_PATH}")
    print(f"日志文件: {LOG_FILE_PATH}")
    print("=" * 60)
    
    # 读取行政区划
    regions = read_divisions()
    if not regions:
        print("未获取到行政区划数据，程序退出")
        logging.error("未获取到行政区划数据，程序退出")
        exit(1)
    
    print(f"\n待查询行政区划 ({len(regions)} 个):")
    for i, region in enumerate(regions[:10], 1):
        print(f"  {i}. {region}")
    if len(regions) > 10:
        print(f"  ... 等 {len(regions)} 个行政区划")
    
    # 创建Excel文件并设置表头
    print(f"\n正在创建输出文件: {OUTPUT_FILE_PATH}")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["区域", "uid", "street_id", "名称", "城市", "区", "地址", "经纬度", "导航经纬度", "营业时间", "图片数", "链接"])
    wb.save(OUTPUT_FILE_PATH)
    
    print(f"\n开始查询 {', '.join(TARGET_CITIES)} 的药店数据...")
    print(f"当前API已使用次数: {API_COUNT}, 限制: {MAX_API_CALLS}")
    logging.info(f"开始批量查询，目标城市: {', '.join(TARGET_CITIES)}, 当前API使用次数: {API_COUNT}, 限制: {MAX_API_CALLS}")
    
    total_pharmacies = 0  # 总药店数量
    completed_regions = []  # 已完成查询的区县
    failed_regions = []  # 查询失败的区县
    
    # 遍历所有区县进行查询
    for i, region in enumerate(regions, 1):
        print(f"\n[{i}/{len(regions)}] 开始查询: {region}")
        
        try:
            API_COUNT, region_count, limit_reached = get_region_pharmacy_data_and_save(
                API_COUNT, region, ws, wb
            )
            
            total_pharmacies += region_count
            completed_regions.append((region, region_count))
            
            if limit_reached:
                print(f"\n*** 已达到API调用次数限制，停止查询 ***")
                print(f"已完成查询的区县: {len(completed_regions)}/{len(regions)}")
                logging.warning(f"已达到API调用次数限制，停止查询")
                break
                
        except Exception as e:
            print(f"查询 {region} 时发生异常: {e}")
            logging.error(f"查询 {region} 时发生异常: {e}")
            failed_regions.append(region)
            continue
        
        # 在区域之间添加延迟，避免请求过快
        if i < len(regions):  # 不是最后一个区域时添加延迟
            print(f"\n区域查询间隔延迟 {REQUEST_DELAY} 秒...")
            time.sleep(REQUEST_DELAY)
    
    # 输出汇总信息
    print("\n" + "=" * 60)
    print(f"查询完成汇总")
    print(f"=" * 60)
    print(f"总API调用次数: {API_COUNT}")
    print(f"总药店数量: {total_pharmacies}")
    print(f"成功查询区县数: {len(completed_regions)}")
    print(f"失败区县数: {len(failed_regions)}")
    
    if completed_regions:
        print(f"\n各区县药店数量统计:")
        for region, count in sorted(completed_regions, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {region}: {count} 家")
        if len(completed_regions) > 10:
            print(f"  ... 等 {len(completed_regions)} 个区县")
    
    if failed_regions:
        print(f"\n查询失败的区县: {', '.join(failed_regions[:5])}")
        if len(failed_regions) > 5:
            print(f"  ... 等 {len(failed_regions)} 个区县")
    
    print(f"\n数据已保存到: {OUTPUT_FILE_PATH}")
    print(f"日志已保存到: {LOG_FILE_PATH}")
    
    # 记录最终汇总日志
    logging.info(f"查询完成汇总 - 总API调用: {API_COUNT}, 总药店数: {total_pharmacies}, 成功区县: {len(completed_regions)}, 失败区县: {len(failed_regions)}")
    
    print(f"\n{'=' * 60}")
    print("数据获取及保存完成。")
