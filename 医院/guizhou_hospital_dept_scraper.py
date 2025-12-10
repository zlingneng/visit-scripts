#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贵州省医院科室信息抓取脚本
抓取贵州省所有医院的科室信息，包括医院名称、等级、科室名称、医生数量和链接
"""

import requests
import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re
from urllib.parse import urljoin

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('guizhou_hospital_dept_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GuizhouHospitalDeptScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.hospitals_data = []
        self.departments_data = []
        
    def get_page(self, url, max_retries=3):
        """获取页面内容"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except Exception as e:
                logger.warning(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {url}, 错误: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    logger.error(f"最终获取页面失败: {url}")
                    return None
    
    def get_guizhou_hospitals(self):
        """从网站动态获取贵州省所有医院列表（包含城市信息）"""
        logger.info("开始从网站动态获取贵州省医院列表...")
        
        try:
            url = "https://www.haodf.com/hospital/list-52.html"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            hospitals = []
            
            # 查找所有城市标题
            city_titles = soup.find_all('div', class_='m_title_green')
            
            for city_title in city_titles:
                city_name = city_title.get_text(strip=True)
                logger.info(f"正在处理城市: {city_name}")
                
                # 查找紧跟在城市标题后面的医院列表
                hospital_list = city_title.find_next_sibling('div', class_='m_ctt_green')
                if not hospital_list:
                    # 如果没有找到兄弟节点，尝试查找父节点下的医院列表
                    parent = city_title.parent
                    if parent:
                        hospital_list = parent.find('div', class_='m_ctt_green')
                
                if not hospital_list:
                    logger.info(f"  未找到 {city_name} 的医院列表")
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
                        hospital_level = '未知'
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
                        
                        hospital_info = {
                            'name': hospital_name,
                            'city': city_name,
                            'level': hospital_level,
                            'url': hospital_url
                        }
                        
                        hospitals.append(hospital_info)
                        city_hospital_count += 1
                        logger.info(f"  - {hospital_name} ({hospital_level})")
                
                logger.info(f"  {city_name} 共找到 {city_hospital_count} 家医院")
            
            logger.info(f"共获取到 {len(hospitals)} 家医院")
            return hospitals
            
        except Exception as e:
            logger.error(f"获取医院列表时出错: {e}")
            return []
    
    def get_hospital_departments(self, hospital_url, hospital_name, city, hospital_level):
        """获取医院的科室列表"""
        # 构造科室列表页面URL
        hospital_id = re.search(r'/hospital/(\d+)\.html', hospital_url)
        if not hospital_id:
            logger.warning(f"无法从URL中提取医院ID: {hospital_url}")
            return []
        
        dept_url = f"https://www.haodf.com/hospital/{hospital_id.group(1)}/keshi/list.html"
        logger.info(f"正在获取 {hospital_name} 的科室列表: {dept_url}")
        html = self.get_page(dept_url)
        if not html:
            logger.warning(f"无法获取科室页面: {dept_url}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        departments = []
        
        # 查找科室列表容器
        dept_container = soup.find('div', class_='hos-keshi')
        if not dept_container:
            logger.warning(f"未找到科室列表容器: {dept_url}")
            return []
        
        # 查找所有科室大类
        dept_categories = dept_container.find_all('div', class_='item-wrap')
        logger.info(f"找到 {len(dept_categories)} 个科室大类")
        
        # 处理每个科室大类
        for category in dept_categories:
            # 获取科室大类名称
            category_name_elem = category.find('h3', class_='keshi-name-showall')
            category_name = category_name_elem.get_text(strip=True) if category_name_elem else "未知科室"
            
            # 查找该大类下的所有科室
            dept_links = category.find_all('a', class_='faculty-item')
            
            # 处理该大类下的所有科室
            for link in dept_links:
                try:
                    # 从链接中提取科室名称
                    dept_name = ''
                    name_div = link.find('div', class_='name-txt')
                    if name_div:
                        dept_name = name_div.get_text(strip=True)
                    
                    if not dept_name:
                        continue
                        
                    dept_href = link.get('href')
                    if dept_href:
                        dept_url_full = urljoin(dept_url, dept_href)
                        
                        # 提取医生数量
                        doctor_count = 0
                        count_div = link.find('div', class_='count')
                        if count_div:
                            count_text = count_div.get_text(strip=True)
                            # 提取数字
                            count_match = re.search(r'(\d+)', count_text)
                            if count_match:
                                doctor_count = int(count_match.group(1))
                        
                        # 添加科室信息到列表
                        department_info = {
                            '医院名称': hospital_name,
                            '所属城市': city,
                            '医院等级': hospital_level,
                            '科室名称': dept_name,
                            '医生数量': doctor_count,
                            '科室链接': dept_url_full
                        }
                        
                        departments.append(department_info)
                        logger.info(f"发现科室: {hospital_name} - {category_name} - {dept_name} ({doctor_count}位医生)")
                        
                except Exception as e:
                    logger.error(f"解析科室信息时出错: {e}")
                    continue
        
        # 如果没有找到按大类组织的科室，尝试原来的解析方法作为备选
        if not departments:
            logger.info("未找到按大类组织的科室，尝试备选解析方法")
            # 查找带有faculty-item类的链接
            dept_links = soup.find_all('a', class_='faculty-item')
            logger.info(f"找到 {len(dept_links)} 个科室链接")
            
            # 处理所有科室
            for link in dept_links:
                try:
                    # 从链接中提取科室名称
                    dept_name = ''
                    name_div = link.find('div', class_='name-txt')
                    if name_div:
                        dept_name = name_div.get_text(strip=True)
                    
                    if not dept_name:
                        continue
                        
                    dept_href = link.get('href')
                    if dept_href:
                        dept_url_full = urljoin(dept_url, dept_href)
                        
                        # 提取医生数量
                        doctor_count = 0
                        count_div = link.find('div', class_='count')
                        if count_div:
                            count_text = count_div.get_text(strip=True)
                            # 提取数字
                            count_match = re.search(r'(\d+)', count_text)
                            if count_match:
                                doctor_count = int(count_match.group(1))
                        
                        # 添加科室信息到列表
                        department_info = {
                            '医院名称': hospital_name,
                            '所属城市': city,
                            '医院等级': hospital_level,
                            '科室名称': dept_name,
                            '医生数量': doctor_count,
                            '科室链接': dept_url_full
                        }
                        
                        departments.append(department_info)
                        logger.info(f"发现科室: {hospital_name} - {dept_name} ({doctor_count}位医生)")
                        
                except Exception as e:
                    logger.error(f"解析科室信息时出错: {e}")
                    continue
        
        logger.info(f"总共获取到 {len(departments)} 个科室")
        return departments
    
    def scrape_all_hospitals(self):
        """抓取所有医院的科室信息"""
        logger.info("开始抓取贵州省医院科室信息...")
        
        # 获取医院列表
        hospitals = self.get_guizhou_hospitals()
        if not hospitals:
            logger.error("未能获取医院列表")
            return
        
        total_hospitals = len(hospitals)
        
        for i, hospital in enumerate(hospitals, 1):
            logger.info(f"正在处理医院 {i}/{total_hospitals}: {hospital['name']}")
            
            try:
                # 记录医院信息
                self.hospitals_data.append({
                    '医院名称': hospital['name'],
                    '所属城市': hospital['city'],
                    '医院等级': hospital['level'],
                    '医院链接': hospital['url']
                })
                
                # 获取医院科室
                departments = self.get_hospital_departments(
                    hospital['url'], hospital['name'], hospital['city'], hospital['level']
                )
                
                self.departments_data.extend(departments)
                
                # 避免请求过于频繁，设置随机间隔2-4秒
                import random
                sleep_time = random.uniform(2, 4)
                logger.info(f"等待 {sleep_time:.2f} 秒后继续...")
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"处理医院 {hospital['name']} 时出错: {e}")
                continue
        
        logger.info(f"抓取完成！共获取 {len(self.departments_data)} 个科室信息")
    
    def save_to_excel(self):
        """保存数据到Excel文件"""
        if not self.departments_data:
            logger.warning("没有数据可保存")
            return
        
        # 创建DataFrame
        df = pd.DataFrame(self.departments_data)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'贵州省医院科室信息_{timestamp}.xlsx'
        
        try:
            # 保存到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 保存科室数据
                df.to_excel(writer, sheet_name='科室信息', index=False)
                
                # 创建统计信息
                stats_data = [
                    ['统计项目', '数量'],
                    ['总科室数', len(df)],
                    ['医院数', df['医院名称'].nunique()],
                    ['城市数', df['所属城市'].nunique()],
                    ['总医生数', df['医生数量'].sum()]
                ]
                
                stats_df = pd.DataFrame(stats_data[1:], columns=stats_data[0])
                stats_df.to_excel(writer, sheet_name='统计信息', index=False)
                
                # 按医院统计科室数
                hospital_stats = df.groupby('医院名称').size().reset_index(name='科室数量')
                hospital_stats.to_excel(writer, sheet_name='医院科室统计', index=False)
                
                # 按城市统计
                city_stats = df.groupby('所属城市').size().reset_index(name='科室数量')
                city_stats.to_excel(writer, sheet_name='城市科室统计', index=False)
            
            logger.info(f"数据已保存到: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            return None

def main():
    """主函数"""
    scraper = GuizhouHospitalDeptScraper()
    
    # 开始抓取
    scraper.scrape_all_hospitals()
    
    # 保存到Excel
    filename = scraper.save_to_excel()
    
    if filename:
        print(f"\n抓取完成！数据已保存到 {filename}")
        print(f"共获取 {len(scraper.departments_data)} 个科室信息")
    else:
        print("\n抓取失败！")

if __name__ == "__main__":
    main()