import openpyxl
import os
import json
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime


def read_excel_data(excel_file_path):
    workbook = openpyxl.load_workbook(excel_file_path)
    sheet = workbook["大门"]
    data_dict = {}
    text_data1 = []
    text_data2 = []
    text_data3 = []
    for row in sheet.iter_rows(min_row = 1, values_only=True):
        photo_name = str(row[0])  # 假设第一列数据是和图片名称对应的内容，转换为字符串方便后续匹配
        data_dict[photo_name] = {}
        data_dict[photo_name]["text1"] = row[18]  # 拜访时间
        data_dict[photo_name]["text2"] = row[4]  # 地址
        data_dict[photo_name]["text3"] = row[5]  # 拜访日期
        # 添加新的字段用于照片命名
        data_dict[photo_name]["terminal_name"] = row[1]  # 终端名称
        data_dict[photo_name]["visit_date"] = row[5]     # 拜访日期
        data_dict[photo_name]["visitor"] = row[9]        # 拜访人员
        data_dict[photo_name]["photo_type"] = row[17]    # 照片进出
        text_data1.append(row[18])
        text_data2.append(row[4])
        text_data3.append(row[5])
    return data_dict, text_data1, text_data2, text_data3


def load_watermark_config(config_path='config.json'):
    default_config = {
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
    "font_path": "/Users/a000/Downloads/zhangzhenghui/msyh.ttf"}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败，使用默认配置: {e}")
    return default_config


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
                try:
                    text3 = data_dict[photo_name_without_ext]["text3"].strftime("yyyy.mm.dd")
                except AttributeError:
                    text3 = data_dict[photo_name_without_ext]["text3"]

                text3 = datetime.strptime(text3, "%Y-%m-%d")
                weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                weekday = weekdays[text3.weekday()]
                text3 = text3.strftime("%Y.%m.%d")  # 转换为点分隔的日期格式显示
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
                image_folder2 = r'/Users/a000/Documents/济生/医院拜访25/贵州医院拜访250115-5/大门'
                font1 = ImageFont.truetype(font_path, size = font_size1)  # 根据需要调整字体和大小
                font2 = ImageFont.truetype(font_path, size = font_size2)  # 根据需要调整字体和大小
                font3 = ImageFont.truetype(font_path, size = font_size3)  # 根据需要调整字体和大小
                draw.text((x_position1, y_position1), text1, font = font1, fill = (255, 255, 255))  
                # 根据需要调整文字位置和颜色
                draw.text((x_position2, y_position2), text2, font = font2, fill = (255, 255, 255))  
                # 根据需要调整文字位置和颜色
                draw.text((x_position3, y_position3), text3, font = font3, fill = (255, 255, 255))  
                # 根据需要调整文字位置和颜色
                
                # 生成新的照片名称：终端名称-拜访日期-拜访人员-照片进出
                terminal_name = data_dict[photo_name_without_ext].get("terminal_name") or "未知终端"
                visit_date = data_dict[photo_name_without_ext].get("visit_date")
                visitor = data_dict[photo_name_without_ext].get("visitor") or "未知拜访人"
                photo_type = data_dict[photo_name_without_ext].get("photo_type")
                
                # 清理文件名中的非法字符
                def clean_filename(name):
                    if name is None:
                        return "未知"
                    # 移除或替换文件名中的非法字符
                    illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
                    for char in illegal_chars:
                        name = str(name).replace(char, '_')
                    return name.strip()
                
                terminal_name = clean_filename(terminal_name)
                visitor = clean_filename(visitor)
                
                # 格式化拜访日期
                if hasattr(visit_date, 'strftime'):
                    visit_date_str = visit_date.strftime("%Y.%m.%d")
                elif isinstance(visit_date, str):
                    try:
                        # 尝试将字符串解析为日期，然后格式化
                        date_obj = datetime.strptime(visit_date, "%Y-%m-%d")
                        visit_date_str = date_obj.strftime("%Y.%m.%d")
                    except (ValueError, TypeError):
                        visit_date_str = visit_date
                else:
                    visit_date_str = str(visit_date) if visit_date else "未知日期"
                
                # 格式化照片类型
                if photo_type == 1.0:
                    photo_type_str = "进"
                elif photo_type == 2.0:
                    photo_type_str = "出"
                else:
                    photo_type_str = "未知"
                
                # 获取原始文件扩展名
                file_extension = os.path.splitext(image_file)[1]
                
                # 生成新文件名
                new_filename = f"{visit_date_str}-{terminal_name}-{visitor}-{photo_type_str}{file_extension}"
                
                print(f"保存照片: {new_filename}")
                img.save(os.path.join(image_folder2, new_filename))
            else:
                print(f"在Excel数据中未找到与图片 {image_file} 对应的记录")
        except IndexError:
            print(f"文字列表长度小于图片数量，无法为所有图片添加文字：{image_file}")
        except FileNotFoundError:
            print(f"找不到图片文件：{image_file}")


excel_file_path = r'/Users/a000/Documents/济生/医院拜访25/贵州医院拜访250115-5/贵州医院拜访250115-5_修改后.xlsx'
image_folder = r'/Users/a000/Pictures/2501-5'
text_list = read_excel_data(excel_file_path)
add_text_to_images(image_folder, text_list)