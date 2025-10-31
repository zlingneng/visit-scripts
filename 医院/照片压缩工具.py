#!/Users/a000/miniconda3/bin/python
# -*- coding: utf-8 -*-
"""
照片压缩工具
功能：将指定目录中大于1.5M的照片压缩到1M左右
"""

import os
import sys
import shutil
from PIL import Image
import pillow_heif
from pathlib import Path
import time

# 配置参数
SOURCE_DIR = "/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/照片4"
TARGET_SIZE_MB = 1.0  # 目标大小（MB）
MAX_SIZE_MB = 1.5     # 超过此大小才压缩
QUALITY_START = 85    # 初始压缩质量
QUALITY_MIN = 60      # 最低压缩质量

# 支持的图片格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heic', '.heif'}

def get_file_size_mb(file_path):
    """获取文件大小（MB）"""
    return os.path.getsize(file_path) / (1024 * 1024)

def compress_image(input_path, output_path, target_size_mb=1.0, quality_start=85, quality_min=60):
    """压缩图片到指定大小（优先保持尺寸，再调整质量）"""
    try:
        # 注册HEIF格式支持
        pillow_heif.register_heif_opener()
        
        # 打开图片
        with Image.open(input_path) as img:
            # 转换为RGB模式（如果需要）
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 获取原始尺寸
            original_width, original_height = img.size
            temp_path = output_path + '.temp'
            
            # 目标范围：0.8MB - 1.5MB 都可以接受
            target_min = target_size_mb * 0.8
            target_max = target_size_mb * 1.5
            
            # 优先策略：保持原始尺寸，调整质量
            quality = quality_start
            best_result = None
            
            # 在原始尺寸下寻找最佳质量
            while quality >= quality_min:
                img.save(temp_path, 'JPEG', quality=quality, optimize=True)
                size_mb = get_file_size_mb(temp_path)
                
                # 如果在目标范围内，直接使用
                if target_min <= size_mb <= target_max:
                    os.rename(temp_path, output_path)
                    return True, size_mb, quality, (original_width, original_height)
                
                # 记录最接近目标的结果
                if best_result is None or abs(size_mb - target_size_mb) < abs(best_result[1] - target_size_mb):
                    best_result = (quality, size_mb, (original_width, original_height))
                
                # 如果已经小于目标范围，停止降低质量
                if size_mb < target_min:
                    break
                    
                quality -= 3  # 更细粒度的调整
            
            # 如果原始尺寸下找到了可接受的结果，使用它
            if best_result and best_result[1] <= target_max * 1.5:  # 允许稍微超出一点
                img.save(output_path, 'JPEG', quality=best_result[0], optimize=True)
                return True, best_result[1], best_result[0], best_result[2]
            
            # 如果原始尺寸下效果不好，才考虑缩小尺寸
            scale_factors = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7]  # 更细粒度的缩放
            
            for scale_factor in scale_factors:
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                resized_img = img.resize((new_width, new_height), Image.Lanczos)
                
                # 在新尺寸下寻找合适的质量
                quality = quality_start
                while quality >= quality_min:
                    resized_img.save(temp_path, 'JPEG', quality=quality, optimize=True)
                    size_mb = get_file_size_mb(temp_path)
                    
                    # 如果在目标范围内，使用这个结果
                    if target_min <= size_mb <= target_max:
                        os.rename(temp_path, output_path)
                        return True, size_mb, quality, (new_width, new_height)
                    
                    # 如果已经小于目标，停止
                    if size_mb < target_min:
                        break
                        
                    quality -= 5
                
                # 如果这个尺寸下最高质量的结果在可接受范围内，使用它
                resized_img.save(temp_path, 'JPEG', quality=quality_start, optimize=True)
                size_mb = get_file_size_mb(temp_path)
                if size_mb <= target_max:
                    os.rename(temp_path, output_path)
                    return True, size_mb, quality_start, (new_width, new_height)
            
            # 最后的备选方案：使用70%尺寸和中等质量
            new_width = int(original_width * 0.7)
            new_height = int(original_height * 0.7)
            resized_img = img.resize((new_width, new_height), Image.Lanczos)
            resized_img.save(output_path, 'JPEG', quality=75, optimize=True)
            
            final_size = get_file_size_mb(output_path)
            return True, final_size, 75, (new_width, new_height)
            
    except Exception as e:
        print(f"压缩失败 {input_path}: {str(e)}")
        return False, 0, 0, (0, 0)
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

