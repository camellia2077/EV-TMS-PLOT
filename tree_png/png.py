from PIL import Image, ImageDraw, ImageFont
import os
import html # 用于转义HTML特殊字符

# --- 用于 PDF 的 DPI 设置 ---
PDF_DPI = 300.0

def points_to_pixels(points, dpi=PDF_DPI):
    """将点单位转换为像素单位"""
    return int(points * dpi / 72.0)

# --- 原有的 text_to_png 函数 ---
def text_to_png(text_content, output_filename="flowchart.png", font_path=None, font_size=15,
                bg_color=(255, 255, 255), text_color=(0, 0, 0), padding=20, scale_factor=2.0):
    lines = text_content.strip().split('\n')
    scaled_font_size = int(font_size * scale_factor)
    scaled_padding = int(padding * scale_factor)
    try:
        if font_path and os.path.exists(font_path): font = ImageFont.truetype(font_path, scaled_font_size)
        else: # Fallback
            try: font = ImageFont.truetype("arial.ttf", scaled_font_size)
            except IOError: font = ImageFont.load_default()
    except Exception as e:
        print(f"PNG: Font loading error: {e}"); font = ImageFont.load_default()

    line_actual_heights = []
    max_width = 0
    try: # Pillow >= 10
        temp_image = Image.new("RGB", (1,1)); draw_temp = ImageDraw.Draw(temp_image)
        for line in lines:
            bbox = draw_temp.textbbox((0,0), line, font=font)
            text_width = bbox[2] - bbox[0]; text_height = bbox[3] - bbox[1]
            line_actual_heights.append(text_height)
            if text_width > max_width: max_width = text_width
    except AttributeError: # Pillow < 10
        for line in lines:
            # getsize is deprecated and will be removed in Pillow 10 (2023-07-01).
            # Use getbbox or getlength instead.
            try:
                text_width, text_height = font.getsize(line) # type: ignore
            except AttributeError: # Even older Pillow or specific font issue
                 bbox = font.getbbox(line)
                 text_width = bbox[2] - bbox[0]
                 text_height = bbox[3] - bbox[1]
            line_actual_heights.append(text_height)
            if text_width > max_width: max_width = text_width
    
    line_spacing_ratio = 1.5
    scaled_line_height_for_stepping = int(scaled_font_size * line_spacing_ratio)
    total_text_block_height = 0
    if lines and line_actual_heights:
        total_text_block_height = sum(line_actual_heights) + max(0, len(lines) - 1) * (scaled_line_height_for_stepping - scaled_font_size)
        if not line_actual_heights : total_text_block_height = scaled_padding 
    elif lines: total_text_block_height = len(lines) * scaled_line_height_for_stepping
    else: total_text_block_height = scaled_padding 

    img_width = int(max_width + scaled_padding * 2)
    img_height = int(total_text_block_height + scaled_padding * 2)
    if img_width <= scaled_padding * 2 : img_width = int(300 * scale_factor) 
    if img_height <= scaled_padding * 2 : img_height = int(100 * scale_factor)

    image = Image.new("RGB", (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(image)
    y_text = scaled_padding
    for i, line in enumerate(lines):
        draw.text((scaled_padding, y_text), line, font=font, fill=text_color)
        if i < len(lines) - 1:
            y_text += scaled_line_height_for_stepping
        elif line_actual_heights: 
            pass 
    try:
        image.save(output_filename)
        print(f"流程图已保存为 PNG: {output_filename} (尺寸: {img_width}x{img_height})")
    except Exception as e: print(f"保存 PNG 图片失败: {e}")


# --- 原有的 text_to_pdf 函数 ---
def text_to_pdf(text_content, output_filename="flowchart.pdf", font_path=None, font_size_pt=12,
                bg_color_rgb=(255, 255, 255), text_color_rgb=(0, 0, 0), padding_pt=36):
    lines = text_content.strip().split('\n')
    font_size_px = points_to_pixels(font_size_pt, PDF_DPI)
    padding_px = points_to_pixels(padding_pt, PDF_DPI)
    
    pil_font = None
    try:
        if font_path and os.path.exists(font_path):
            pil_font = ImageFont.truetype(font_path, font_size_px)
            print(f"PDF: 使用字体 {font_path} (大小: {font_size_px}px 用于绘制, 对应 {font_size_pt}pt)")
        else:
            try:
                pil_font = ImageFont.truetype("arial.ttf", font_size_px)
                print(f"PDF: 使用 Arial 字体 (大小: {font_size_px}px)")
            except IOError:
                pil_font = ImageFont.load_default()
                print("PDF: 警告: 未找到 Arial, 使用Pillow默认字体 (可能不支持缩放)。")
    except Exception as e:
        print(f"PDF: 字体加载错误: {e}. 使用Pillow默认字体。")
        pil_font = ImageFont.load_default()

    line_actual_heights_px = []
    max_width_px = 0
    try: # Pillow >= 10.0.0
        temp_image = Image.new("RGB", (1,1))
        draw_temp = ImageDraw.Draw(temp_image)
        for line in lines:
            bbox = draw_temp.textbbox((0,0), line, font=pil_font)
            text_width_px = bbox[2] - bbox[0]
            text_height_px = bbox[3] - bbox[1]
            line_actual_heights_px.append(text_height_px)
            if text_width_px > max_width_px:
                max_width_px = text_width_px
    except AttributeError: # Pillow < 10.0.0
        for line in lines:
            try:
                text_width_px, text_height_px = pil_font.getsize(line) # type: ignore
            except AttributeError: # Even older Pillow or specific font issue
                 bbox = pil_font.getbbox(line)
                 text_width_px = bbox[2] - bbox[0]
                 text_height_px = bbox[3] - bbox[1]
            line_actual_heights_px.append(text_height_px)
            if text_width_px > max_width_px:
                max_width_px = text_width_px
    
    line_height_step_px = points_to_pixels(font_size_pt * 1.5, PDF_DPI)
    total_text_block_height_px = 0
    if lines and line_actual_heights_px:
        total_text_block_height_px = (len(lines) - 1) * line_height_step_px + line_actual_heights_px[-1]
    elif lines:
        total_text_block_height_px = len(lines) * line_height_step_px
    else: 
        total_text_block_height_px = points_to_pixels(font_size_pt, PDF_DPI)

    img_width_px = max_width_px + 2 * padding_px
    img_height_px = total_text_block_height_px + 2 * padding_px

    if not lines or max_width_px == 0:
        img_width_px = max(img_width_px, points_to_pixels(200, PDF_DPI))
        img_height_px = max(img_height_px, points_to_pixels(100, PDF_DPI))

    image = Image.new("RGB", (img_width_px, img_height_px), bg_color_rgb)
    draw = ImageDraw.Draw(image)
    current_y_px = padding_px
    for i, line in enumerate(lines):
        draw.text((padding_px, current_y_px), line, font=pil_font, fill=text_color_rgb)
        if i < len(lines) - 1:
            current_y_px += line_height_step_px
    try:
        image.save(output_filename, "PDF", resolution=PDF_DPI, title="Flowchart")
        print(f"流程图已保存为 PDF: {output_filename}")
    except Exception as e:
        print(f"保存 PDF 文件失败: {e}")

# --- 新增 text_to_html 函数 ---
def text_to_html(text_content, output_filename="flowchart.html",
                 font_family="Arial, sans-serif", font_size_px=16,
                 text_color_hex="#000000", bg_color_hex="#FFFFFF",
                 padding_px=20, line_height_ratio=1.5):
    """
    将多行文本内容转换为HTML文件。

    参数:
        text_content (str): 要转换为HTML的文本内容，多行用换行符分隔。
        output_filename (str): 输出HTML文件的文件名。
        font_family (str): CSS字体族。
        font_size_px (int): 字体大小 (单位: 像素)。
        text_color_hex (str): 文本颜色 (十六进制)。
        bg_color_hex (str): 背景颜色 (十六进制)。
        padding_px (int): 内容区域的内边距 (单位: 像素)。
        line_height_ratio (float): 行高比例 (相对于字体大小)。
    """
    lines = text_content.strip().split('\n')
    
    html_lines = []
    for line in lines:
        # 转义HTML特殊字符，例如 < > &
        escaped_line = html.escape(line)
        # 如果行为空，则添加一个HTML换行符实体，以在视觉上保留空行
        html_lines.append(f'<div>{escaped_line if escaped_line.strip() else "&nbsp;"}</div>')

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{os.path.splitext(os.path.basename(output_filename))[0]}</title>
    <style>
        body {{
            font-family: {font_family};
            font-size: {font_size_px}px;
            color: {text_color_hex};
            background-color: {bg_color_hex};
            margin: 0; /* 移除浏览器默认边距 */
            padding: {padding_px}px; /* 在body上应用内边距 */
            white-space: pre-wrap; /* 保留空格和换行符，但允许自动换行 */
        }}
        div {{
            line-height: {line_height_ratio};
            min-height: 1em; /* 确保空div也占据一些高度 */
        }}
        /* 或者使用 pre 标签来更好地保留格式，但需要调整样式 */
        /*
        pre {{
            font-family: inherit; 
            font-size: inherit;
            color: inherit;
            background-color: inherit;
            margin: 0;
            padding: {padding_px}px;
            white-space: pre-wrap;
            word-wrap: break-word; 
            line-height: {line_height_ratio};
        }}
        */
    </style>
</head>
<body>
    {''.join(html_lines)}
</body>
</html>
"""
    # 如果使用<pre>标签，可以这样构建:
    # escaped_full_text = html.escape(text_content.strip())
    # html_content = f"""... <pre>{escaped_full_text}</pre> ..."""


    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"流程图已保存为 HTML: {output_filename}")
    except Exception as e:
        print(f"保存 HTML 文件失败: {e}")


# --- 主程序 ---
if __name__ == "__main__":
    input_file = "input.txt"
    flowchart_text = ""

    # 为演示方便，如果input.txt不存在，创建一个包含示例内容的文件
    if not os.path.exists(input_file):
        print(f"提示: 输入文件 '{input_file}' 未找到。将创建一个包含示例内容的 '{input_file}'。")
        try:
            with open(input_file, "w", encoding="utf-8") as f:
                f.write("这是第一行流程文本。\n这是第二行，包含一些->特殊符号<END>\n\n这是在空行之后的另一行。\n\t前面有缩进的一行。")
            print(f"示例文件 '{input_file}' 已创建。")
        except Exception as e:
            print(f"创建示例文件 '{input_file}' 失败: {e}")


    if os.path.exists(input_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                flowchart_text = f.read()
            if not flowchart_text.strip():
                print(f"警告: '{input_file}' 为空。")
                flowchart_text = " " # 避免后续处理空字符串出错
        except Exception as e:
            print(f"读取文件 '{input_file}' 失败: {e}")
            flowchart_text = f"错误: 无法读取 {input_file}"
    else:
        # 这段逻辑在上面已处理，理论上不会执行，除非创建示例文件失败
        print(f"错误: 输入文件 '{input_file}' 未找到。请创建该文件并填入流程图文本。")
        flowchart_text = f"错误: 文件 {input_file} 未找到。"
    
    # 字体查找逻辑
    font_candidates = ["SourceHanSerifSC-Bold.otf", "SimSun.ttf", "msyh.ttc", "ukai.ttc"] # 添加一些常见中文字体
    font_file_path = None
    
    # 尝试在脚本同目录下查找
    for font_name in font_candidates:
        if os.path.exists(font_name):
            font_file_path = font_name
            print(f"找到字体: {font_name}")
            break
    
    if not font_file_path: # 如果未找到，尝试系统路径
        font_dirs = []
        if os.name == 'nt': # Windows
            font_dirs.append(os.path.join(os.environ.get('SYSTEMROOT', 'C:/Windows'), 'Fonts'))
        elif os.name == 'posix': # Linux, macOS
            font_dirs.extend(['/usr/share/fonts/truetype/', '/usr/local/share/fonts/', '~/.fonts/',
                              '/Library/Fonts/', '/System/Library/Fonts/'])
        
        for f_dir in font_dirs:
            f_dir_expanded = os.path.expanduser(f_dir) #展开 ~
            if os.path.isdir(f_dir_expanded):
                for font_name in font_candidates:
                    path_try = os.path.join(f_dir_expanded, font_name)
                    if os.path.exists(path_try):
                        font_file_path = path_try
                        print(f"找到系统字体: {font_file_path}")
                        break
            if font_file_path:
                break
                
    if not font_file_path:
        print("警告: 未找到指定候选字体，PNG/PDF输出将尝试系统默认字体，可能影响非英文字符显示。")
        print("警告: HTML输出将依赖浏览器默认字体或指定的通用字体族。")


    # --- PNG 输出设置 ---
    png_scale_factor = 3.0 
    png_base_font_size = 14 
    png_base_padding = 25   

    print("\n--- 生成 PNG 图片 ---")
    text_to_png(flowchart_text, 
                output_filename="text_flowchart.png", 
                font_path=font_file_path, 
                font_size=png_base_font_size, 
                padding=png_base_padding,   
                scale_factor=png_scale_factor)

    # --- PDF 输出设置 ---
    pdf_font_size_pt = 11 
    pdf_padding_pt = 36   

    print("\n--- 生成 PDF 文件 ---")
    text_to_pdf(flowchart_text,
                output_filename="text_flowchart.pdf",
                font_path=font_file_path,
                font_size_pt=pdf_font_size_pt,
                padding_pt=pdf_padding_pt)

    # --- HTML 输出设置 ---
    html_font_family = "Consolas, 'Courier New', monospace, '黑体', 'SimHei'" # 优先等宽，然后是中文黑体
    html_font_size_px = 14
    html_padding_px = 20
    html_line_height_ratio = 1.6

    print("\n--- 生成 HTML 文件 ---")
    text_to_html(flowchart_text,
                 output_filename="text_flowchart.html",
                 font_family=html_font_family,
                 font_size_px=html_font_size_px,
                 text_color_hex="#333333", # 深灰色文本
                 bg_color_hex="#F8F8F8",   # 浅灰色背景
                 padding_px=html_padding_px,
                 line_height_ratio=html_line_height_ratio)

    print("\n所有任务完成。")
