#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按新的排序规则处理药店拜访数据
1. 按区域a的值分组计数作为第一排序（降序）
2. 区域a的值作为第二排序（升序）
3. 区域编号作为第三排序（升序）
4. 区域内序号作为第四排序（升序）
"""

import pandas as pd
import numpy as np
from datetime import datetime
from openpyxl import load_workbook

# 配置参数
FILE_PATH = "/Users/a000/Documents/济生/药店拜访25/2505张丹凤/遵义拜访时间250813-3.xlsx"
SHEET_NAME = "张丹凤05"
NEW_SHEET_NAME = "张丹凤05_新排序"

def process_pharmacy_data_v2():
    """按新排序规则处理药店数据"""
    try:
        # 读取Excel文件
        print(f"正在读取文件: {FILE_PATH}")
        print(f"工作表: {SHEET_NAME}")
        
        df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
        print(f"原始数据行数: {len(df)}")
        
        # 1. 按照"区域编号"进行分组，统计每个区域编号下各区域的药店数量
        print("\n=== 步骤1: 按区域编号分组统计 ===")
        
        # 计算每个区域编号下各区域的药店数量
        region_stats = df.groupby(['区域编号', '区域']).size().reset_index(name='药店数量')
        print("各区域编号下的区域统计:")
        print(region_stats.head(10).to_string(index=False))
        
        # 2. 找出每个区域编号中药店数量最多的区域作为"区域a"
        print("\n=== 步骤2: 确定每个区域编号的主要区域(区域a) ===")
        
        # 对每个区域编号，找出药店数量最多的区域
        region_a_mapping = {}
        for region_num in df['区域编号'].unique():
            region_group = region_stats[region_stats['区域编号'] == region_num]
            max_count_row = region_group.loc[region_group['药店数量'].idxmax()]
            region_a_mapping[region_num] = max_count_row['区域']
        
        # 为原始数据添加区域a列
        df['区域a'] = df['区域编号'].map(region_a_mapping)
        
        print("区域编号到区域a的映射:")
        for region_num, region_a in sorted(region_a_mapping.items()):
            print(f"  区域编号 {region_num} -> 区域a: {region_a}")
        
        # 3. 计算区域a的分组计数
        print("\n=== 步骤3: 计算区域a分组计数 ===")
        
        region_a_counts = df['区域a'].value_counts().to_dict()
        df['区域a计数'] = df['区域a'].map(region_a_counts)
        
        print("区域a计数统计:")
        for region_a, count in sorted(region_a_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {region_a}: {count}个药店")
        
        # 4. 按照新的排序规则进行排序
        print("\n=== 步骤4: 按新排序规则排序 ===")
        print("排序规则:")
        print("  1. 区域a值优先级（以'区'结尾的优先）")
        print("  2. 区域a计数（降序）")
        print("  3. 区域a值（升序）")
        print("  4. 区域编号（升序）")
        print("  5. 区域内顺序（升序）")
        
        # 添加区域a优先级列：以'区'结尾的为0，其他为1
        df['区域a优先级'] = df['区域a'].apply(lambda x: 0 if x.endswith('区') else 1)
        
        print("\n区域a优先级分类:")
        priority_stats = df.groupby(['区域a优先级', '区域a']).size().reset_index(name='数量')
        for priority in [0, 1]:
            priority_data = priority_stats[priority_stats['区域a优先级'] == priority]
            priority_name = "以'区'结尾" if priority == 0 else "其他"
            print(f"  {priority_name}:")
            for _, row in priority_data.iterrows():
                print(f"    {row['区域a']}: {row['数量']}个药店")
        
        # 执行多级排序
        df_sorted = df.sort_values([
            '区域a优先级',  # 第一排序：区域a优先级（升序，0在前）
            '区域a计数',    # 第二排序：区域a计数（降序）
            '区域a',        # 第三排序：区域a值（升序）
            '区域编号',     # 第四排序：区域编号（升序）
            '区域内顺序'    # 第五排序：区域内顺序（升序）
        ], ascending=[True, False, True, True, True]).reset_index(drop=True)
        
        print(f"排序后数据行数: {len(df_sorted)}")
        
        # 5. 显示排序结果预览
        print("\n=== 步骤5: 排序结果预览 ===")
        
        preview_columns = ['区域a计数', '区域a优先级', '区域a', '区域编号', '区域内顺序', '名称']
        print("前20行排序结果:")
        print(df_sorted[preview_columns].head(20).to_string(index=False))
        
        # 6. 验证排序正确性
        print("\n=== 步骤6: 验证排序正确性 ===")
        
        # 检查区域a优先级是否按升序排列
        is_priority_asc = df_sorted['区域a优先级'].is_monotonic_increasing
        print(f"区域a优先级升序排列: {'✓' if is_priority_asc else '✗'}")
        
        # 检查相同区域a优先级内的区域a计数是否按降序排列
        for priority in df_sorted['区域a优先级'].unique():  # 检查每个优先级
            subset = df_sorted[df_sorted['区域a优先级'] == priority]
            if len(subset) > 1:
                is_count_desc = subset['区域a计数'].is_monotonic_decreasing
                priority_name = "以'区'结尾" if priority == 0 else "其他"
                print(f"{priority_name}内区域a计数降序: {'✓' if is_count_desc else '✗'}")
                
                # 检查相同计数内的区域a是否按升序排列
                for count in subset['区域a计数'].unique()[:3]:
                    count_subset = subset[subset['区域a计数'] == count]
                    if len(count_subset) > 1:
                        is_region_a_asc = count_subset['区域a'].is_monotonic_increasing
                        print(f"  {priority_name}-计数{count}内区域a升序: {'✓' if is_region_a_asc else '✗'}")
        
        # 7. 保存到原Excel文件的新标签页
        print(f"\n=== 步骤7: 保存到原文件新标签页 ===")
        
        try:
            # 使用openpyxl加载现有工作簿
            with pd.ExcelWriter(FILE_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_sorted.to_excel(writer, sheet_name=NEW_SHEET_NAME, index=False)
            
            print(f"数据已保存到原文件的新标签页: {NEW_SHEET_NAME}")
            
        except Exception as e:
            print(f"保存到原文件时出错: {e}")
            # 备用方案：保存到新文件
            backup_file = f"/Users/a000/药店拜访/遵义药店数据_新排序_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df_sorted.to_excel(backup_file, index=False)
            print(f"已保存到备用文件: {backup_file}")
        
        # 8. 输出最终统计信息
        print("\n=== 最终统计信息 ===")
        print(f"总药店数: {len(df_sorted)}")
        print(f"区域a种类数: {df_sorted['区域a'].nunique()}")
        print(f"区域编号数: {df_sorted['区域编号'].nunique()}")
        
        print("\n区域a计数分布:")
        count_distribution = df_sorted['区域a计数'].value_counts().sort_index(ascending=False)
        for count, freq in count_distribution.items():
            print(f"  计数{count}: {freq}个药店")
        
        print("\n前10个区域a及其计数:")
        top_regions = df_sorted[['区域a', '区域a计数']].drop_duplicates().head(10)
        for _, row in top_regions.iterrows():
            print(f"  {row['区域a']}: {row['区域a计数']}个药店")
        
        return df_sorted
        
    except Exception as e:
        print(f"处理数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = process_pharmacy_data_v2()
    if result is not None:
        print("\n处理完成！")
    else:
        print("\n处理失败！")