#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import random
from collections import defaultdict
import openpyxl
from openpyxl import Workbook

# 使用 chinese_calendar 包来处理中国节假日
try:
    import chinese_calendar as cc
    CHINESECALENDAR_AVAILABLE = True
except ImportError:
    CHINESECALENDAR_AVAILABLE = False
    print("警告：未安装 chinese_calendar 包，将使用简化的节假日处理")
    print("建议安装：pip install chinesecalendar")

# 配置项将在脚本末尾统一设置

def is_workday(date):
    """判断是否为工作日（可拜访日）
    
    规则：
    - 周一到周六可以拜访
    - 周日不可以拜访
    - 法定节假日不可以拜访（包括调休的周六）
    """
    # 统一的节假日判断逻辑
    # 周日不可拜访
    if date.weekday() == 6:  # 周日
        return False
    
    # 法定节假日不可拜访（根据国务院办公厅2025年放假安排）
    holidays_2025 = [
        # 元旦：1月1日（周三）放假1天
        datetime(2025, 1, 1).date(),
        
        # 春节：1月28日（农历除夕、周二）至2月4日（农历正月初七、周二）放假调休，共8天
        datetime(2025, 1, 28).date(), datetime(2025, 1, 29).date(), datetime(2025, 1, 30).date(),
        datetime(2025, 1, 31).date(), datetime(2025, 2, 1).date(), datetime(2025, 2, 2).date(),
        datetime(2025, 2, 3).date(), datetime(2025, 2, 4).date(),
        
        # 清明节：4月4日（周五）至6日（周日）放假，共3天
        datetime(2025, 4, 4).date(), datetime(2025, 4, 5).date(), datetime(2025, 4, 6).date(),
        
        # 劳动节：5月1日（周四）至5日（周一）放假调休，共5天
        datetime(2025, 5, 1).date(), datetime(2025, 5, 2).date(), datetime(2025, 5, 3).date(),
        datetime(2025, 5, 4).date(), datetime(2025, 5, 5).date(),
        
        # 端午节：5月31日（周六）至6月2日（周一）放假，共3天
        datetime(2025, 5, 31).date(), datetime(2025, 6, 1).date(), datetime(2025, 6, 2).date(),
        
        # 国庆节、中秋节：10月1日（周三）至8日（周三）放假调休，共8天
        datetime(2025, 10, 1).date(), datetime(2025, 10, 2).date(), datetime(2025, 10, 3).date(),
        datetime(2025, 10, 4).date(), datetime(2025, 10, 5).date(), datetime(2025, 10, 6).date(),
        datetime(2025, 10, 7).date(), datetime(2025, 10, 8).date(),
    ]
    # 确保比较的是日期部分
    check_date = date.date() if hasattr(date, 'date') else date
    if check_date in holidays_2025:
        return False
    
    # 其他情况（周一到周六的非节假日）返回 True
    return True

def get_working_days(start_date, end_date):
    """获取可拜访日期（周一到周六，排除法定节假日）"""
    working_days = []
    current_date = start_date
    
    while current_date <= end_date:
        if is_workday(current_date):
            working_days.append(current_date)
        current_date += timedelta(days=1)
    
    return working_days

def read_excel_data(file_path):
    """读取Excel文件的筛选标签页和医院地址标签页"""
    try:
        # 读取导出筛选结果标签页
        df = pd.read_excel(file_path, sheet_name='导出筛选结果')
        print(f"成功读取数据，共{len(df)}条记录")
        print(f"列名：{list(df.columns)}")
        
        # 读取医院地址标签页
        df_addr = pd.read_excel(file_path, sheet_name='医院地址')
        # 重命名列名为标准格式
        df_addr.columns = ['医院名称', '地址']
        print(f"成功读取医院地址数据，共{len(df_addr)}条记录")
        
        return df, df_addr
    except Exception as e:
        print(f"读取Excel文件失败：{e}")
        return None, None

