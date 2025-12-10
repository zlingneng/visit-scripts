#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片视角随机变形工具
功能：对指定文件夹中的图片进行随机视角变形处理
包括：透视变换、旋转、缩放、倾斜等效果
"""

import os
import cv2
import numpy as np
import random
from pathlib import Path
import argparse
from datetime import datetime

class ImagePerspectiveTransformer:
    def __init__(self, output_suffix="_transformed"):
        self.output_suffix = output_suffix
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    
    def random_perspective_transform(self, image, intensity=0.3):
        """
        随机透视变换 - 剪切四边形区域并拉伸到原图尺寸
        intensity: 变形强度 (0-1)
        """
        h, w = image.shape[:2]
        
        # 计算变形幅度 - 按照长宽的1/15
        max_offset_x = w / 15  # 宽度方向的最大偏移
        max_offset_y = h / 15  # 高度方向的最大偏移
        
        # 生成随机偏移的四个角点（作为剪切区域）
        crop_points = np.float32([
            [random.uniform(0, max_offset_x), 
             random.uniform(0, max_offset_y)],  # 左上角
            [w-1 - random.uniform(0, max_offset_x), 
             random.uniform(0, max_offset_y)],  # 右上角
            [w-1 - random.uniform(0, max_offset_x), 
             h-1 - random.uniform(0, max_offset_y)],  # 右下角
            [random.uniform(0, max_offset_x), 
             h-1 - random.uniform(0, max_offset_y)]  # 左下角
        ])
        
        # 目标四个角点（原图的四个角）
        dst_points = np.float32([
            [0, 0],
            [w-1, 0],
            [w-1, h-1],
            [0, h-1]
        ])
        
        # 透视变换矩阵：将剪切的四边形拉伸到原图尺寸
        matrix = cv2.getPerspectiveTransform(crop_points, dst_points)
        
        # 应用变换
        transformed = cv2.warpPerspective(image, matrix, (w, h), 
                                        borderMode=cv2.BORDER_CONSTANT, 
                                        borderValue=(0, 0, 0))
        
        return transformed
    
    def random_rotation(self, image, max_angle=10):
        """
        随机旋转 - 原图旋转后用原图大小框裁剪，会丢失超出框外的内容
        max_angle: 最大旋转角度
        """
        h, w = image.shape[:2]
        
        # 随机角度
        angle = random.uniform(-max_angle, max_angle)
        
        # 计算旋转后需要的画布大小
        angle_rad = np.radians(abs(angle))
        new_w = int(w * np.cos(angle_rad) + h * np.sin(angle_rad))
        new_h = int(h * np.cos(angle_rad) + w * np.sin(angle_rad))
        
        # 旋转中心（扩展画布的中心）
        center = (new_w // 2, new_h // 2)
        
        # 旋转矩阵
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # 调整旋转矩阵，将原图放在扩展画布中心
        matrix[0, 2] += center[0] - w // 2
        matrix[1, 2] += center[1] - h // 2
        
        # 在扩展画布上旋转
        rotated_large = cv2.warpAffine(image, matrix, (new_w, new_h), 
                                     borderMode=cv2.BORDER_REFLECT_101)
        
        # 用原图大小的框从中心裁剪（会丢失超出框外的内容）
        start_x = (new_w - w) // 2
        start_y = (new_h - h) // 2
        rotated = rotated_large[start_y:start_y+h, start_x:start_x+w]
        
        return rotated
    
    def random_scale_crop(self, image, scale_range=(0.85, 1.15)):
        """
        随机缩放和裁剪
        scale_range: 缩放范围
        """
        h, w = image.shape[:2]
        
        # 随机缩放因子
        scale = random.uniform(*scale_range)
        
        # 新尺寸
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # 缩放
        scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        
        if scale > 1.0:
            # 如果放大了，需要裁剪到原尺寸
            start_x = (new_w - w) // 2
            start_y = (new_h - h) // 2
            result = scaled[start_y:start_y+h, start_x:start_x+w]
        else:
            # 如果缩小了，需要填充到原尺寸
            result = np.zeros((h, w, 3), dtype=image.dtype)
            start_x = (w - new_w) // 2
            start_y = (h - new_h) // 2
            result[start_y:start_y+new_h, start_x:start_x+new_w] = scaled
        
        return result
    
    def random_shear(self, image, max_shear=0.2):
        """
        随机剪切变形
        max_shear: 最大剪切强度
        """
        h, w = image.shape[:2]
        
        # 随机剪切参数
        shear_x = random.uniform(-max_shear, max_shear)
        shear_y = random.uniform(-max_shear, max_shear)
        
        # 剪切变换矩阵
        matrix = np.float32([
            [1, shear_x, 0],
            [shear_y, 1, 0]
        ])
        
        # 应用剪切
        sheared = cv2.warpAffine(image, matrix, (w, h), 
                               borderMode=cv2.BORDER_REFLECT_101)
        
        return sheared
    
    def apply_random_transform(self, image, transform_types=None, intensity=0.3):
        """
        应用随机变换（仅透视变换）
        transform_types: 要应用的变换类型列表
        intensity: 变换强度
        """
        result = image.copy()
        
        # 先应用旋转变换
        #result = self.random_rotation(result, max_angle=10)
        
        # 再应用透视变换
        result = self.random_perspective_transform(result, intensity)
        
        return result
    
    def process_image(self, image_path, output_dir, intensity=0.3, num_variants=1):
        """
        处理单张图片
        image_path: 输入图片路径
        output_dir: 输出目录
        intensity: 变形强度
        num_variants: 生成变体数量
        """
        try:
            # 读取图片
            image = cv2.imread(str(image_path))
            if image is None:
                print(f"无法读取图片: {image_path}")
                return False
            
            # 获取文件信息
            file_path = Path(image_path)
            file_stem = file_path.stem
            file_ext = file_path.suffix
            
            # 确保输出目录存在
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            success_count = 0
            
            for i in range(num_variants):
                # 应用随机变换
                transformed = self.apply_random_transform(image, intensity=intensity)
                
                # 生成输出文件名
                if num_variants == 1:
                    output_name = f"{file_stem}{self.output_suffix}{file_ext}"
                else:
                    output_name = f"{file_stem}{self.output_suffix}_{i+1}{file_ext}"
                
                output_path = output_dir / output_name
                
                # 保存图片
                if cv2.imwrite(str(output_path), transformed):
                    success_count += 1
                    print(f"已保存: {output_path}")
                else:
                    print(f"保存失败: {output_path}")
            
            return success_count > 0
            
        except Exception as e:
            print(f"处理图片 {image_path} 时出错: {str(e)}")
            return False
    
    def process_folder(self, input_folder, output_folder=None, intensity=0.3, num_variants=1):
        """
        处理文件夹中的所有图片
        input_folder: 输入文件夹路径
        output_folder: 输出文件夹路径（如果为None，则在输入文件夹下创建子文件夹）
        intensity: 变形强度
        num_variants: 每张图片生成的变体数量
        """
        input_path = Path(input_folder)
        
        if not input_path.exists():
            print(f"输入文件夹不存在: {input_folder}")
            return
        
        # 设置输出文件夹
        if output_folder is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 在输入文件夹的父目录下创建输出文件夹（同级）
            output_path = input_path.parent / f"{input_path.name}_transformed_{timestamp}"
        else:
            output_path = Path(output_folder)
        
        # 查找所有图片文件
        image_files = []
        for ext in self.supported_formats:
            image_files.extend(input_path.glob(f"*{ext}"))
            image_files.extend(input_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print(f"在文件夹 {input_folder} 中未找到支持的图片文件")
            return
        
        print(f"找到 {len(image_files)} 张图片")
        print(f"输出目录: {output_path}")
        print(f"变形强度: {intensity}")
        print(f"每张图片生成 {num_variants} 个变体")
        print("-" * 50)
        
        # 处理每张图片
        success_count = 0
        for i, image_file in enumerate(image_files, 1):
            print(f"处理第 {i}/{len(image_files)} 张: {image_file.name}")
            if self.process_image(image_file, output_path, intensity, num_variants):
                success_count += 1
        
        print("-" * 50)
        print(f"处理完成！成功处理 {success_count}/{len(image_files)} 张图片")
        print(f"输出目录: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='图片视角随机变形工具')
    parser.add_argument('input_folder', help='输入文件夹路径')
    parser.add_argument('-o', '--output', help='输出文件夹路径（可选）')
    parser.add_argument('-i', '--intensity', type=float, default=0.3, 
                       help='变形强度 (0.1-1.0，默认0.3)')
    parser.add_argument('-n', '--num_variants', type=int, default=1,
                       help='每张图片生成的变体数量（默认1）')
    
    args = parser.parse_args()
    
    # 验证参数
    if not (0.1 <= args.intensity <= 1.0):
        print("错误：变形强度必须在 0.1-1.0 之间")
        return
    
    if args.num_variants < 1:
        print("错误：变体数量必须大于0")
        return
    
    # 创建变形器并处理
    transformer = ImagePerspectiveTransformer()
    transformer.process_folder(
        args.input_folder, 
        args.output, 
        args.intensity, 
        args.num_variants
    )

if __name__ == "__main__":
    # 如果直接运行脚本，使用配置的路径
    input_folder = "/Users/a000/Documents/济生/医院拜访25/2511/何勇2511/科室"
    output_folder = "/Users/a000/Documents/济生/医院拜访25/2511/何勇2511/科室_变形"  # 将在输入文件夹下创建子文件夹
    intensity = 0.4  # 变形强度
    num_variants = 1  # 每张图片生成1个变体
    
    print("=" * 60)
    print("图片视角随机变形工具")
    print("=" * 60)
    
    transformer = ImagePerspectiveTransformer()
    transformer.process_folder(input_folder, output_folder, intensity, num_variants)