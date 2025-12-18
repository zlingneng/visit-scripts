# 百度坐标系(BD-09)转WGS84坐标系
# 参考：https://github.com/wandergis/coordTransform_py

import math
import pandas as pd

# 配置部分
EXCEL_FILE_PATH = '/Users/a000/Documents/济生/药店拜访25/福建/附近药店数据_20251215_2216.xlsx'
SHEET_NAME = 'Sheet1'
INPUT_COLUMN = '经纬度'  # 百度坐标所在列（第7列）
OUTPUT_COLUMN = '华为经纬度'  # 华为照片经纬度系统(WGS84)所在列（新列）

# 定义一些常量
x_PI = 3.14159265358979324 * 3000.0 / 180.0
PI = 3.1415926535897932384626
a = 6378245.0
ee = 0.00669342162296594323


def bd09_to_wgs84(bd_lon, bd_lat):
    """百度坐标系(BD-09)转WGS84坐标系"""
    # 先将百度坐标转为火星坐标(GCJ-02)
    gcj_lat, gcj_lon = bd09_to_gcj02(bd_lon, bd_lat)
    # 再将火星坐标转为WGS84坐标
    wgs_lat, wgs_lon = gcj02_to_wgs84(gcj_lat, gcj_lon)
    return wgs_lon, wgs_lat


def bd09_to_gcj02(bd_lon, bd_lat):
    """百度坐标系(BD-09)转火星坐标系(GCJ-02)"""
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_PI)
    gcj_lon = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)
    return gcj_lat, gcj_lon


def gcj02_to_wgs84(gcj_lat, gcj_lon):
    """火星坐标系(GCJ-02)转WGS84坐标系"""
    if out_of_china(gcj_lat, gcj_lon):
        return gcj_lat, gcj_lon
    dlat = _transformlat(gcj_lon - 105.0, gcj_lat - 35.0)
    dlng = _transformlng(gcj_lon - 105.0, gcj_lat - 35.0)
    radlat = gcj_lat / 180.0 * PI
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * PI)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * PI)
    mglat = gcj_lat + dlat
    mglng = gcj_lon + dlng
    wgs_lat = gcj_lat * 2 - mglat
    wgs_lon = gcj_lon * 2 - mglng
    return wgs_lat, wgs_lon


def _transformlat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * PI) + 40.0 * math.sin(lat / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * PI) + 320 * math.sin(lat * PI / 30.0)) * 2.0 / 3.0
    return ret


def _transformlng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * PI) + 20.0 * math.sin(2.0 * lng * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * PI) + 40.0 * math.sin(lng / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * PI) + 300.0 * math.sin(lng / 30.0 * PI)) * 2.0 / 3.0
    return ret


def out_of_china(lat, lng):
    """判断坐标是否在中国境外"""
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def main():
    # 读取Excel文件
    df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=SHEET_NAME)
    
    # 预览数据
    print("数据预览:")
    print(df.head())
    print(f"\n数据形状: {df.shape}")
    print(f"\n列名: {list(df.columns)}")
    
    # 处理经纬度转换
    print(f"\n开始转换经纬度...")
    wgs84_coords = []
    
    for idx, row in df.iterrows():
        try:
            # 获取百度坐标
            bd_coord = str(row[INPUT_COLUMN]).strip()
            if bd_coord and bd_coord != 'nan':
                # 分割经纬度
                lat_str, lon_str = bd_coord.split(',')
                bd_lat = float(lat_str)
                bd_lon = float(lon_str)
                
                # 转换为WGS84
                wgs_lon, wgs_lat = bd09_to_wgs84(bd_lon, bd_lat)
                # 格式化为字符串
                wgs_coord = f"{wgs_lat:.8f},{wgs_lon:.8f}"
                wgs84_coords.append(wgs_coord)
            else:
                wgs84_coords.append('')
        except Exception as e:
            print(f"第{idx+1}行转换失败: {e}")
            wgs84_coords.append('')
    
    # 将转换结果写入输出列
    df[OUTPUT_COLUMN] = wgs84_coords
    
    # 保存结果
    output_file = EXCEL_FILE_PATH.replace('.xlsx', '_转换后.xlsx')
    df.to_excel(output_file, index=False)
    
    print(f"\n转换完成！")
    print(f"转换结果已保存到: {output_file}")
    print(f"共处理 {len(df)} 行数据")


if __name__ == "__main__":
    main()