def assign_hospitals_to_visitors(hospitals, visitors, df):
    """为拜访人员分配医院（按照各拜访人分配的医院医生总量差距最小）"""
    hospital_assignment = {visitor: [] for visitor in visitors}
    hospitals_list = list(hospitals)
    
    # 计算每个医院的医生数量
    hospital_doctor_counts = {}
    for hospital in hospitals_list:
        doctor_count = len(df[df['医院名称'] == hospital])
        hospital_doctor_counts[hospital] = doctor_count
    
    # 按医生数量从多到少排序医院
    sorted_hospitals = sorted(hospital_doctor_counts.items(), key=lambda x: x[1], reverse=True)
    
    # 贪心分配：每次将医院分配给当前医生总数最少的拜访人
    visitor_doctor_counts = {visitor: 0 for visitor in visitors}
    
    for hospital, doctor_count in sorted_hospitals:
        # 找到当前医生总数最少的拜访人
        min_visitor = min(visitor_doctor_counts.keys(), key=lambda v: visitor_doctor_counts[v])
        
        # 分配医院给该拜访人
        hospital_assignment[min_visitor].append(hospital)
        visitor_doctor_counts[min_visitor] += doctor_count
    
    # 打印分配结果
    print("\n=== 医院分配结果 ===")
    for visitor in visitors:
        total_doctors = sum(hospital_doctor_counts[h] for h in hospital_assignment[visitor])
        print(f"{visitor}: {len(hospital_assignment[visitor])}家医院, 共{total_doctors}位医生")
        for hospital in hospital_assignment[visitor]:
            print(f"  - {hospital}: {hospital_doctor_counts[hospital]}位医生")
    
    # 计算差距
    doctor_counts = [sum(hospital_doctor_counts[h] for h in hospital_assignment[v]) for v in visitors]
    max_diff = max(doctor_counts) - min(doctor_counts) if doctor_counts else 0
    print(f"医生总量差距: {max_diff}")
    
    return hospital_assignment

def balance_daily_visits(df, visitors, target_visits):
    """均衡拜访人的拜访量分配"""
    total_doctors = len(df)
    visits_per_person = target_visits // len(visitors)
    
    # 确保总拜访量不超过可用医生数
    if target_visits > total_doctors:
        target_visits = total_doctors
        visits_per_person = target_visits // len(visitors)
    
    visitor_targets = {}
    
    # 尽量平均分配，剩余的分配给第一个拜访人
    for i, visitor in enumerate(visitors):
        if i == 0:  # 第一个拜访人分配剩余的
            visitor_targets[visitor] = visits_per_person + (target_visits % len(visitors))
        else:
            visitor_targets[visitor] = visits_per_person
    
    print(f"拜访量分配: {visitor_targets}")
    return visitor_targets

def select_daily_hospitals(visitor_hospitals, df, doctor_visited, max_hospitals=2):
    """为拜访人每天选择医院（优先选择剩余医生较多的医院）"""
    if len(visitor_hospitals) <= max_hospitals:
        return visitor_hospitals
    
    # 计算每个医院的剩余医生数量
    hospital_remaining_doctors = {}
    for hospital in visitor_hospitals:
        remaining_doctors = df[
            (df['医院名称'] == hospital) & 
            (~df['医生名称'].isin(doctor_visited))
        ]
        hospital_remaining_doctors[hospital] = len(remaining_doctors)
    
    # 按剩余医生数量从多到少排序，选择前max_hospitals个
    sorted_hospitals = sorted(hospital_remaining_doctors.items(), 
                            key=lambda x: x[1], reverse=True)
    selected_hospitals = [hospital for hospital, count in sorted_hospitals[:max_hospitals]]
    
    return selected_hospitals

