from PIL import Image, ImageDraw, ImageFont
import os

def text_to_png(text_content, output_filename="flowchart.png", font_path=None, font_size=15, bg_color=(255, 255, 255), text_color=(0, 0, 0), padding=20):
    """
    将多行文本内容转换为PNG图片。

    参数:
        text_content (str): 要转换为图片的文本内容，多行用换行符分隔。
        output_filename (str): 输出PNG图片的文件名。
        font_path (str, optional): TTF字体文件的路径。如果为None，将尝试使用默认字体。
        font_size (int): 字体大小。
        bg_color (tuple): 图片背景颜色 (R, G, B)。
        text_color (tuple): 文本颜色 (R, G, B)。
        padding (int): 图片四周的内边距。
    """
    lines = text_content.strip().split('\n')

    # 尝试加载字体
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            # 尝试加载一个常见的系统字体作为备选
            try:
                font = ImageFont.truetype("arial.ttf", font_size) # Windows/Linux
                print("使用 Arial 字体。")
            except IOError:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", font_size) # Linux
                    print("使用 DejaVuSans 字体。")
                except IOError:
                    try:
                        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size) # macOS (路径可能变化)
                        print("使用 Helvetica 字体。")
                    except IOError:
                        font = ImageFont.load_default() # Pillow的默认字体
                        print("警告: 未找到指定或备用字体，使用Pillow默认字体。效果可能不佳。")
    except Exception as e:
        print(f"加载字体错误: {e}. 使用Pillow默认字体。")
        font = ImageFont.load_default()

    # 计算文本尺寸
    line_heights = []
    max_width = 0
    # Pillow 10.0.0 之后 ImageDraw.textbbox 替代 getsize
    try:
        # 创建一个临时的 ImageDraw 对象来获取文本框大小
        temp_image = Image.new("RGB", (1, 1))
        draw_temp = ImageDraw.Draw(temp_image)
        for line in lines:
            # textbbox 返回 (left, top, right, bottom)
            bbox = draw_temp.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            line_heights.append(text_height)
            if text_width > max_width:
                max_width = text_width
    except AttributeError: # 兼容旧版 Pillow (<10.0.0)
        print("警告: 使用旧版Pillow的getsize方法。建议更新Pillow库以获得更准确的文本尺寸计算。")
        for line in lines:
            text_width, text_height = font.getsize(line) # type: ignore
            line_heights.append(text_height) # getsize 返回的 height 通常是基于字体的，可能不是非常精确的行高
            if text_width > max_width:
                max_width = text_width


    # 实际使用的行高，可以基于平均值或最大值，或者固定一个比例
    # 为了简单，我们使用字体大小作为基础行高，并增加一些间距
    actual_line_height = font_size * 1.5 # 或者 max(line_heights) * 1.2 if line_heights else font_size * 1.5

    total_calculated_text_height = 0
    if line_heights:
        total_calculated_text_height = sum(line_heights) + (len(lines) -1) * (actual_line_height - font_size) if len(lines) > 1 else sum(line_heights)

    if not line_heights: # 如果没有行，设置一个默认高度
        total_height = padding * 2
    else:
        total_height = int(total_calculated_text_height)


    # 创建图片
    img_width = int(max_width + padding * 2)
    img_height = int(total_height + padding * 2)
    if img_width <= padding*2 : img_width = 300 # 最小宽度，防止文本为空时图片过小
    if img_height <= padding*2 : img_height = 100 # 最小高度

    image = Image.new("RGB", (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(image)

    # 逐行绘制文本
    y_text = padding
    current_line_height_offset = 0
    if line_heights: # 确保 line_heights 非空
      current_line_height_offset = (actual_line_height - line_heights[0]) / 2 if line_heights else 0


    for i, line in enumerate(lines):
        # Pillow 10.0.0+ .text() , 旧版 .textsize()
        try:
            # bbox = draw.textbbox((padding, y_text), line, font=font) # 使用textbbox获取精确位置可能导致重叠，如果行高控制不当
            draw.text((padding, y_text + current_line_height_offset), line, font=font, fill=text_color)
            # 使用基于 actual_line_height 的固定行高或者bbox计算的行高
            if line_heights : # 确保 line_heights 和索引 i 有效
                 y_text += actual_line_height # 使用固定的行高
                 if i + 1 < len(line_heights):
                     current_line_height_offset = (actual_line_height - line_heights[i+1]) / 2
                 elif i + 1 == len(line_heights) and len(line_heights) == 1: # last line single line
                     current_line_height_offset = (actual_line_height - line_heights[i]) / 2

            else: # 如果 line_heights 为空（例如，文本内容为空）
                 y_text += actual_line_height


        except AttributeError: # 兼容旧版
            draw.text((padding, y_text), line, font=font, fill=text_color)
            y_text += actual_line_height


    # 保存图片
    try:
        image.save(output_filename)
        print(f"流程图已保存为: {output_filename}")
    except Exception as e:
        print(f"保存图片失败: {e}")

# --- 主程序 ---
if __name__ == "__main__":
    input_file = "input.txt"
    flowchart_text = ""

    if os.path.exists(input_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                flowchart_text = f.read()
            if not flowchart_text.strip():
                print(f"警告: '{input_file}' 为空。将生成一个空白图片。")
                flowchart_text = " " # 使用一个空格确保能生成图片
        except Exception as e:
            print(f"读取文件 '{input_file}' 失败: {e}")
            flowchart_text = f"错误: 无法读取 {input_file}"
    else:
        print(f"错误: 输入文件 '{input_file}' 未找到。请创建该文件并填入流程图文本。")
        flowchart_text = f"错误: 文件 {input_file} 未找到。"

    # 指定字体路径，确保你的系统上有这个字体或者修改为可用的字体路径
    # 例如，在Windows上可能是 "C:/Windows/Fonts/msyh.ttc" (微软雅黑) 或 "simsun.ttc" (宋体)
    # 在Linux上可能是 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    # 如果不确定，可以先设置为 None，让程序尝试默认字体
    # 为了更好地显示中文和特殊字符，推荐使用支持这些字符的字体
    
    # 尝试常见的字体名称
    font_candidates = ["simsun.ttc", "msyh.ttc", "ukai.ttc", "NotoSansCJK-Regular.ttc"] 
    font_file_path = None
    
    for font_name in font_candidates:
        if os.path.exists(font_name): # 检查当前目录
            font_file_path = font_name
            print(f"在当前目录找到字体: {font_name}")
            break
        # 检查 Windows 字体目录
        elif os.name == 'nt' and os.path.exists(os.path.join(os.environ.get('SYSTEMROOT', 'C:/Windows'), 'Fonts', font_name)):
            font_file_path = os.path.join(os.environ.get('SYSTEMROOT', 'C:/Windows'), 'Fonts', font_name)
            print(f"在系统字体目录找到字体: {font_file_path}")
            break
        # 检查 macOS 常见字体目录 (简单示例)
        elif os.uname().sysname == 'Darwin':
             if os.path.exists(f"/System/Library/Fonts/{font_name}"):
                 font_file_path = f"/System/Library/Fonts/{font_name}"
                 print(f"在系统字体目录找到字体: {font_file_path}")
                 break
             elif os.path.exists(f"/Library/Fonts/{font_name}"):
                 font_file_path = f"/Library/Fonts/{font_name}"
                 print(f"在系统字体目录找到字体: {font_file_path}")
                 break
        # 检查 Linux 常见字体目录 (简单示例)


    if not font_file_path:
        print("注意: 未在当前目录或常见系统路径找到指定的候选字体。将尝试Pillow默认字体或系统默认字体。")

    text_to_png(flowchart_text, output_filename="text_flowchart.png", font_path=font_file_path, font_size=14, padding=30)
