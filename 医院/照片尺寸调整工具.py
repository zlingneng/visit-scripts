#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片尺寸调整工具
功能：根据照片的长宽比例进行不同的尺寸调整
- 长>宽的照片：长度缩放到1600像素
- 长<宽的照片：宽度缩放到1700像素
"""

import os
import sys
from pathlib import Path

# 依赖导入将在依赖检查后进行

# 配置参数 - 请根据实际需要修改这些参数
SOURCE_DIR = "/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/照片4"  # 源照片目录
OUTPUT_DIR = "/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/照片4_处理后"  # 输出目录
RESIZE_LONG_EDGE = 1600  # 长边目标像素（长>宽时）
RESIZE_SHORT_EDGE = 1700  # 短边目标像素（长<宽时）

# 支持的图片格式
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.heic', '.heif'}

def install_dependencies():
    """安装必要的依赖包"""
    try:
        import PIL
        import pillow_heif
        print("✓ 依赖包已安装")
        # 导入模块
        global Image, pillow_heif
        from PIL import Image
        import pillow_heif
        return True
    except ImportError:
        print("缺少依赖包，正在安装...")
        try:
            import subprocess
            # 分别安装包以避免版本冲突
            packages = ["Pillow", "pillow-heif"]
            for package in packages:
                print(f"正在安装 {package}...")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", 
                    "-i", "https://mirrors.aliyun.com/pypi/simple/", 
                    "--force-reinstall",  # 强制重新安装以解决版本冲突
                    "--no-cache-dir",     # 不使用缓存
                    package
                ], check=True, capture_output=True, text=True)
                print(f"✓ {package} 安装成功")
            
            print("✓ 依赖包安装成功")
            # 安装成功后导入模块
            global Image, pillow_heif
            from PIL import Image
            import pillow_heif
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ 自动安装失败: {e}")
            print("请手动安装依赖包:")
            print(f"  {sys.executable} -m pip install -i https://mirrors.aliyun.com/pypi/simple/ Pillow pillow-heif")
            return False
        except Exception as e:
            print(f"✗ 安装过程中出现错误: {e}")
            return False

def resize_image_by_ratio(image_path, output_path):
    """根据长宽比例调整图片尺寸"""
    try:
        # 注册HEIF格式支持
        pillow_heif.register_heif_opener()
        
        # 打开图片
        with Image.open(image_path) as img:
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
            print(f"  原始尺寸: {original_width}x{original_height}")
            
            # 根据长宽比例决定缩放方式
            if original_width > original_height:
                # 长>宽：将长度缩放到1600像素
                new_width = RESIZE_LONG_EDGE
                new_height = int(original_height * (RESIZE_LONG_EDGE / original_width))
                print(f"  缩放类型: 长>宽 -> 长度缩放到{RESIZE_LONG_EDGE}px")
            elif original_width < original_height:
                # 长<宽：将宽度缩放到1700像素
                new_width = RESIZE_SHORT_EDGE
                new_height = int(original_height * (RESIZE_SHORT_EDGE / original_width))
                print(f"  缩放类型: 长<宽 -> 宽度缩放到{RESIZE_SHORT_EDGE}px")
            else:
                # 正方形图片：使用长边规则
                new_width = RESIZE_LONG_EDGE
                new_height = RESIZE_LONG_EDGE
                print(f"  缩放类型: 正方形 -> 长宽都缩放到{RESIZE_LONG_EDGE}px")
            
            # 调整图片尺寸
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 保存图片
            resized_img.save(output_path, 'JPEG', quality=90, optimize=True)
            print(f"  调整后尺寸: {new_width}x{new_height}")
            return True
            
    except Exception as e:
        print(f"  处理失败: {str(e)}")
        return False

def process_directory(source_dir, output_dir):
    """处理目录中的所有图片"""
    # 检查源目录是否存在
    if not os.path.exists(source_dir):
        print(f"错误：源目录不存在 {source_dir}")
        return False
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"开始处理目录: {source_dir}")
    print(f"输出目录: {output_dir}")
    print("-" * 60)
    
    # 统计信息
    total_files = 0
    processed_files = 0
    failed_files = 0
    
    # 遍历目录中的所有文件
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = Path(file).suffix.lower()
            
            # 检查是否为支持的图片格式
            if file_ext not in SUPPORTED_FORMATS:
                continue
            
            total_files += 1
            print(f"处理 {file}:")
            
            try:
                # 计算相对路径以保持目录结构
                relative_path = os.path.relpath(file_path, source_dir)
                output_path = os.path.join(output_dir, relative_path)
                
                # 确保输出目录存在
                output_path_obj = Path(output_path)
                output_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                # 如果是JPEG/JPG且已经是目标格式，直接复制
                if file_ext in ('.jpg', '.jpeg'):
                    # 先尝试直接调整尺寸
                    if resize_image_by_ratio(file_path, str(output_path_obj.with_suffix('.jpg'))):
                        processed_files += 1
                        print(f"  ✓ 处理成功")
                    else:
                        failed_files += 1
                        print(f"  ✗ 处理失败")
                else:
                    # 其他格式转换为JPG
                    if resize_image_by_ratio(file_path, str(output_path_obj.with_suffix('.jpg'))):
                        processed_files += 1
                        print(f"  ✓ 处理成功并转换为JPG")
                    else:
                        failed_files += 1
                        print(f"  ✗ 处理失败")
                        
            except Exception as e:
                print(f"处理文件出错 {file}: {str(e)}")
                failed_files += 1
            
            print()  # 空行分隔
    
    # 输出统计结果
    print("=" * 60)
    print("处理完成!")
    print(f"总文件数: {total_files}")
    print(f"成功处理: {processed_files}")
    print(f"处理失败: {failed_files}")
    print(f"输出目录: {output_dir}")
    
    return True

def main():
    print("照片尺寸调整工具")
    print("=" * 40)
    print(f"长>宽的照片：长度缩放到 {RESIZE_LONG_EDGE} 像素")
    print(f"长<宽的照片：宽度缩放到 {RESIZE_SHORT_EDGE} 像素")
    print()
    
    # 检查并安装依赖
    if not install_dependencies():
        print("依赖包安装失败，请手动安装后再运行脚本")
        sys.exit(1)
    
    # 确认操作
    print(f"源目录: {SOURCE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    
    confirm = input("\n确认开始处理？(y/N): ")
    if confirm.lower() in ['y', 'yes', '是']:
        process_directory(SOURCE_DIR, OUTPUT_DIR)
    else:
        print("操作已取消")

if __name__ == "__main__":
    main()