def calculate_visit_times(visits_today, visitor):
    """计算一天的拜访开始和结束时间"""
    # 每人每天的拜访开始时间为早上八点半到9点间随机
    start_hour = 8
    start_minute = random.randint(30, 59)
    if start_minute == 59:
        start_hour = 9
        start_minute = 0
    
    current_time = datetime.combine(datetime.today().date(), time(start_hour, start_minute))
    
    for i, visit in enumerate(visits_today):
        previous_visit = visits_today[i-1] if i > 0 else None
        
        # 如果不是第一次拜访，需要计算间隔时间
        if previous_visit is not None:
            # 判断是否跨医院
            if visit['医院名称'] != previous_visit['医院名称']:
                # 跨医院：上一个医院的拜访结束时间加上45-60分钟
                travel_time = random.randint(45, 60)
                current_time += timedelta(minutes=travel_time)
            # 判断是否跨科室（同医院不同科室）
            elif visit['科室'] != previous_visit['科室']:
                # 跨科室：上一个科室的拜访结束时间加5-10分钟
                interval_time = random.randint(5, 10)
                current_time += timedelta(minutes=interval_time)
            # 同医院同科室，直接接续（current_time已经是上次拜访结束时间）
        
        # 检查是否跨越午休时间（11:50-13:30）
        # 无论是跨医院、跨科室还是同科室，都需要检查午休时间
        lunch_start = datetime.combine(datetime.today().date(), time(11, 50))
        lunch_end = datetime.combine(datetime.today().date(), time(13, 30))
        
        # 如果当前时间在午休时间段内，顺延到13点30到14点间随机值
        if current_time >= lunch_start and current_time < lunch_end:
            # 顺延到13点30到14点间随机值
            new_start_minute = random.randint(30, 59)
            new_start_hour = 13
            if new_start_minute == 59:
                new_start_hour = 14
                new_start_minute = 0
            current_time = datetime.combine(datetime.today().date(), time(new_start_hour, new_start_minute))
        
        # 设置拜访开始时间
        visit['拜访开始时间'] = current_time.strftime('%H:%M')
        
        # 拜访时长固定为15-30分钟
        visit_duration = random.randint(15, 30)
        end_time = current_time + timedelta(minutes=visit_duration)
        visit['拜访结束时间'] = end_time.strftime('%H:%M')
        
        # 检查拜访开始时间是否超过17:05
        max_start_time = datetime.combine(datetime.today().date(), time(17, 5))
        if current_time > max_start_time:
            # 如果超过最晚开始时间，则不安排这次拜访
            return visits_today[:i]
        
        # 更新下次拜访的开始时间（设为当前拜访的结束时间）
        current_time = end_time
    
    return visits_today

def check_same_surname(doctor_name, existing_doctors):
    """检查医生姓氏是否与已安排的医生相同"""
    if not existing_doctors:
        return False
    
    # 处理医生姓名中的空格
    clean_name = doctor_name.strip() if doctor_name else ''
    doctor_surname = clean_name[0] if clean_name else ''
    
    for existing_doctor in existing_doctors:
        clean_existing = existing_doctor.strip() if existing_doctor else ''
        existing_surname = clean_existing[0] if clean_existing else ''
        if doctor_surname == existing_surname and doctor_surname != '':
            return True
    
    return False

def check_consecutive_hospital_visits(visitor_hospital_history, hospital, current_date_str):
    """检查拜访者是否连续3天及以上拜访同一家医院"""
    if len(visitor_hospital_history) < 2:
        return False  # 历史记录不足2天，不会连续3天
    
    # 获取最近2天的拜访记录
    recent_visits = visitor_hospital_history[-2:]
    
    # 检查最近2天是否都拜访了同一家医院
    if all(visit['hospital'] == hospital for visit in recent_visits):
        return True  # 如果今天再拜访同一家医院，就会连续3天
    
    return False

