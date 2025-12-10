#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片组内相似度排序工具
按照文件名前缀分组，计算组内照片相似度，并按相似度重新排序文件名
"""

import os
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict
import shutil
from datetime import datetime
import re

class PhotoGroupSimilarityProcessor:
    def __init__(self, similarity_threshold=0.85, hash_threshold=0.7):
        self.similarity_threshold = similarity_threshold
        self.hash_threshold = hash_threshold
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
    def get_image_files(self, directory: str) -> List[str]:
        """获取目录中的所有图片文件（不包含子目录）"""
        image_files = []
        if not os.path.exists(directory):
            print(f"警告: 目录不存在 {directory}")
            return image_files
            
        try:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and Path(file).suffix.lower() in self.supported_formats:
                    image_files.append(file_path)
        except PermissionError:
            print(f"警告: 没有权限访问目录 {directory}")
        except Exception as e:
            print(f"警告: 读取目录时出错 {directory}: {e}")
            
        return image_files
    
    def extract_prefix(self, filename: str) -> str:
        """提取文件名前缀（_之前的数字部分）"""
        basename = os.path.basename(filename)
        # 匹配文件名开头的数字部分（直到第一个下划线）
        match = re.match(r'^(\d+)', basename)
        if match:
            return match.group(1)
        return "unknown"
    
    def group_files_by_prefix(self, image_files: List[str]) -> Dict[str, List[str]]:
        """按照文件名前缀分组"""
        groups = defaultdict(list)
        for file_path in image_files:
            prefix = self.extract_prefix(file_path)
            groups[prefix].append(file_path)
        return dict(groups)
    
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
    
    def calculate_dhash(self, image_path: str) -> str:
        """计算差异哈希（dHash），对图像变化更敏感"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # 转换为灰度图并缩放到9x8（比较相邻像素）
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (9, 8))
            
            # 计算水平差异
            hash_str = ''
            for i in range(8):
                for j in range(8):
                    hash_str += '1' if resized[i, j] > resized[i, j + 1] else '0'
            
            return hash_str
        except Exception as e:
            print(f"计算dHash失败 {image_path}: {e}")
            return None
    
    def calculate_color_histogram_fast(self, image_path: str) -> np.ndarray:
        """计算快速颜色直方图"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # 缩小图片以提高速度
            img_small = cv2.resize(img, (64, 64))
            
            # 计算RGB三通道的简化直方图
            hist_r = cv2.calcHist([img_small], [0], None, [8], [0, 256])
            hist_g = cv2.calcHist([img_small], [1], None, [8], [0, 256])
            hist_b = cv2.calcHist([img_small], [2], None, [8], [0, 256])
            
            # 合并并归一化
            hist = np.concatenate([hist_r.flatten(), hist_g.flatten(), hist_b.flatten()])
            hist = hist / (hist.sum() + 1e-7)  # 避免除零
            
            return hist
        except Exception as e:
            print(f"计算颜色直方图失败 {image_path}: {e}")
            return None
    
    def calculate_thumbnail_similarity(self, img1_path: str, img2_path: str) -> float:
        """计算缩略图像素相似度"""
        try:
            img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                return 0.0
            
            # 缩放到16x16进行快速比较
            thumb1 = cv2.resize(img1, (16, 16))
            thumb2 = cv2.resize(img2, (16, 16))
            
            # 计算结构相似度的简化版本
            diff = np.abs(thumb1.astype(float) - thumb2.astype(float))
            mse = np.mean(diff ** 2)
            
            # 转换为相似度（0-1）
            similarity = 1 / (1 + mse / 1000.0)
            return similarity
        except Exception as e:
            print(f"计算缩略图相似度失败: {e}")
            return 0.0
    
    def calculate_similarity(self, img1_path: str, img2_path: str) -> float:
        """计算两张图片的综合相似度（多种快速方法结合）"""
        # 方法1: 改进的感知哈希（pHash）
        hash1 = self.calculate_image_hash(img1_path)
        hash2 = self.calculate_image_hash(img2_path)
        
        if not hash1 or not hash2:
            return 0.0
        
        hamming_dist = self.hamming_distance(hash1, hash2)
        phash_similarity = 1 - (hamming_dist / 64.0)
        
        # 方法2: 差异哈希（dHash）
        dhash1 = self.calculate_dhash(img1_path)
        dhash2 = self.calculate_dhash(img2_path)
        
        dhash_similarity = 0.0
        if dhash1 and dhash2:
            dhash_dist = self.hamming_distance(dhash1, dhash2)
            dhash_similarity = 1 - (dhash_dist / 64.0)
        
        # 方法3: 快速颜色直方图
        hist1 = self.calculate_color_histogram_fast(img1_path)
        hist2 = self.calculate_color_histogram_fast(img2_path)
        
        hist_similarity = 0.0
        if hist1 is not None and hist2 is not None:
            # 使用余弦相似度
            dot_product = np.dot(hist1, hist2)
            norm1 = np.linalg.norm(hist1)
            norm2 = np.linalg.norm(hist2)
            if norm1 > 0 and norm2 > 0:
                hist_similarity = dot_product / (norm1 * norm2)
        
        # 方法4: 缩略图像素相似度
        thumb_similarity = self.calculate_thumbnail_similarity(img1_path, img2_path)
        
        # 综合相似度（权重可调）
        # pHash权重30%，dHash权重30%，颜色直方图权重25%，缩略图权重15%
        overall_similarity = (
            phash_similarity * 0.30 + 
            dhash_similarity * 0.30 + 
            hist_similarity * 0.25 + 
            thumb_similarity * 0.15
        )
        
        return overall_similarity
    
    def calculate_group_similarities(self, group_files: List[str]) -> List[Tuple[str, str, float]]:
        """计算组内所有照片的两两相似度"""
        similarities = []
        n = len(group_files)
        
        print(f"    计算 {n} 张照片的两两相似度...")
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self.calculate_similarity(group_files[i], group_files[j])
                similarities.append((group_files[i], group_files[j], similarity))
                
                if (len(similarities)) % 10 == 0:
                    print(f"      进度: {len(similarities)}/{n*(n-1)//2}")
        
        return similarities
    
    def sort_files_by_similarity(self, group_files: List[str]) -> List[Tuple[str, float]]:
        """按所有两两相似度值倒序排列，已排序的照片不再参与后续排序"""
        if len(group_files) <= 1:
            return [(f, 0.0) for f in group_files]
        
        # 计算所有两两相似度
        similarities = self.calculate_group_similarities(group_files)
        
        # 按相似度从高到低排序所有照片对
        similarities.sort(key=lambda x: x[2], reverse=True)
        
        # 构建排序结果
        sorted_files = []
        used_files = set()
        
        # 按相似度从高到低依次处理照片对
        for file1, file2, similarity in similarities:
            # 如果两张照片都还没有被排序
            if file1 not in used_files and file2 not in used_files:
                # 随机决定这两张照片的前后顺序
                import random
                if random.random() > 0.5:
                    sorted_files.extend([(file1, similarity), (file2, similarity)])
                else:
                    sorted_files.extend([(file2, similarity), (file1, similarity)])
                used_files.add(file1)
                used_files.add(file2)
            # 如果只有第一张照片还没有被排序
            elif file1 not in used_files:
                sorted_files.append((file1, similarity))
                used_files.add(file1)
            # 如果只有第二张照片还没有被排序
            elif file2 not in used_files:
                sorted_files.append((file2, similarity))
                used_files.add(file2)
            # 如果两张照片都已经被排序，跳过这个相似度对
        
        # 添加剩余的照片（没有参与任何相似度对的）
        for file_path in group_files:
            if file_path not in used_files:
                sorted_files.append((file_path, 0.0))
        
        return sorted_files
    
    def rename_files_by_similarity(self, directory: str, backup_dir: str = None):
        """按相似度重新命名文件"""
        print(f"开始处理目录: {directory}")
        
        # 获取所有图片文件
        image_files = self.get_image_files(directory)
        print(f"找到 {len(image_files)} 张照片")
        
        if not image_files:
            print("目录中没有找到照片文件")
            return
        
        # 按前缀分组
        groups = self.group_files_by_prefix(image_files)
        print(f"按前缀分为 {len(groups)} 组:")
        for prefix, files in groups.items():
            print(f"  组 {prefix}: {len(files)} 张照片")
        
        # 创建备份目录
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
            print(f"备份目录: {backup_dir}")
        
        # 处理每个组
        all_rename_operations = []
        
        for prefix, group_files in groups.items():
            print(f"\n处理组 {prefix} ({len(group_files)} 张照片):")
            
            if len(group_files) == 1:
                print(f"  只有1张照片，无需排序")
                continue
            
            # 按相似度排序
            sorted_files = self.sort_files_by_similarity(group_files)
            
            print(f"  排序结果:")
            for i, (file_path, similarity_score) in enumerate(sorted_files):
                if similarity_score > 0:
                    print(f"    {i+1}. {os.path.basename(file_path)} (高相似度: {similarity_score:.3f})")
                else:
                    print(f"    {i+1}. {os.path.basename(file_path)} (无高相似度对)")
            
            # 生成新文件名
            for i, (old_path, similarity_score) in enumerate(sorted_files):
                old_name = os.path.basename(old_path)
                name_parts = old_name.split('_', 1)
                
                if len(name_parts) > 1:
                    # 保持原有的后缀部分，只修改序号
                    new_name = f"{prefix}_{i+1:02d}_{name_parts[1]}"
                else:
                    # 如果没有下划线，直接添加序号
                    name_without_ext = os.path.splitext(old_name)[0]
                    ext = os.path.splitext(old_name)[1]
                    new_name = f"{prefix}_{i+1:02d}{ext}"
                
                new_path = os.path.join(directory, new_name)
                all_rename_operations.append((old_path, new_path, similarity_score))
        
        # 执行重命名操作
        if all_rename_operations:
            print(f"\n开始重命名 {len(all_rename_operations)} 个文件...")
            
            for old_path, new_path, similarity_score in all_rename_operations:
                try:
                    # 备份原文件
                    if backup_dir:
                        backup_path = os.path.join(backup_dir, os.path.basename(old_path))
                        shutil.copy2(old_path, backup_path)
                    
                    # 重命名
                    if old_path != new_path:  # 避免重命名为相同名称
                        # 如果目标文件已存在，先重命名为临时文件
                        if os.path.exists(new_path):
                            temp_path = new_path + ".temp"
                            os.rename(old_path, temp_path)
                            os.rename(temp_path, new_path)
                        else:
                            os.rename(old_path, new_path)
                        
                        print(f"  ✓ {os.path.basename(old_path)} -> {os.path.basename(new_path)} (相似度: {similarity_score:.3f})")
                    
                except Exception as e:
                    print(f"  ✗ 重命名失败: {old_path} -> {new_path}: {e}")
        
        print(f"\n处理完成！")
    
    def save_similarity_report(self, directory: str, output_file: str):
        """生成相似度分析报告"""
        image_files = self.get_image_files(directory)
        groups = self.group_files_by_prefix(image_files)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("照片组内相似度分析报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"分析目录: {directory}\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总照片数: {len(image_files)}\n")
            f.write(f"分组数: {len(groups)}\n\n")
            
            for prefix, group_files in groups.items():
                f.write(f"组 {prefix} ({len(group_files)} 张照片):\n")
                f.write("-" * 30 + "\n")
                
                if len(group_files) <= 1:
                    f.write("  只有1张照片，无需分析\n\n")
                    continue
                
                sorted_files = self.sort_files_by_similarity(group_files)
                
                for i, (file_path, similarity_score) in enumerate(sorted_files):
                    f.write(f"  {i+1}. {os.path.basename(file_path)}\n")
                    if similarity_score > 0:
                        f.write(f"     高相似度分数: {similarity_score:.3f}\n")
                    else:
                        f.write(f"     无高相似度对\n")
                
                f.write("\n")

def main():
    # 配置路径
    target_directory = "/Users/a000/Documents/济生/医院拜访25/2504/贵州医生拜访2504-张丹凤/transformed_20250724_091051"
    
    # 创建备份目录
    backup_directory = os.path.join(os.path.dirname(target_directory), "backup_" + datetime.now().strftime('%Y%m%d_%H%M'))
    
    # 相似度阈值配置
    hash_threshold = 0.7
    similarity_threshold = 0.85
    
    print("照片组内相似度排序工具")
    print("=" * 35)
    print(f"目标目录: {target_directory}")
    print(f"备份目录: {backup_directory}")
    print(f"哈希初筛阈值: {hash_threshold}")
    print(f"相似度阈值: {similarity_threshold}")
    print()
    
    # 创建处理器
    processor = PhotoGroupSimilarityProcessor(
        similarity_threshold=similarity_threshold,
        hash_threshold=hash_threshold
    )
    
    # 执行重命名
    processor.rename_files_by_similarity(target_directory, backup_directory)
    
    # 生成报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    target_parent_dir = os.path.dirname(target_directory)
    report_file = os.path.join(target_parent_dir, f"照片相似度排序报告_{timestamp}.txt")
    processor.save_similarity_report(target_directory, report_file)
    print(f"\n分析报告已保存到: {report_file}")

if __name__ == "__main__":
    main()