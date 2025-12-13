#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片GPS信息读取工具（百度地图版）
功能：
1. 读取照片的GPS经纬度信息
2. 将WGS84坐标转换为百度坐标系（BD09）
3. 使用百度地图API逆地理编码查询地址

使用方法：
python 查看照片GPS_百度.py [照片路径]
如果不提供照片路径，默认读取华为照片
"""

import sys
import json
from urllib import request, parse
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# 默认要查看的照片路径
DEFAULT_PHOTO_PATH = "/Users/a000/Pictures/huawei251210/IMG_20251210_160312.jpg"

# 百度地图API密钥（AK）
# 请到 https://lbsyun.baidu.com/apiconsole/key 申请
BAIDU_AK = "9quP8V19nrZZdtTPu3Dgc66kvPSnV0rf"  # 在这里填入你的百度AK，例如："你的百度AK"


def get_exif_data(image_path):
    """读取图片的 EXIF 信息"""
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return {}
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value
        return exif
    except Exception as e:
        print(f"读取图片失败: {e}")
        return {}


def get_gps_info(exif):
    """从 EXIF 中提取 GPS 信息并转换成十进制度经纬度（WGS84坐标系）"""
    gps_info_raw = exif.get("GPSInfo")
    if not gps_info_raw:
        return None, None, None

    gps_info = {}
    for key, val in gps_info_raw.items():
        sub_tag = GPSTAGS.get(key, key)
        gps_info[sub_tag] = val

    def _convert_to_degrees(value):
        """将GPS坐标转换为十进制度"""
        try:
            # 兼容三种格式：
            # 格式1 (华为等): (26.0, 34.0, 43.660125) - 直接是度分秒的浮点数
            # 格式2 (标准): ((26, 1), (34, 1), (43660125, 1000000)) - 分数形式
            # 格式3 (PIL IFDRational): (IFDRational(26,1), IFDRational(34,1), IFDRational(43660125,1000000)) - IFDRational类型
            
            # 检查第一个元素是否可下标访问（格式2）
            if hasattr(value[0], '__getitem__') and not isinstance(value[0], (str, bytes)):
                # 格式2：分数形式 (分子, 分母)
                d = value[0][0] / value[0][1] if value[0][1] != 0 else 0
                m = value[1][0] / value[1][1] if value[1][1] != 0 else 0
                s = value[2][0] / value[2][1] if value[2][1] != 0 else 0
            else:
                # 格式1和3：直接转换为浮点数（包括IFDRational类型）
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
            
            return d + (m / 60.0) + (s / 3600.0)
        except Exception as e:
            print(f"坐标转换出错: {e}")
            print(f"原始数据: {value}")
            return None

    lat = lon = None

    if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
        lat = _convert_to_degrees(gps_info["GPSLatitude"])
        if lat is not None and gps_info["GPSLatitudeRef"] in ["S", "南"]:
            lat = -lat

    if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
        lon = _convert_to_degrees(gps_info["GPSLongitude"])
        if lon is not None and gps_info["GPSLongitudeRef"] in ["W", "西"]:
            lon = -lon

    return lat, lon, gps_info


def convert_wgs84_to_bd09(lon, lat, ak):
    """
    使用百度地图坐标转换API将WGS84坐标转换为百度坐标系（BD09）
    API文档: http://lbsyun.baidu.com/index.php?title=webapi/guide/changeposition
    
    参数:
        lon: WGS84经度
        lat: WGS84纬度
        ak: 百度地图AK
    返回:
        (bd_lon, bd_lat) 或 (None, None)
    """
    if lon is None or lat is None:
        return None, None
    
    if not ak:
        print("\n⚠️  未配置百度AK，无法进行坐标转换")
        print("   请到 https://lbsyun.baidu.com/apiconsole/key 申请百度地图AK")
        return None, None

    # 坐标转换API
    base_url = "http://api.map.baidu.com/geoconv/v1/"
    params = {
        "coords": f"{lon},{lat}",
        "from": "1",  # 源坐标类型：1代表WGS84（GPS坐标）
        "to": "5",    # 目标坐标类型：5代表百度坐标（BD09）
        "ak": ak,
        "output": "json"
    }
    
    url = base_url + "?" + parse.urlencode(params)
    print(f"\n📍 步骤1: 坐标转换（WGS84 -> BD09）")
    print(f"   原始坐标(WGS84): 经度={lon:.6f}, 纬度={lat:.6f}")
    
    try:
        with request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        obj = json.loads(data)
        
        if obj.get("status") == 0:
            result = obj.get("result", [])
            if result and len(result) > 0:
                bd_lon = result[0]["x"]
                bd_lat = result[0]["y"]
                print(f"   转换后坐标(BD09): 经度={bd_lon:.6f}, 纬度={bd_lat:.6f}")
                return bd_lon, bd_lat
            else:
                print(f"   ❌ 转换失败: 返回结果为空")
                return None, None
        else:
            print(f"   ❌ 转换失败: {obj.get('message', '未知错误')}")
            return None, None
    except Exception as e:
        print(f"   ❌ 调用坐标转换API出错: {e}")
        return None, None


def reverse_geocode_baidu(bd_lon, bd_lat, ak):
    """
    使用百度地图逆地理编码API查询地址
    API文档: https://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-geocoding
    
    参数:
        bd_lon: 百度坐标系经度
        bd_lat: 百度坐标系纬度
        ak: 百度地图AK
    """
    if bd_lon is None or bd_lat is None:
        print("\n❌ 无法进行逆地理编码：坐标为空")
        return
    
    if not ak:
        print("\n⚠️  未配置百度AK，无法查询地址")
        return

    # 逆地理编码API
    base_url = "http://api.map.baidu.com/reverse_geocoding/v3/"
    params = {
        "ak": ak,
        "output": "json",
        "coordtype": "bd09ll",  # 百度坐标系
        "location": f"{bd_lat},{bd_lon}"  # 注意：百度API要求格式是"纬度,经度"
    }
    
    url = base_url + "?" + parse.urlencode(params)
    print(f"\n📍 步骤2: 逆地理编码查询地址")
    
    # 生成百度地图网页链接（供浏览器查看）
    baidu_map_url = f"https://api.map.baidu.com/marker?location={bd_lat},{bd_lon}&title=照片拍摄位置&content=&output=html&src=webapp.baidu.openAPIdemo"
    print(f"   📌 在浏览器中查看位置: {baidu_map_url}")
    
    try:
        with request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        obj = json.loads(data)
        
        if obj.get("status") == 0:
            result = obj.get("result", {})
            formatted_address = result.get("formatted_address", "")
            addressComponent = result.get("addressComponent", {})
            
            print(f"\n✅ 查询成功！")
            print(f"   完整地址: {formatted_address}")
            print(f"\n   详细信息:")
            print(f"   - 省份: {addressComponent.get('province', '')}")
            print(f"   - 城市: {addressComponent.get('city', '')}")
            print(f"   - 区县: {addressComponent.get('district', '')}")
            print(f"   - 街道: {addressComponent.get('street', '')}")
            print(f"   - 门牌号: {addressComponent.get('street_number', '')}")
            
            # 周边POI信息
            pois = result.get("pois", [])
            if pois:
                print(f"\n   📍 附近地标:")
                for i, poi in enumerate(pois[:3], 1):  # 只显示前3个
                    print(f"      {i}. {poi.get('name', '')} (距离约{poi.get('distance', '')}米)")
        else:
            print(f"   ❌ 查询失败: status={obj.get('status')}, message={obj.get('message', '未知错误')}")
    except Exception as e:
        print(f"   ❌ 调用逆地理编码API出错: {e}")


def main():
    print("=" * 70)
    print("📷 照片GPS信息读取工具（百度地图版）")
    print("=" * 70)
    
    # 获取照片路径
    if len(sys.argv) > 1:
        photo_path = sys.argv[1]
    else:
        photo_path = DEFAULT_PHOTO_PATH
    
    print(f"\n📁 正在读取图片: {photo_path}")
    
    # 读取EXIF信息
    exif = get_exif_data(photo_path)
    if not exif:
        print("❌ 这张图片没有任何 EXIF 信息（可能是经过压缩/处理丢失了元数据）")
        return
    
    # 提取GPS信息
    lat, lon, gps_info = get_gps_info(exif)
    
    if lat is None or lon is None:
        print("❌ EXIF 中没有 GPS 信息")
        print("\n💡 提示: 请确保照片是在开启GPS定位的情况下拍摄的")
        return
    
    print(f"\n📊 原始 GPS 信息 (WGS84坐标系):")
    for k, v in gps_info.items():
        print(f"   {k}: {v}")
    
    # 坐标转换和地址查询
    if BAIDU_AK:
        # 步骤1: 坐标转换
        bd_lon, bd_lat = convert_wgs84_to_bd09(lon, lat, BAIDU_AK)
        
        # 步骤2: 逆地理编码
        if bd_lon and bd_lat:
            reverse_geocode_baidu(bd_lon, bd_lat, BAIDU_AK)
        else:
            print("\n❌ 坐标转换失败，无法查询地址")
    else:
        print("\n" + "=" * 70)
        print("⚠️  未配置百度地图AK，无法进行坐标转换和地址查询")
        print("=" * 70)
        print("\n📝 配置步骤:")
        print("   1. 访问百度地图开放平台: https://lbsyun.baidu.com/")
        print("   2. 注册/登录账号")
        print("   3. 进入控制台 -> 应用管理 -> 创建应用")
        print("   4. 获取AK（访问应用密钥）")
        print("   5. 在脚本中设置: BAIDU_AK = '你的AK'")
        print("\n💡 需要启用的服务:")
        print("   - 坐标转换服务")
        print("   - 逆地理编码服务")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