def greedy_visit_planning(df, df_addr, working_days, visitors, target_visits, daily_visits_range):
    """使用贪心算法制定拜访计划"""
    # 获取所有医院
    hospitals = df['医院名称'].unique()
    
    # 为拜访人员分配医院
    hospital_assignment = assign_hospitals_to_visitors(hospitals, visitors, df)
    
    # 均衡拜访人的拜访量分配
    visitor_targets = balance_daily_visits(df, visitors, target_visits)
    
    visit_plan = []
    doctor_visited = set()  # 记录已拜访的医生
    daily_hospital_dept_count = defaultdict(lambda: defaultdict(int))  # 每天每家医院每个科室的拜访次数
    daily_hospital_dept_doctors = defaultdict(lambda: defaultdict(list))  # 每天每家医院每个科室已安排的医生姓名
    visitor_visit_count = {visitor: 0 for visitor in visitors}  # 记录每个拜访人的拜访次数
    visitor_hospital_history = {visitor: [] for visitor in visitors}  # 记录每个拜访者的医院拜访历史
    
    total_visits = 0
    
    for day in working_days:
        # 检查是否所有拜访人都已达到目标
        all_completed = all(visitor_visit_count[visitor] >= visitor_targets[visitor] for visitor in visitors)
        if all_completed or total_visits >= target_visits:
            break
            
        day_str = day.strftime('%Y-%m-%d')
        daily_hospital_dept_count[day_str] = defaultdict(int)
        daily_hospital_dept_doctors[day_str] = defaultdict(list)
        
        for visitor in visitors:
            # 检查该拜访人是否已达到目标拜访量
            if visitor_visit_count[visitor] >= visitor_targets[visitor]:
                continue
                
            # 每人每天拜访量根据配置设定，但不超过剩余目标
            remaining_target = visitor_targets[visitor] - visitor_visit_count[visitor]
            daily_visits = min(random.randint(*daily_visits_range), remaining_target)
            
            if daily_visits <= 0:
                continue
            
            visitor_hospitals = hospital_assignment[visitor]
            
            # 每天选择医院（优先选择剩余医生较多的医院）
            daily_hospitals = select_daily_hospitals(visitor_hospitals, df, doctor_visited, max_hospitals=2)
            
            # 过滤掉会导致连续3天拜访同一医院的医院
            filtered_hospitals = []
            for hospital in daily_hospitals:
                if not check_consecutive_hospital_visits(visitor_hospital_history[visitor], hospital, day_str):
                    filtered_hospitals.append(hospital)
            
            # 如果过滤后没有可选医院，则跳过该拜访者今天的安排
            if not filtered_hospitals:
                continue
                
            daily_hospitals = filtered_hospitals
            
            # 贪心策略：优先选择医生较多的医院，减少医院数量
            hospital_doctor_count = {}
            for hospital in daily_hospitals:
                available_doctors = df[
                    (df['医院名称'] == hospital) & 
                    (~df['医生名称'].isin(doctor_visited))
                ]
                hospital_doctor_count[hospital] = len(available_doctors)
            
            # 按医生数量排序医院
            sorted_hospitals = sorted(hospital_doctor_count.items(), 
                                    key=lambda x: x[1], reverse=True)
            
            visits_today = []
            hospital_visits_today = defaultdict(int)
            
            for hospital, available_count in sorted_hospitals:
                if len(visits_today) >= daily_visits or total_visits >= target_visits:
                    break
                    
                if available_count == 0:
                    continue
                    
                # 获取该医院未拜访的医生
                available_doctors = df[
                    (df['医院名称'] == hospital) & 
                    (~df['医生名称'].isin(doctor_visited))
                ]
                
                if len(available_doctors) == 0:
                    continue
                
                # 动态调整最少拜访限制：后期清理剩余医生时放宽限制
                remaining_total_doctors = len(df[~df['医生名称'].isin(doctor_visited)])
                total_remaining_visits = target_visits - total_visits
                
                # 如果剩余医生较少或接近目标完成，放宽最少拜访限制
                if remaining_total_doctors <= 50 or total_remaining_visits <= 100:
                    min_visits_per_hospital = 2  # 放宽到最少2条
                else:
                    min_visits_per_hospital = 3  # 正常情况下最少3条
                
                max_visits_this_hospital = min(
                    daily_visits - len(visits_today),
                    len(available_doctors),
                    target_visits - total_visits
                )
                
                if max_visits_this_hospital < min_visits_per_hospital:
                    continue
                    
                # 按科室分组
                dept_groups = available_doctors.groupby('科室')
                
                hospital_visits = 0
                for dept, dept_doctors in dept_groups:
                    if hospital_visits >= max_visits_this_hospital:
                        break
                        
                    # 每个科室每天最多4-6次拜访
                    max_dept_visits = random.randint(4, 6)
                    current_dept_visits = daily_hospital_dept_count[day_str][f"{hospital}_{dept}"]
                    
                    if current_dept_visits >= max_dept_visits:
                        continue
                    
                    remaining_dept_visits = max_dept_visits - current_dept_visits
                    dept_visits = min(
                        remaining_dept_visits,
                        len(dept_doctors),
                        max_visits_this_hospital - hospital_visits
                    )
                    
                    # 逐个选择医生，确保不重复姓氏
                    existing_doctors_in_dept = daily_hospital_dept_doctors[day_str][f"{hospital}_{dept}"]
                    selected_doctors = []
                    available_doctors_list = list(dept_doctors.iterrows())
                    random.shuffle(available_doctors_list)  # 随机打乱顺序
                    
                    for _, doctor_row in available_doctors_list:
                        if len(selected_doctors) >= dept_visits:
                            break
                            
                        # 检查与已选择的医生和当天已安排的医生是否有相同姓氏
                        current_dept_doctors = existing_doctors_in_dept + [d['医生名称'] for d in selected_doctors]
                        if not check_same_surname(doctor_row['医生名称'], current_dept_doctors):
                            selected_doctors.append(doctor_row)
                    
                    if len(selected_doctors) == 0:
                        continue
                    
                    for doctor_row in selected_doctors:
                        if len(visits_today) >= daily_visits or total_visits >= target_visits:
                            break
                            
                        # 匹配医院地址
                        hospital_addr = df_addr[df_addr['医院名称'] == doctor_row['医院名称']]
                        address = hospital_addr['地址'].iloc[0] if len(hospital_addr) > 0 else '地址未找到'
                        
                        visit = {
                            '日期': day_str,
                            '医院名称': doctor_row['医院名称'],
                            '拜访人': visitor,
                            '科室': doctor_row['科室'],
                            '医生名称': doctor_row['医生名称'],
                            '地址': address
                        }
                        
                        visits_today.append(visit)
                        doctor_visited.add(doctor_row['医生名称'])
                        daily_hospital_dept_count[day_str][f"{hospital}_{dept}"] += 1
                        daily_hospital_dept_doctors[day_str][f"{hospital}_{dept}"].append(doctor_row['医生名称'])
                        hospital_visits += 1
                        total_visits += 1
                        visitor_visit_count[visitor] += 1
                
                hospital_visits_today[hospital] = hospital_visits
            
            # 计算拜访时间
            visits_today = calculate_visit_times(visits_today, visitor)
            visit_plan.extend(visits_today)
            
            # 更新拜访者的医院历史记录
            if visits_today:
                # 获取当天拜访的医院列表（去重）
                hospitals_visited_today = list(set([visit['医院名称'] for visit in visits_today]))
                # 为每个拜访的医院添加记录
                for hospital in hospitals_visited_today:
                    visitor_hospital_history[visitor].append({
                        'date': day_str,
                        'hospital': hospital
                    })
    
    return visit_plan

