#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
好大夫在线贵州省医院信息抓取脚本
抓取页面：https://www.haodf.com/hospital/list-52.html
提取：城市、医院名称、类型、URL信息
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time

# 配置参数
URL = "https://www.haodf.com/hospital/list-52.html"
OUTPUT_FILE = f"贵州省医院列表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_page_content(url):
    """获取页面内容"""
    try:
        print(f"正在获取页面内容: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        # 自动检测编码
        response.encoding = response.apparent_encoding or 'utf-8'
        return response.text
    except Exception as e:
        print(f"获取页面失败: {e}")
        return None

def parse_hospital_info(html_content):
    """解析医院信息"""
    soup = BeautifulSoup(html_content, 'html.parser')
    hospitals = []
    
    # 查找所有城市标题
    city_titles = soup.find_all('div', class_='m_title_green')
    
    for city_title in city_titles:
        city_name = city_title.get_text(strip=True)
        print(f"正在处理城市: {city_name}")
        
        # 查找紧跟在城市标题后面的医院列表
        hospital_list = city_title.find_next_sibling('div', class_='m_ctt_green')
        if not hospital_list:
            # 如果没有找到兄弟节点，尝试查找父节点下的医院列表
            parent = city_title.parent
            if parent:
                hospital_list = parent.find('div', class_='m_ctt_green')
        
        if not hospital_list:
            print(f"  未找到 {city_name} 的医院列表")
            continue
            
        # 查找所有医院链接
        hospital_links = hospital_list.find_all('li')
        city_hospital_count = 0
        
        for li in hospital_links:
            link = li.find('a')
            span = li.find('span')
            
            if link:
                # 提取医院名称和URL
                hospital_name = link.get_text(strip=True)
                hospital_url = link.get('href', '').strip()
                
                # 确保URL是完整的
                if hospital_url and not hospital_url.startswith('http'):
                    hospital_url = 'https://www.haodf.com' + hospital_url
                
                # 提取医院类型信息
                type_text = ''
                hospital_level = ''
                hospital_specialty = ''
                
                if span:
                    type_text = span.get_text(strip=True)
                    # 使用正则表达式提取等级和特色
                    match = re.search(r'\(([^,]+),\s*特色:([^)]+)\)', type_text)
                    if match:
                        hospital_level = match.group(1).strip()
                        hospital_specialty = match.group(2).strip()
                    else:
                        # 尝试其他格式
                        match2 = re.search(r'\(([^)]+)\)', type_text)
                        if match2:
                            content = match2.group(1).strip()
                            if ',' in content:
                                parts = content.split(',')
                                hospital_level = parts[0].strip()
                                if len(parts) > 1 and '特色:' in parts[1]:
                                    hospital_specialty = parts[1].replace('特色:', '').strip()
                            else:
                                hospital_level = content
                
                hospitals.append({
                    '城市': city_name,
                    '医院名称': hospital_name,
                    '医院等级': hospital_level,
                    '特色科室': hospital_specialty,
                    '医院URL': hospital_url,
                    '原始类型信息': type_text
                })
                
                city_hospital_count += 1
                print(f"  - {hospital_name} ({hospital_level}, {hospital_specialty})")
        
        print(f"  {city_name} 共找到 {city_hospital_count} 家医院")
    
    return hospitals

def save_to_excel(hospitals, filename):
    """保存到Excel文件"""
    try:
        df = pd.DataFrame(hospitals)
        
        # 创建Excel写入器
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 保存主数据
            df.to_excel(writer, sheet_name='医院列表', index=False)
            
            # 创建统计信息
            stats = {
                '统计项目': ['总医院数', '城市数', '三甲医院数', '二甲医院数', '其他等级医院数'],
                '数量': [
                    len(df),
                    df['城市'].nunique(),
                    len(df[df['医院等级'] == '三甲']),
                    len(df[df['医院等级'] == '二甲']),
                    len(df[~df['医院等级'].isin(['三甲', '二甲'])])
                ]
            }
            stats_df = pd.DataFrame(stats)
            stats_df.to_excel(writer, sheet_name='统计信息', index=False)
            
            # 按城市分组统计
            city_stats = df.groupby('城市').size().reset_index(name='医院数量')
            city_stats.to_excel(writer, sheet_name='城市统计', index=False)
        
        print(f"\n数据已保存到: {filename}")
        print(f"共抓取到 {len(hospitals)} 家医院")
        print(f"涵盖 {df['城市'].nunique()} 个城市")
        
        return True
    except Exception as e:
        print(f"保存Excel文件失败: {e}")
        return False

def main():
    """主函数"""
    print("开始抓取贵州省医院信息...")
    print("=" * 50)
    
    # 获取页面内容
    html_content = fetch_page_content(URL)
    if not html_content:
        print("无法获取页面内容，程序退出")
        return
    
    # 解析医院信息
    hospitals = parse_hospital_info(html_content)
    
    if not hospitals:
        print("未找到医院信息")
        return
    
    # 保存到Excel
    success = save_to_excel(hospitals, OUTPUT_FILE)
    
    if success:
        print("\n抓取完成！")
        print(f"输出文件: {OUTPUT_FILE}")
    else:
        print("\n抓取失败！")

if __name__ == "__main__":
    main()