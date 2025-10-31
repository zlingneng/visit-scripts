from datetime import datetime
import openpyxl
import os
from PIL import Image, ImageDraw, ImageFont


def read_excel_data(excel_file_path):
    workbook = openpyxl.load_workbook(excel_file_path)
    sheet = workbook["拜访数据"]
    data_dict = {}
    text_data1 = []
    text_data2 = []
    text_data3 = []
    for row in sheet.iter_rows(min_row = 1, values_only=True):
        photo_name = str(row[0])  # 假设第一列数据是和图片名称对应的内容，转换为字符串方便后续匹配
        data_dict[photo_name] = {}
        data_dict[photo_name]["text1"] = row[6]
        data_dict[photo_name]["text2"] = row[4]
        data_dict[photo_name]["text3"] = row[5]
        text_data1.append(row[6])
        text_data2.append(row[4])
        text_data3.append(row[5])
    return data_dict, text_data1, text_data2, text_data3


def load_watermark_config():
    # 内置配置，无需外部配置文件
    config = {
        "text1": {
            "x_ratio": 0.05,
            "y_ratio": 0.78,
            "font_size_ratio": 0.065
        },
        "text2": {
            "x_ratio": 0.05,
            "y_ratio": 0.9,
            "font_size_ratio": 0.025
        },
        "text3": {
            "x_ratio": 0.05,
            "y_ratio": 0.871,
            "font_size_ratio": 0.025
        },
        "font_path": "/Users/a000/Downloads/zhangzhenghui/msyh.ttf"
    }
    return config


def add_text_to_images(image_folder, text_list):
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith('.jpeg') 
                   or f.lower().endswith('.png') or f.lower().endswith('.jpg') or 
                   f.lower().endswith('.webp')]
    data_dict, text_data1, text_data2, text_data3 = text_list
    for image_file in image_files:
        try:
            img = Image.open(os.path.join(image_folder, image_file))
            width, height = img.size
            draw = ImageDraw.Draw(img)

            photo_name_without_ext = os.path.splitext(image_file)[0]  # 获取图片名称（去掉扩展名）
            if photo_name_without_ext in data_dict:  # 判断该图片名称是否在Excel数据字典中有对应记录
                #text1 = data_dict[photo_name_without_ext]["text1"].strftime("%H:%M")
                try:
                    # 尝试将值转换为时间格式并格式化
                    text1 = data_dict[photo_name_without_ext]["text1"].strftime("%H:%M")
                except AttributeError:
                    # 如果不是时间格式（没有strftime方法），则保留原始字符串
                    text1 = data_dict[photo_name_without_ext]["text1"]
                text2 = data_dict[photo_name_without_ext]["text2"]
                text3 = data_dict[photo_name_without_ext]["text3"]
                
                # 如果text3已经是datetime对象，直接使用
                if isinstance(text3, datetime):
                    pass  # 已经是datetime对象，无需处理
                elif isinstance(text3, str):
                    # 尝试解析多种日期格式
                    date_formats = ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"]
                    parsed = False
                    for fmt in date_formats:
                        try:
                            text3 = datetime.strptime(text3, fmt)
                            parsed = True
                            break
                        except ValueError:
                            continue
                    
                    if not parsed:
                        raise ValueError(f"无法解析日期格式: {text3}，支持的格式: {', '.join(date_formats)}")
                else:
                    raise ValueError(f"text3必须是datetime对象或字符串，当前类型: {type(text3)}")
                weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                weekday = weekdays[text3.weekday()]
                text3 = text3.strftime("%Y.%m.%d")
                text3 = f"{text3} {weekday}"

                # 加载水印配置
                config = load_watermark_config()
                
                # 根据配置计算位置和字体大小
                x_position1 = int(width * config['text1']['x_ratio'])
                y_position1 = int(height * config['text1']['y_ratio'])
                font_size1 = int(height * config['text1']['font_size_ratio'])
                
                x_position2 = int(width * config['text2']['x_ratio'])
                y_position2 = int(height * config['text2']['y_ratio'])
                font_size2 = int(height * config['text2']['font_size_ratio'])
                
                x_position3 = int(width * config['text3']['x_ratio'])
                y_position3 = int(height * config['text3']['y_ratio'])
                font_size3 = int(height * config['text3']['font_size_ratio'])
                
                font_path = config['font_path']
                image_folder2 = image_folderout
                font1 = ImageFont.truetype(font_path, size = font_size1)  # 根据需要调整字体和大小
                font2 = ImageFont.truetype(font_path, size = font_size2)  # 根据需要调整字体和大小
                font3 = ImageFont.truetype(font_path, size = font_size3)  # 根据需要调整字体和大小
                draw.text((x_position1, y_position1), text1, font = font1, fill = (255, 255, 255))  
                # 根据需要调整文字位置和颜色
                draw.text((x_position2, y_position2), text2, font = font2, fill = (255, 255, 255))  
                # 根据需要调整文字位置和颜色
                draw.text((x_position3, y_position3), text3, font = font3, fill = (255, 255, 255))  
                # 根据需要调整文字位置和颜色
                
                # 添加右下角"水印相机"文字，30%透明度
                watermark_text = "水印相机"
                watermark_font_size = int(height * 0.035)  # 字体大小为图片高度的3%
                watermark_font = ImageFont.truetype(font_path, size=watermark_font_size)
                
                # 获取文字尺寸
                bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # 计算右下角位置（留一些边距）
                watermark_x = width - text_width - int(width * 0.04)  # 右边距为图片宽度的2%
                watermark_y = height - text_height - int(height * 0.04)  # 下边距为图片高度的2%
                
                # 创建半透明文字（30%透明度，即70%不透明度）
                # 创建一个临时图像用于绘制半透明文字
                txt_img = Image.new('RGBA', img.size, (255, 255, 255, 0))
                txt_draw = ImageDraw.Draw(txt_img)
                txt_draw.text((watermark_x, watermark_y), watermark_text, font=watermark_font, fill=(255, 255, 255, int(255 * 0.75)))
                
                # 将半透明文字合成到原图上
                img = Image.alpha_composite(img.convert('RGBA'), txt_img).convert('RGB')
                
                img.save(os.path.join(image_folder2, f"{image_file}"))
            else:
                print(f"在Excel数据中未找到与图片 {image_file} 对应的记录")
        except IndexError:
            print(f"文字列表长度小于图片数量，无法为所有图片添加文字：{image_file}")
        except FileNotFoundError:
            print(f"找不到图片文件：{image_file}")


excel_file_path = r'/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/贵州医生拜访2510-何勇-蔡林川-周星贤-整理.xlsx'
image_folder = r'/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/照片3'
image_folderout = r'/Users/a000/Documents/济生/医院拜访25/2510/何勇2510/照片4'
text_list = read_excel_data(excel_file_path)
add_text_to_images(image_folder, text_list)