def save_to_excel(visit_plan, output_file, visitor_name):
    """保存拜访计划到Excel文件"""
    df_result = pd.DataFrame(visit_plan)
    
    # 确保列的顺序：日期 医院名称 地址 拜访人 科室 医生名称 拜访开始时间 拜访结束时间
    column_order = ['日期', '医院名称', '地址', '拜访人', '科室', '医生名称', '拜访开始时间', '拜访结束时间']
    df_result = df_result[column_order]
    
    # 按日期、拜访人和拜访开始时间排序
    df_result['日期'] = pd.to_datetime(df_result['日期'])
    df_result = df_result.sort_values(['日期', '拜访人', '拜访开始时间'])
    df_result['日期'] = df_result['日期'].dt.strftime('%Y/%m/%d')
    
    # 保存到Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_result.to_excel(writer, sheet_name='拜访计划', index=False)
        
        # 添加统计信息
        stats = []
        stats.append(['总拜访次数', len(df_result)])
        stats.append([f'{visitor_name}拜访次数', len(df_result[df_result['拜访人'] == visitor_name])])
        stats.append(['涉及医院数量', df_result['医院名称'].nunique()])
        stats.append(['涉及医生数量', df_result['医生名称'].nunique()])
        
        df_stats = pd.DataFrame(stats, columns=['统计项', '数值'])
        df_stats.to_excel(writer, sheet_name='统计信息', index=False)
    
    print(f"拜访计划已保存到：{output_file}")
    return df_result

def print_calendar_info(working_days):
    """打印日历信息，显示工作日和节假日"""
    print("\n=== 日历信息 ===")
    if CHINESECALENDAR_AVAILABLE:
        print("✅ 使用 chinese_calendar 包处理节假日")
    else:
        print("⚠️ 使用简化版节假日处理")
    
    print(f"可拜访日期数量：{len(working_days)}")
    print("可拜访日期列表：")
    for day in working_days:
        weekday_name = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][day.weekday()]
        print(f"  {day.strftime('%Y-%m-%d')} ({weekday_name})")

