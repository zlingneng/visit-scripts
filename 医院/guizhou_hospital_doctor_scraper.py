#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贵州省医院医生信息抓取脚本
目标科室：呼吸科、儿科、妇科、泌尿科、肾内科、中医科
"""

import requests
import time
import json
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import os
from urllib.parse import urljoin, urlparse
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('guizhou_doctor_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GuizhouHospitalScraper:
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
        
        # 目标科室关键词 - 使用更灵活的匹配
        self.target_keywords = [
            '呼吸',  # 匹配呼吸科、呼吸内科、呼吸与危重症医学科等
            '儿科', '儿内科', #'小儿', '新生儿',  # 匹配各种儿科
            '妇科', '妇产科', #'产科',  # 匹配妇科相关
            '泌尿',  # 匹配泌尿科、泌尿外科等
            '肾脏', '肾内科', '肾病',  # 匹配肾脏相关科室
            '中医' ,  # 匹配中医科相关
            '全科'
        ]
        
        self.doctors_data = []
        self.hospitals_data = []
        
    def get_page(self, url, max_retries=3):
        """获取页面内容"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'  # 好大夫网站使用utf-8编码
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
            url = "https://www.haodf.com/hospital/list-35.html"
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
            
            # 按城市统计
            city_stats = {}
            for hospital in hospitals:
                city = hospital['city']
                if city not in city_stats:
                    city_stats[city] = 0
                city_stats[city] += 1
            
            logger.info("各城市医院数量统计:")
            for city, count in city_stats.items():
                logger.info(f"  {city}: {count} 家")
            
            return hospitals
            
        except Exception as e:
            logger.error(f"获取医院列表时出错: {e}")
            return []
    
    def get_hospital_departments(self, hospital_url):
        """获取医院的科室列表"""
        # 构造科室列表页面URL
        hospital_id = re.search(r'/hospital/(\d+)\.html', hospital_url)
        if not hospital_id:
            logger.warning(f"无法从URL中提取医院ID: {hospital_url}")
            return []
        
        dept_url = f"https://www.haodf.com/hospital/{hospital_id.group(1)}/keshi/list.html"
        logger.info(f"正在获取科室列表: {dept_url}")
        html = self.get_page(dept_url)
        if not html:
            logger.warning(f"无法获取科室页面: {dept_url}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        departments = []
        
        # 根据实际HTML结构查找科室链接
        # 方法1: 查找带有faculty-item类的链接（最准确）
        dept_links = soup.find_all('a', class_='faculty-item')
        logger.info(f"方法1找到 {len(dept_links)} 个faculty-item链接")
        
        # 方法2: 如果没有找到，查找包含医院ID的科室链接
        if not dept_links:
            hospital_id_str = hospital_id.group(1)
            dept_links = soup.find_all('a', href=re.compile(f'/hospital/{hospital_id_str}/keshi/'))
            logger.info(f"方法2找到 {len(dept_links)} 个医院ID链接")
        
        # 方法3: 如果还没有找到，查找包含/keshi/的链接（备用）
        if not dept_links:
            dept_links = soup.find_all('a', href=re.compile(r'/keshi/'))
            logger.info(f"方法3找到 {len(dept_links)} 个keshi链接")
        
        logger.info(f"总共找到 {len(dept_links)} 个科室链接")
        
        for i, link in enumerate(dept_links[:5]):  # 只调试前5个
            # 从链接中提取科室名称
            dept_name = ''
            name_div = link.find('div', class_='name-txt')
            if name_div:
                dept_name = name_div.get_text(strip=True)
                logger.info(f"科室{i+1}: 通过name-txt找到: {dept_name}")
            else:
                # 尝试其他可能的类名
                name_span = link.find('span', class_='name')
                if name_span:
                    dept_name = name_span.get_text(strip=True)
                    logger.info(f"科室{i+1}: 通过span.name找到: {dept_name}")
                else:
                    dept_name = link.get_text(strip=True)
                    logger.info(f"科室{i+1}: 通过链接文本找到: {dept_name}")
            
            if not dept_name:
                logger.warning(f"科室{i+1}: 未找到科室名称")
                continue
            
            # 检查是否匹配目标关键词
            matched_keywords = [keyword for keyword in self.target_keywords if keyword in dept_name]
            if matched_keywords:
                logger.info(f"科室{i+1}: {dept_name} 匹配关键词: {matched_keywords}")
            else:
                logger.info(f"科室{i+1}: {dept_name} 不匹配任何关键词")
        
        # 现在处理所有科室
        for link in dept_links:
            # 从链接中提取科室名称
            dept_name = ''
            name_div = link.find('div', class_='name-txt')
            if name_div:
                dept_name = name_div.get_text(strip=True)
            else:
                # 尝试其他可能的类名
                name_span = link.find('span', class_='name')
                if name_span:
                    dept_name = name_span.get_text(strip=True)
                else:
                    dept_name = link.get_text(strip=True)
            
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
                
                # 检查是否是目标科室
                if any(keyword in dept_name for keyword in self.target_keywords):
                    departments.append({
                        'name': dept_name,
                        'url': dept_url_full,
                        'doctor_count': doctor_count
                    })
                    logger.info(f"发现目标科室: {dept_name} (医生数量: {doctor_count})")
        
        return departments
    
    def get_department_doctors(self, dept_url, dept_name, hospital_name, city, hospital_level='未知', doctor_count=0):
        """获取科室的医生列表，支持分页"""
        doctors = []
        
        # 计算需要抓取的页数（每页20个医生）
        total_pages = max(1, (doctor_count + 19) // 20) if doctor_count > 0 else 5  # 默认最多5页
        
        for page in range(1, total_pages + 1):
            # 构造分页URL
            if '/keshi/' in dept_url and not dept_url.endswith('/tuijian.html'):
                if dept_url.endswith('.html'):
                    base_url = dept_url.replace('.html', '/tuijian.html')
                else:
                    base_url = dept_url + '/tuijian.html'
            else:
                base_url = dept_url
            
            # 添加分页参数
            if page == 1:
                page_url = f"{base_url}?type=keshi"
            else:
                page_url = f"{base_url}?type=keshi&p={page}"
            
            logger.info(f"抓取第{page}页医生信息: {page_url}")
            
            html = self.get_page(page_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            page_doctors = []

            # 根据实际HTML结构查找医生信息
            # 查找医生列表容器
            doctor_list = soup.find('ul', class_='doc-list')
            if doctor_list:
                doctor_items = doctor_list.find_all('li', class_='item')
                
                for item in doctor_items:
                    try:
                        # 查找医生链接
                        doctor_link = item.find('a', class_='item-bd')
                        if not doctor_link:
                            continue
                        
                        doctor_url = urljoin(dept_url, doctor_link.get('href', ''))
                        
                        # 提取医生姓名
                        name_span = item.find('span', class_='name')
                        raw_name = name_span.get_text(strip=True) if name_span else ''
                        
                        # 清洗医生姓名，移除科室前缀
                        doctor_name = self.clean_doctor_name(raw_name, dept_name)
                        
                        # 提取职称
                        grade_span = item.find('span', class_='grade')
                        title = grade_span.get_text(strip=True) if grade_span else ''
                        
                        # 提取学历/教授信息
                        edu_grade_span = item.find('span', class_='edu-grade')
                        if edu_grade_span:
                            edu_grade = edu_grade_span.get_text(strip=True)
                            if edu_grade:
                                title = f"{title} {edu_grade}" if title else edu_grade
                        
                        # 提取擅长领域
                        goodat_p = item.find('p', class_='goodat')
                        specialty = ''
                        if goodat_p:
                            specialty_text = goodat_p.get_text(strip=True)
                            if specialty_text.startswith('擅长：'):
                                specialty = specialty_text[3:]
                            else:
                                specialty = specialty_text
                        
                        if doctor_name and len(doctor_name) >= 2:
                            doctor_info = {
                                '医院名称': hospital_name,
                                '所属城市': city,
                                '医院等级': hospital_level,
                                '科室名称': dept_name,
                                '医生姓名': doctor_name,
                                '职称': title,
                                '擅长领域': specialty,
                                '医生链接': doctor_url,
                                '抓取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            
                            page_doctors.append(doctor_info)
                            logger.info(f"发现医生: {hospital_name} - {dept_name} - {doctor_name}")
                            
                    except Exception as e:
                        logger.error(f"解析医生信息时出错: {e}")
                        continue
            

            
            # 将当前页的医生添加到总列表
            doctors.extend(page_doctors)
            
            # 如果当前页没有医生，可能已经到了最后一页
            if not page_doctors:
                break
                
        return doctors
    
    def clean_doctor_name(self, raw_name, dept_name):
        """清洗医生姓名，移除科室前缀和其他无关信息"""
        # 移除科室名称前缀
        name = raw_name
        if dept_name in name:
            name = name.replace(dept_name, '')
        
        # 移除常见的职称后缀
        title_patterns = [
            r'主任医师.*?$', r'副主任医师.*?$', r'主治医师.*?$', r'住院医师.*?$',
            r'教授.*?$', r'副教授.*?$', r'讲师.*?$',
            r'科主任.*?$', r'副主任.*?$', r'主任.*?$',
            r'\d+\.\d+$', r'\d+$'  # 移除评分数字
        ]
        
        for pattern in title_patterns:
            name = re.sub(pattern, '', name)
        
        # 清理空格和特殊字符
        name = re.sub(r'\s+', '', name)
        name = name.strip()
        
        return name if name else raw_name
    
    def scrape_all_hospitals(self):
        """抓取所有医院的目标科室医生信息"""
        logger.info("开始抓取贵州省医院医生信息...")
        
        # 获取医院列表
        hospitals = self.get_guizhou_hospitals()
        if not hospitals:
            logger.error("未能获取医院列表")
            return
        
        total_hospitals = len(hospitals)
        
        for i, hospital in enumerate(hospitals, 1):
            logger.info(f"正在处理医院 {i}/{total_hospitals}: {hospital['name']}")
            
            try:
                # 获取医院科室
                departments = self.get_hospital_departments(hospital['url'])
                
                if not departments:
                    logger.info(f"医院 {hospital['name']} 没有目标科室")
                    continue
                
                # 记录医院信息
                self.hospitals_data.append({
                    '医院名称': hospital['name'],
                    '所属城市': hospital['city'],
                    '医院等级': hospital['level'],
                    '医院链接': hospital['url'],
                    '目标科室数量': len(departments),
                    '科室列表': ', '.join([d['name'] for d in departments])
                })
                
                # 获取每个科室的医生
                for dept in departments:
                    logger.info(f"正在处理科室: {dept['name']}")
                    
                    doctors = self.get_department_doctors(
                        dept['url'], dept['name'], hospital['name'], hospital['city'], hospital['level'], dept['doctor_count']
                    )
                    
                    self.doctors_data.extend(doctors)
                    
                    # 避免请求过于频繁
                    time.sleep(1)
                
                # 每处理完一个医院休息一下
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"处理医院 {hospital['name']} 时出错: {e}")
                continue
        
        logger.info(f"抓取完成！共获取 {len(self.doctors_data)} 位医生信息")
    
    def save_to_excel(self):
        """保存数据到Excel文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存医生数据
        if self.doctors_data:
            doctors_df = pd.DataFrame(self.doctors_data)
            doctors_file = f'贵州省医院医生信息_{timestamp}.xlsx'
            
            with pd.ExcelWriter(doctors_file, engine='openpyxl') as writer:
                doctors_df.to_excel(writer, sheet_name='医生信息', index=False)
                
                # 按医院分组统计
                hospital_stats = doctors_df.groupby('医院名称').agg({
                    '医生姓名': 'count',
                    '科室名称': lambda x: ', '.join(x.unique())
                }).rename(columns={'医生姓名': '医生数量', '科室名称': '科室列表'})
                hospital_stats.to_excel(writer, sheet_name='医院统计')
                
                # 按科室分组统计
                dept_stats = doctors_df.groupby('科室名称').agg({
                    '医生姓名': 'count',
                    '医院名称': lambda x: ', '.join(x.unique())
                }).rename(columns={'医生姓名': '医生数量', '医院名称': '医院列表'})
                dept_stats.to_excel(writer, sheet_name='科室统计')
            
            logger.info(f"医生数据已保存到: {doctors_file}")
        
        # 保存医院数据
        if self.hospitals_data:
            hospitals_df = pd.DataFrame(self.hospitals_data)
            hospitals_file = f'贵州省医院列表_{timestamp}.xlsx'
            hospitals_df.to_excel(hospitals_file, index=False)
            logger.info(f"医院数据已保存到: {hospitals_file}")
    
    def run(self):
        """运行爬虫"""
        try:
            self.scrape_all_hospitals()
            self.save_to_excel()
            
            # 打印统计信息
            logger.info("=== 抓取统计 ===")
            logger.info(f"总医院数: {len(self.hospitals_data)}")
            logger.info(f"总医生数: {len(self.doctors_data)}")
            
            if self.doctors_data:
                df = pd.DataFrame(self.doctors_data)
                logger.info("按科室统计:")
                dept_counts = df['科室名称'].value_counts()
                for dept, count in dept_counts.items():
                    logger.info(f"  {dept}: {count}位医生")
                
        except Exception as e:
            logger.error(f"运行过程中出错: {e}")
            raise

if __name__ == "__main__":
    scraper = GuizhouHospitalScraper()
    scraper.run()