def process_directory(source_dir):
    """处理目录中的所有图片"""
    if not os.path.exists(source_dir):
        print(f"错误：目录不存在 {source_dir}")
        return
    
    print(f"开始处理目录: {source_dir}")
    print(f"压缩条件: 文件大小 > {MAX_SIZE_MB}MB")
    print(f"目标大小: {TARGET_SIZE_MB}MB")
    print("-" * 60)
    
    # 统计信息
    total_files = 0
    processed_files = 0
    skipped_files = 0
    failed_files = 0
    total_saved_mb = 0
    
    start_time = time.time()
    
    # 遍历目录中的所有文件
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            # 检查是否为支持的图片格式
            if file_ext not in SUPPORTED_FORMATS:
                continue
            
            total_files += 1
            
            try:
                # 检查文件大小
                original_size_mb = get_file_size_mb(file_path)
                
                if original_size_mb <= MAX_SIZE_MB:
                    print(f"跳过 {file} (大小: {original_size_mb:.2f}MB <= {MAX_SIZE_MB}MB)")
                    skipped_files += 1
                    continue
                
                print(f"处理 {file} (原始大小: {original_size_mb:.2f}MB)")
                
                # 创建备份文件名
                backup_path = file_path + '.backup'
                
                # 备份原文件
                if not os.path.exists(backup_path):
                    os.rename(file_path, backup_path)
                else:
                    # 如果备份已存在，说明之前处理过，直接处理备份文件
                    pass
                
                # 压缩图片
                success, final_size_mb, quality, new_dimensions = compress_image(
                    backup_path, file_path, TARGET_SIZE_MB, QUALITY_START, QUALITY_MIN
                )
                
                if success:
                    saved_mb = original_size_mb - final_size_mb
                    total_saved_mb += saved_mb
                    processed_files += 1
                    
                    print(f"  ✓ 压缩成功: {original_size_mb:.2f}MB → {final_size_mb:.2f}MB")
                    print(f"    节省空间: {saved_mb:.2f}MB, 质量: {quality}, 尺寸: {new_dimensions[0]}x{new_dimensions[1]}")
                else:
                    # 压缩失败，恢复原文件
                    if os.path.exists(backup_path):
                        os.rename(backup_path, file_path)
                    failed_files += 1
                    print(f"  ✗ 压缩失败")
                    
            except Exception as e:
                print(f"处理文件出错 {file}: {str(e)}")
                failed_files += 1
    
    # 输出统计结果
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print("\n" + "="*60)
    print("处理完成！")
    print(f"总文件数: {total_files}")
    print(f"已处理: {processed_files}")
    print(f"已跳过: {skipped_files}")
    print(f"失败: {failed_files}")
    print(f"总节省空间: {total_saved_mb:.2f}MB")
    print(f"处理时间: {elapsed_time:.1f}秒")
    
    if processed_files > 0:
        print(f"平均每个文件节省: {total_saved_mb/processed_files:.2f}MB")
        print(f"平均处理速度: {processed_files/elapsed_time:.1f}文件/秒")

def install_dependencies():
    """安装必要的依赖包"""
    try:
        import PIL
        import pillow_heif
        print("依赖包已安装")
        return True
    except ImportError as e:
        print(f"缺少依赖包，正在安装...")
        # 获取当前Python解释器路径
        python_executable = sys.executable
        print(f"使用Python解释器: {python_executable}")
        
        # 尝试使用当前Python解释器安装依赖
        try:
            import subprocess
            result = subprocess.run([
                python_executable, "-m", "pip", "install", 
                "-i", "https://mirrors.aliyun.com/pypi/simple/", 
                "Pillow", "pillow-heif"
            ], check=True, capture_output=True, text=True)
            print("依赖包安装成功")
            return True
        except subprocess.CalledProcessError as install_error:
            print(f"自动安装失败: {install_error}")
            print(f"错误详情: {install_error.stderr}")
            return False
        except Exception as general_error:
            print(f"安装过程中出现错误: {general_error}")
            return False

if __name__ == "__main__":
    print("照片压缩工具")
    print("=" * 40)
    
    # 检查并安装依赖
    if not install_dependencies():
        print("依赖包安装失败，请手动安装后再运行脚本")
        print("可以尝试在终端中运行以下命令:")
        print(f"{sys.executable} -m pip install -i https://mirrors.aliyun.com/pypi/simple/ Pillow pillow-heif")
        sys.exit(1)
    
    # 检查源目录是否存在
    if not os.path.exists(SOURCE_DIR):
        print(f"错误：源目录不存在 {SOURCE_DIR}")
        print("请修改脚本中的 SOURCE_DIR 变量为正确的路径")
        sys.exit(1)
    
    # 确认操作
    print(f"即将处理目录: {SOURCE_DIR}")
    print(f"压缩条件: 文件大小 > {MAX_SIZE_MB}MB")
    print(f"目标大小: {TARGET_SIZE_MB}MB")
    print("\n注意：原文件将被备份为 .backup 后缀")
    
    confirm = input("\n确认开始处理？(y/N): ")
    if confirm.lower() in ['y', 'yes', '是']:
        process_directory(SOURCE_DIR)
    else:
        print("操作已取消")