def main(visitor_config, daily_visits_range, excel_file, output_file, start_year_month, end_year_month, target_visits=400):
    # 验证配置
    if visitor_config not in CONFIG:
        print(f"错误：未找到配置 '{visitor_config}'")
        print(f"可用配置：{list(CONFIG.keys())}")
        return
    
    # 获取配置
    config = CONFIG[visitor_config]
    visitor_name = config['visitor_name']
    target_hospitals = config['target_hospitals']
    
    # 解析日期配置
    start_year, start_month = start_year_month
    end_year, end_month = end_year_month
    
    # 计算月份的最后一天
    import calendar
    last_day = calendar.monthrange(end_year, end_month)[1]
    
    start_date = datetime(start_year, start_month, 1)
    end_date = datetime(end_year, end_month, last_day)
    
    visitors = [visitor_name]  # 只有一个拜访者
    
    print(f"\n=== 当前配置：{visitor_config} ===")
    print(f"拜访人员：{visitor_name}")
    print(f"每日拜访量：{daily_visits_range[0]}-{daily_visits_range[1]}条")
    print(f"目标医院数量：{len(target_hospitals)}家")
    print(f"时间范围：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    
    # 读取数据
    print("\n正在读取Excel文件...")
    df, df_addr = read_excel_data(excel_file)
    if df is None or df_addr is None:
        return
    
    # 过滤数据，只保留指定医院的医生
    print(f"原始数据：{len(df)}条记录")
    df = df[df['医院名称'].isin(target_hospitals)]
    print(f"过滤后数据：{len(df)}条记录")
    print(f"涉及医院：{df['医院名称'].unique()}")
    
    # 过滤医院地址数据
    df_addr = df_addr[df_addr['医院名称'].isin(target_hospitals)]
    
    # 获取工作日
    working_days = get_working_days(start_date, end_date)
    print_calendar_info(working_days)
    
    # 生成拜访计划
    print("\n正在生成拜访计划...")
    visit_plan = greedy_visit_planning(df, df_addr, working_days, visitors, target_visits, daily_visits_range)
    
    # 保存结果
    print("\n正在保存结果...")
    df_result = save_to_excel(visit_plan, output_file, visitor_name)
    
    # 打印统计信息
    print("\n=== 拜访计划统计 ===")
    print(f"总拜访次数：{len(visit_plan)}")
    print(f"{visitor_name}拜访次数：{len([v for v in visit_plan if v['拜访人'] == visitor_name])}")
    print(f"涉及医院数量：{len(set([v['医院名称'] for v in visit_plan]))}")
    print(f"涉及医生数量：{len(set([v['医生名称'] for v in visit_plan]))}")
    
    # 按日期统计
    daily_stats = defaultdict(lambda: defaultdict(int))
    for visit in visit_plan:
        daily_stats[visit['日期']][visit['拜访人']] += 1
    
    print("\n=== 每日拜访统计 ===")
    for date in sorted(daily_stats.keys()):
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        weekday_name = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
        print(f"{date} ({weekday_name}): {visitor_name} {daily_stats[date][visitor_name]}次")

# ==================== 配置区域 ====================
# 在这里修改所有配置参数

# 每日拜访量配置
DAILY_VISITS_RANGE = (13, 16)  # 每天拜访条数范围，可根据需要修改

# 拜访人员选择配置
VISITOR_CONFIG = '何勇'  # 可选择：'何勇' 或 '张丹凤'

# 目标拜访总数
TARGET_VISITS = 400

# 文件路径配置
EXCEL_FILE = '/Users/a000/Documents/济生/医院拜访25/医院医生列表2025-07-10.xlsx'  # 输入Excel文件路径
OUTPUT_FILE = '/Users/a000/Documents/济生/医院拜访25/2510/贵州医生拜访2510-hy.xlsx'  # 输出Excel文件路径

# 拜访日期范围配置（年，月）
START_YEAR_MONTH = (2025, 10)  # 开始年月：(年份, 月份)
END_YEAR_MONTH = START_YEAR_MONTH #(2025, 3)    # 结束年月：(年份, 月份)

# 人员配置字典（只包含人员相关信息）
CONFIG = {
    '何勇': {
        'visitor_name': '何勇',
        'target_hospitals': [
            '贵阳市第二人民医院（金阳医院）',
            '贵州省人民医院',
            '贵州省职工医院',
            '贵州中医药大学第一附属医院',
            '上海儿童医学中心贵州医院'
        ]
    },
    '张丹凤': {
        'visitor_name': '张丹凤',
        'target_hospitals': [
            '贵黔国际总医院',
            '贵阳市第一人民医院',
            '贵阳市妇幼保健院',
            '贵阳市公共卫生救治中心',
            '贵州省第二人民医院',
            '贵州省中医药大学第二附属医院',
            '清镇市第一人民医院',            
            '贵州医科大学附属医院'
        ]
    }
}

# ==================== 程序入口 ====================
if __name__ == "__main__":
    main(VISITOR_CONFIG, DAILY_VISITS_RANGE, EXCEL_FILE, OUTPUT_FILE, START_YEAR_MONTH, END_YEAR_MONTH, TARGET_VISITS)