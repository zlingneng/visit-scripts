#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片相似度比对工具
用于检测不同目录中的照片是否有高度相似的内容
"""

import os
import cv2
import numpy as np
from pathlib import Path
import hashlib
from collections import defaultdict
import argparse
from typing import List, Tuple, Dict
import shutil
from datetime import datetime

class PhotoSimilarityDetector:
    def __init__(self, similarity_threshold=0.85, hash_threshold=0.7):
        self.similarity_threshold = similarity_threshold
        self.hash_threshold = hash_threshold  # 提高初筛阈值，减少详细比对数量
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
    def get_image_files(self, directory: str) -> List[str]:
        """获取目录中的所有图片文件（不包含子目录）"""
        image_files = []
        if not os.path.exists(directory):
            print(f"警告: 目录不存在 {directory}")
            return image_files
            
        # 只获取当前目录下的文件，不递归子目录
        try:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                # 确保是文件而不是目录，并且是支持的图片格式
                if os.path.isfile(file_path) and Path(file).suffix.lower() in self.supported_formats:
                    image_files.append(file_path)
        except PermissionError:
            print(f"警告: 没有权限访问目录 {directory}")
        except Exception as e:
            print(f"警告: 读取目录时出错 {directory}: {e}")
            
        return image_files
    
    def calculate_image_hash(self, image_path: str) -> str:
        """计算图片的感知哈希值"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 缩放到8x8
            resized = cv2.resize(gray, (8, 8))
            
            # 计算平均值
            avg = resized.mean()
            
            # 生成哈希
            hash_str = ''
            for i in range(8):
                for j in range(8):
                    hash_str += '1' if resized[i, j] > avg else '0'
            
            return hash_str
        except Exception as e:
            print(f"处理图片失败 {image_path}: {e}")
            return None
    
    def calculate_histogram_similarity(self, img1_path: str, img2_path: str) -> float:
        """计算两张图片的快速直方图相似度"""
        try:
            img1 = cv2.imread(img1_path)
            img2 = cv2.imread(img2_path)
            
            if img1 is None or img2 is None:
                return 0.0
            
            # 缩小图片尺寸以提高速度
            img1_small = cv2.resize(img1, (64, 64))
            img2_small = cv2.resize(img2, (64, 64))
            
            # 计算简化的RGB直方图
            hist1 = cv2.calcHist([img1_small], [0, 1, 2], None, [16, 16, 16], [0, 256, 0, 256, 0, 256])
            hist2 = cv2.calcHist([img2_small], [0, 1, 2], None, [16, 16, 16], [0, 256, 0, 256, 0, 256])
            
            # 计算相关性
            correlation = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return correlation
        except Exception as e:
            print(f"计算直方图相似度失败: {e}")
            return 0.0
    
    def calculate_feature_similarity(self, img1_path: str, img2_path: str) -> float:
        """计算快速特征相似度"""
        try:
            img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                return 0.0
            
            # 缩小图片以提高速度
            img1_small = cv2.resize(img1, (32, 32))
            img2_small = cv2.resize(img2, (32, 32))
            
            # 计算简单的像素差异
            diff = cv2.absdiff(img1_small, img2_small)
            mean_diff = np.mean(diff)
            
            # 转换为相似度 (差异越小，相似度越高)
            similarity = max(0, 1 - (mean_diff / 255.0))
            return similarity
        except Exception as e:
            print(f"计算特征相似度失败: {e}")
            return 0.0
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """计算汉明距离"""
        if not hash1 or not hash2 or len(hash1) != len(hash2):
            return 64  # 最大距离
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    
    def find_similar_photos(self, source_dir: str, target_dirs: List[str]) -> List[Dict]:
        """分阶段查找相似照片 - 先哈希初筛，再详细比对"""
        print(f"开始分析源目录: {source_dir}")
        source_files = self.get_image_files(source_dir)
        print(f"源目录找到 {len(source_files)} 张照片")
        
        if not source_files:
            print("源目录中没有找到照片文件")
            return []
        
        # 获取所有目标目录的文件
        target_files = []
        for target_dir in target_dirs:
            print(f"分析目标目录: {target_dir}")
            files = self.get_image_files(target_dir)
            target_files.extend(files)
            print(f"目标目录找到 {len(files)} 张照片")
        
        print(f"总共需要比对 {len(target_files)} 张目标照片")
        print(f"使用分阶段比对策略: 哈希初筛阈值 {self.hash_threshold}, 最终相似度阈值 {self.similarity_threshold}")
        
        # 第一阶段：预计算所有目标照片的哈希值
        print("\n第一阶段：计算目标照片哈希值...")
        target_hashes = {}
        for i, target_file in enumerate(target_files):
            if (i + 1) % 50 == 0 or i == len(target_files) - 1:
                print(f"  进度: {i+1}/{len(target_files)}")
            target_hash = self.calculate_image_hash(target_file)
            if target_hash:
                target_hashes[target_file] = target_hash
        
        print(f"成功计算 {len(target_hashes)} 张目标照片的哈希值")
        
        similar_pairs = []
        total_comparisons = 0
        detailed_comparisons = 0
        
        # 第二阶段：对每张源照片进行比对
        print("\n第二阶段：源照片比对...")
        for i, source_file in enumerate(source_files):
            print(f"\n处理源照片 {i+1}/{len(source_files)}: {os.path.basename(source_file)}")
            
            source_hash = self.calculate_image_hash(source_file)
            if not source_hash:
                continue
            
            # 哈希初筛阶段
            candidates = []
            for target_file, target_hash in target_hashes.items():
                total_comparisons += 1
                
                # 计算哈希相似度
                hamming_dist = self.hamming_distance(source_hash, target_hash)
                hash_similarity = 1 - (hamming_dist / 64.0)
                
                # 初筛：只有哈希相似度超过阈值的才进入详细比对
                if hash_similarity > self.hash_threshold:
                    candidates.append((target_file, hash_similarity))
            
            print(f"  哈希初筛: {len(candidates)} 张候选照片 (从 {len(target_hashes)} 张中筛选)")
            
            # 详细比对阶段
            if candidates:
                print(f"  开始详细比对 {len(candidates)} 张候选照片...")
                for target_file, hash_similarity in candidates:
                    detailed_comparisons += 1
                    
                    # 计算快速详细相似度
                    hist_similarity = self.calculate_histogram_similarity(source_file, target_file)
                    feature_similarity = self.calculate_feature_similarity(source_file, target_file)
                    
                    # 综合相似度评分 (权重调整)
                    overall_similarity = (hash_similarity * 0.4 + hist_similarity * 0.4 + feature_similarity * 0.2)
                    
                    if overall_similarity > self.similarity_threshold:
                        similar_pairs.append({
                            'source': source_file,
                            'target': target_file,
                            'hash_similarity': hash_similarity,
                            'hist_similarity': hist_similarity,
                            'feature_similarity': feature_similarity,
                            'overall_similarity': overall_similarity
                        })
                        print(f"    ✓ 发现相似照片: {os.path.basename(target_file)} (相似度: {overall_similarity:.3f})")
        
        print(f"\n比对统计:")
        print(f"  总哈希比对次数: {total_comparisons:,}")
        print(f"  详细比对次数: {detailed_comparisons:,}")
        print(f"  效率提升: {((total_comparisons - detailed_comparisons) / total_comparisons * 100):.1f}% 的比对被跳过")
        
        return similar_pairs
    
    def save_results(self, similar_pairs: List[Dict], output_file: str):
        """保存结果到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("照片相似度比对结果\n")
            f.write("=" * 50 + "\n\n")
            
            if not similar_pairs:
                f.write("未发现高度相似的照片\n")
                return
            
            f.write(f"共发现 {len(similar_pairs)} 对相似照片:\n\n")
            
            for i, pair in enumerate(similar_pairs, 1):
                f.write(f"{i}. 相似度: {pair['overall_similarity']:.3f}\n")
                f.write(f"   源照片: {pair['source']}\n")
                f.write(f"   目标照片: {pair['target']}\n")
                f.write(f"   哈希相似度: {pair['hash_similarity']:.3f}\n")
                f.write(f"   直方图相似度: {pair['hist_similarity']:.3f}\n")
                f.write(f"   特征相似度: {pair['feature_similarity']:.3f}\n")
                f.write("-" * 30 + "\n\n")

def main():
    # 配置路径
    source_directory = "/Users/a000/Documents/济生/医院拜访25/2512/贵州医生拜访2512-遵义安顺/未命名文件夹"
    #
    target_directories = [

        # "/Users/a000/Documents/济生/医院拜访25/2511/蔡林川2511/贵州医生拜访2511-蔡林川-审核/照片5",
        # "/Users/a000/Documents/济生/医院拜访25/2511/何勇2511/贵州医生拜访2511-何勇-送审/照片5",
        # "/Users/a000/Documents/济生/医院拜访25/2511/胡乐凤2511/贵州医生拜访2511-胡乐凤-送审/照片5",
        # "/Users/a000/Documents/济生/医院拜访25/2511/张丹凤2511/贵州医生拜访2511-张丹凤_审核/照片5",
        "/Users/a000/Documents/济生/医院拜访25/2511/张令能2511/贵州医生拜访2511-张令能-送审/照片5", #遵义

        # "/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/贵州医生拜访-展嘉科技2510-何勇-蔡林川-周星贤-送审2 2/照片5",
        # "/Users/a000/Documents/济生/医院拜访25/2510/张丹凤2510/贵州医生拜访-展嘉科技2510-张丹凤等-送审/照片5",
        "/Users/a000/Documents/济生/医院拜访25/2510/张令能等2510/贵州医生拜访展嘉科技2510-张令能等-送审/照片4", #遵义

        # "/Users/a000/Documents/济生/医院拜访25/贵州医院拜访250115-8/贵州医院拜访250115-8送审/照片",
        # "/Users/a000/Documents/济生/医院拜访25/2502/贵阳医院拜访2502张丹凤/贵州医院拜访2502-张丹凤3/照片2",
        # "/Users/a000/Documents/济生/医院拜访25/2503/张丹凤2503/贵州医生拜访2503-张丹凤2/照片",
        # "/Users/a000/Documents/济生/医院拜访25/2504/贵州医生拜访2504-张丹凤/贵州医生拜访2504-张丹凤-送审/照片",

        # "/Users/a000/Documents/济生/医院拜访25/贵州医院拜访250115-8/贵州医院拜访250115-8送审/照片",
        # "/Users/a000/Documents/济生/医院拜访25/2502/贵阳医院拜访2502何勇/贵阳医院拜访2502何勇/照片",
        # "/Users/a000/Documents/济生/医院拜访25/2503/何勇2503/贵州医生拜访2503-何勇/照片3",
        # "/Users/a000/Documents/济生/医院拜访25/2505/贵州医生拜访2505-hy/贵州医院拜访2505何勇-送审/照片4"


    ]
    
    # 相似度阈值配置 (优化版)
    hash_threshold = 0.7      # 哈希初筛阈值 (70%相似度进入详细比对，减少候选数量)
    similarity_threshold = 0.85  # 最终相似度阈值 (85%相似度判定为相似)
    
    print("照片相似度比对工具 (优化版)")
    print("=" * 35)
    print(f"源目录: {source_directory}")
    print(f"目标目录:")
    for target_dir in target_directories:
        print(f"  - {target_dir}")
    print(f"哈希初筛阈值: {hash_threshold} (提高效率)")
    print(f"最终相似度阈值: {similarity_threshold}")
    print()
    
    # 创建检测器
    detector = PhotoSimilarityDetector(
        similarity_threshold=similarity_threshold,
        hash_threshold=hash_threshold
    )
    
    # 查找相似照片
    similar_pairs = detector.find_similar_photos(source_directory, target_directories)
    
    # 显示结果
    print("\n" + "=" * 50)
    print("比对结果:")
    
    if not similar_pairs:
        print("未发现高度相似的照片")
    else:
        print(f"共发现 {len(similar_pairs)} 对相似照片:")
        print()
        
        for i, pair in enumerate(similar_pairs, 1):
            print(f"{i}. 相似度: {pair['overall_similarity']:.3f}")
            print(f"   源照片: {os.path.basename(pair['source'])}")
            print(f"   目标照片: {os.path.basename(pair['target'])}")
            print(f"   完整路径: {pair['target']}")
            print()
    
    # 保存结果
    # 生成带时间戳的文件名，保存到源目录的上一级目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    source_parent_dir = os.path.dirname(source_directory)
    output_file = os.path.join(source_parent_dir, f"照片相似度比对结果_{timestamp}.txt")
    detector.save_results(similar_pairs, output_file)
    print(f"详细结果已保存到: {output_file}")

if __name__ == "__main__":
    main()