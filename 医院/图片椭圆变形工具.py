#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片椭圆变形工具
对图片的四个顶点进行椭圆范围内的随机偏移，然后进行透视变换
"""

import cv2
import numpy as np
import os
from pathlib import Path
import random
from typing import Tuple, List

def generate_ellipse_point(center_x: float, center_y: float, a: float, b: float, img_width: int, img_height: int) -> Tuple[float, float]:
    """
    在四分之一椭圆内生成随机点，确保在图片边界内
    使用平缓的概率密度分布，在椭圆1/90处概率密度最高
    """
    max_attempts = 1000
    
    for _ in range(max_attempts):
        # 根据角点位置确定有效的角度范围（四分之一椭圆，朝向图片内部）
        if center_x == 0 and center_y == 0:  # 左上角，朝向右下
            theta_min, theta_max = 0, np.pi/2
        elif center_x == img_width and center_y == 0:  # 右上角，朝向左下
            theta_min, theta_max = np.pi/2, np.pi
        elif center_x == img_width and center_y == img_height:  # 右下角，朝向左上
            theta_min, theta_max = np.pi, 3*np.pi/2
        else:  # 左下角 (0, img_height)，朝向右上
            theta_min, theta_max = 3*np.pi/2, 2*np.pi
        
        # 在有效角度范围内均匀分布
        theta = np.random.uniform(theta_min, theta_max)
        
        # 径向距离的概率密度函数
        # 峰值位置在椭圆半径的1/2处
        peak_ratio = 0.5  # 峰值在椭圆半径的1/2处
        
        # 生成0到1之间的随机数
        u = np.random.random()
        
        # 两边各一半概率分布，从峰值到边界平缓衰减
        # 边界处概率为0，原点处可以不为0
        alpha = 3.0  # 控制平缓程度的参数
        
        if u < 0.5:
            # 前半部分：从0到peak_ratio，平缓增长到峰值
            normalized_u = 2 * u  # 归一化到[0,1]
            # 使用平方根函数实现从原点到峰值的平缓增长
            r = peak_ratio * (normalized_u ** (1.0/alpha))
        else:
            # 后半部分：从peak_ratio到1，平缓衰减到边界（边界为0）
            normalized_u = 2 * (u - 0.5)  # 归一化到[0,1]
            # 使用余弦函数的变形实现从峰值到边界的平缓衰减
            # 确保边界处概率为0
            decay_factor = (1 - normalized_u) ** alpha
            r = peak_ratio + (1 - peak_ratio) * (1 - decay_factor)
        
        # 转换为椭圆坐标，确保朝向图片内部
        if center_x == 0 and center_y == 0:  # 左上角
            dx = r * a * np.cos(theta)  # 向右
            dy = r * b * np.sin(theta)  # 向下
        elif center_x == img_width and center_y == 0:  # 右上角
            dx = -r * a * np.abs(np.cos(theta))  # 向左
            dy = r * b * np.abs(np.sin(theta))   # 向下
        elif center_x == img_width and center_y == img_height:  # 右下角
            dx = -r * a * np.abs(np.cos(theta))  # 向左
            dy = -r * b * np.abs(np.sin(theta))  # 向上
        else:  # 左下角
            dx = r * a * np.abs(np.cos(theta))   # 向右
            dy = -r * b * np.abs(np.sin(theta))  # 向上
        
        # 计算新的坐标
        new_x = center_x + dx
        new_y = center_y + dy
        
        # 检查是否在图片边界内
        if 0 <= new_x <= img_width and 0 <= new_y <= img_height:
            return new_x, new_y
    
    # 如果多次尝试都失败，返回原点（安全回退）
    return center_x, center_y

def get_new_corners(img_height: int, img_width: int) -> List[Tuple[float, float]]:
    """
    获取新的四个角点坐标
    每个角点在以原角点为中心的四分之一椭圆内随机选择
    椭圆的长轴和短轴都是图片长宽的1/40
    概率密度在椭圆半径1/2处最高，两边各一半概率分布
    从峰值到边界平缓衰减，边界处概率为0
    确保所有点都在图片边界内
    """
    # 椭圆的半轴长度
    a = img_width / 10  # 水平半轴
    b = img_height / 10  # 垂直半轴
    
    # 原始四个角点
    original_corners = [
        (0, 0),  # 左上
        (img_width, 0),  # 右上
        (img_width, img_height),  # 右下
        (0, img_height)  # 左下
    ]
    
    new_corners = []
    for corner_x, corner_y in original_corners:
        new_x, new_y = generate_ellipse_point(corner_x, corner_y, a, b, img_width, img_height)
        new_corners.append((new_x, new_y))
    
    return new_corners

def transform_image(image: np.ndarray) -> np.ndarray:
    """
    对图片进行透视变换
    由于新角点都在原图内部，我们需要反向变换：
    从新角点变换回原始矩形，这样可以消除黑边
    """
    height, width = image.shape[:2]
    
    # 获取新的四个角点（这些点都在图片内部）
    new_corners = get_new_corners(height, width)
    src_points = np.float32(new_corners)  # 源点：新的角点
    
    # 目标四个角点（原始矩形角点）
    dst_points = np.float32([
        [0, 0],  # 左上
        [width, 0],  # 右上
        [width, height],  # 右下
        [0, height]  # 左下
    ])
    
    # 计算透视变换矩阵（从新角点到原始角点）
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
    
    # 应用透视变换
    transformed = cv2.warpPerspective(image, matrix, (width, height))
    
    return transformed

def process_single_image(input_path: str, output_path: str) -> bool:
    """
    处理单张图片
    """
    try:
        # 读取图片
        image = cv2.imread(input_path)
        if image is None:
            print(f"无法读取图片: {input_path}")
            return False
        
        # 进行变换
        transformed_image = transform_image(image)
        
        # 保存结果
        success = cv2.imwrite(output_path, transformed_image)
        if success:
            print(f"处理完成: {input_path} -> {output_path}")
            return True
        else:
            print(f"保存失败: {output_path}")
            return False
            
    except Exception as e:
        print(f"处理图片时出错 {input_path}: {str(e)}")
        return False

def process_directory(input_dir: str, output_dir: str = None) -> None:
    """
    处理目录下的所有图片
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"输入目录不存在: {input_dir}")
        return
    
    # 如果没有指定输出目录，在输入目录下创建processed子目录
    if output_dir is None:
        output_path = input_path / "processed"
    else:
        output_path = Path(output_dir)
    
    # 创建输出目录
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    
    # 处理所有图片
    processed_count = 0
    for file_path in input_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            output_file = output_path / f"transformed_{file_path.name}"
            if process_single_image(str(file_path), str(output_file)):
                processed_count += 1
    
    print(f"\n处理完成！共处理了 {processed_count} 张图片")
    print(f"输出目录: {output_path}")

def main():
    """
    主函数
    """
    print("图片椭圆变形工具")
    print("=" * 50)
    
    # 配置参数
    input_directory = "/Users/a000/Documents/济生/医院拜访25/2503/张丹凤2503/照片编辑"  # 输入目录
    output_directory = None  # 输出目录，None表示在输入目录下创建processed子目录
    
    print(f"输入目录: {input_directory}")
    print(f"输出目录: {output_directory if output_directory else '输入目录/processed'}")
    print("\n开始处理...")
    
    # 处理图片
    process_directory(input_directory, output_directory)

if __name__ == "__main__":
    main()