#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Excel文件读取医院科室信息并抓取医生数据的脚本
基于Excel文件中的'医院科室筛选后'标签页中的医院和科室信息抓取医生数据
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
import random

# 配置区域 - 请根据实际情况修改以下配置
EXCEL_FILE_PATH = "/Users/a000/Documents/济生/医院拜访25/贵州省医院科室信息_20251105-3.xlsx"
TARGET_SHEET_NAME = "医院科室筛选后 其他"

# 获取输入文件所在目录
INPUT_DIR = os.path.dirname(EXCEL_FILE_PATH)
# 输出文件放在输入文件同一目录下
OUTPUT_FILE_NAME = os.path.join(INPUT_DIR, "贵州省医院医生信息_{}.xlsx").format(datetime.now().strftime("%Y%m%d_%H%M%S"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('doctor_scraper_from_excel.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DoctorScraperFromExcel:
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
        
        self.doctors_data = []
        self.processed_departments = []
        
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
    
    def read_hospitals_from_excel(self):
        """从Excel文件读取医院科室信息"""
        logger.info(f"正在从Excel文件读取医院科室信息: {EXCEL_FILE_PATH}")
        logger.info(f"目标标签页: {TARGET_SHEET_NAME}")
        
        # 检查文件是否存在
        if not os.path.exists(EXCEL_FILE_PATH):
            logger.error(f"错误: 文件不存在: {EXCEL_FILE_PATH}")
            return []
        
        try:
            # 读取Excel文件中的医院科室信息
            df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=TARGET_SHEET_NAME)
            
            # 提取医院科室信息
            hospitals = []
            for _, row in df.iterrows():
                hospital_info = {
                    'name': row['医院名称'],
                    'city': row['所属城市'],
                    'level': row['医院等级'],
                    'department': row['科室名称'],
                    'dept_url': row['科室链接'],
                    'doctor_count': row['医生数量'] if '医生数量' in row else 0
                }
                hospitals.append(hospital_info)
            
            logger.info(f"成功读取 {len(hospitals)} 条医院科室记录")
            return hospitals
            
        except Exception as e:
            logger.error(f"读取Excel文件时出错: {e}")
            return []
    
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
    
    def scrape_doctors_from_excel(self):
        """根据Excel中的医院科室信息抓取医生数据"""
        logger.info("开始从Excel文件中的医院科室信息抓取医生数据...")
        
        # 从Excel读取医院科室信息
        hospitals_depts = self.read_hospitals_from_excel()
        if not hospitals_depts:
            logger.error("未能读取医院科室信息")
            return
        
        total_records = len(hospitals_depts)
        logger.info(f"共需处理 {total_records} 条医院科室记录")
        
        for i, record in enumerate(hospitals_depts, 1):
            hospital_name = record['name']
            city = record['city']
            hospital_level = record['level']
            dept_name = record['department']
            dept_url = record['dept_url']
            doctor_count = record['doctor_count'] if 'doctor_count' in record else 0
            
            logger.info(f"正在处理 [{i}/{total_records}]: {hospital_name} - {dept_name}")
            
            try:
                # 检查是否已经处理过相同的科室（避免重复抓取）
                dept_identifier = f"{hospital_name}_{dept_name}"
                if dept_identifier in self.processed_departments:
                    logger.info(f"科室 {dept_name} 已处理过，跳过")
                    continue
                
                # 获取科室医生信息
                doctors = self.get_department_doctors(
                    dept_url, dept_name, hospital_name, city, hospital_level, doctor_count
                )
                
                self.doctors_data.extend(doctors)
                self.processed_departments.append(dept_identifier)
                
                logger.info(f"科室 {dept_name} 抓取完成，共获取 {len(doctors)} 位医生")
                
                # 避免请求过于频繁
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logger.error(f"处理 {hospital_name} - {dept_name} 时出错: {e}")
                continue
        
        logger.info(f"抓取完成！共获取 {len(self.doctors_data)} 位医生信息")
    
    def save_to_excel(self):
        """保存数据到Excel文件"""
        if not self.doctors_data:
            logger.warning("没有数据需要保存")
            return
        
        logger.info(f"正在保存数据到Excel文件: {OUTPUT_FILE_NAME}")
        
        try:
            # 创建DataFrame
            df = pd.DataFrame(self.doctors_data)
            
            # 保存到Excel文件
            df.to_excel(OUTPUT_FILE_NAME, index=False, engine='openpyxl')
            logger.info(f"数据已保存到 {OUTPUT_FILE_NAME}")
            
        except Exception as e:
            logger.error(f"保存文件时出错: {e}")

def main():
    """主函数"""
    scraper = DoctorScraperFromExcel()
    scraper.scrape_doctors_from_excel()
    scraper.save_to_excel()

if __name__ == "__main__":
    main()