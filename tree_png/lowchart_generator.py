import configparser
import os
import html
from PIL import Image, ImageDraw, ImageFont
from abc import ABC, abstractmethod

# --- Utility Functions ---
def points_to_pixels(points, dpi):
    """将点单位转换为像素单位"""
    return int(points * dpi / 72.0)

def parse_color_tuple(color_str):
    """Parses a color string like '255, 255, 255' into a tuple of ints."""
    try:
        return tuple(map(int, color_str.split(',')))
    except ValueError:
        print(f"Warning: Could not parse color string '{color_str}'. Defaulting to black or white.")
        return (0, 0, 0) # Default to black, context might need different default

def ensure_output_dir(path):
    """Ensures the output directory exists."""
    if path and not os.path.exists(path):
        os.makedirs(path)
        print(f"Created output directory: {path}")

# --- Configuration Manager ---
class ConfigManager:
    def __init__(self, config_file="config.ini"):
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
        self.config.read(config_file)

    def get(self, section, option, fallback=None):
        return self.config.get(section, option, fallback=fallback)

    def getint(self, section, option, fallback=None):
        return self.config.getint(section, option, fallback=fallback)

    def getfloat(self, section, option, fallback=None):
        return self.config.getfloat(section, option, fallback=fallback)

    def getboolean(self, section, option, fallback=None):
        return self.config.getboolean(section, option, fallback=fallback)

    def get_list(self, section, option, delimiter=',', fallback=None):
        value = self.config.get(section, option, fallback=None)
        if value:
            return [item.strip() for item in value.split(delimiter)]
        return fallback if fallback is not None else []

# --- Abstract Outputter ---
class Outputter(ABC):
    def __init__(self, config_manager, section_name):
        self.config = config_manager
        self.section_name = section_name
        self.output_filename_base = self.config.get(section_name, 'output_filename', fallback=f"default_output_{section_name.lower()}")
        self.output_dir = self.config.get('General', 'output_directory', fallback='output')

    def get_output_path(self):
        return os.path.join(self.output_dir, self.output_filename_base)
        
    @abstractmethod
    def generate(self, text_content, font_path=None):
        pass

# --- Concrete Outputters ---

class PngOutputter(Outputter):
    def __init__(self, config_manager):
        super().__init__(config_manager, 'PNG')
        self.font_size = self.config.getint('PNG', 'font_size', fallback=15)
        self.padding = self.config.getint('PNG', 'padding', fallback=20)
        self.scale_factor = self.config.getfloat('PNG', 'scale_factor', fallback=2.0)
        self.bg_color = parse_color_tuple(self.config.get('PNG', 'bg_color', fallback='255,255,255'))
        self.text_color = parse_color_tuple(self.config.get('PNG', 'text_color', fallback='0,0,0'))

    def generate(self, text_content, font_path=None):
        output_filepath = self.get_output_path()
        ensure_output_dir(os.path.dirname(output_filepath))

        lines = text_content.strip().split('\n')
        scaled_font_size = int(self.font_size * self.scale_factor)
        scaled_padding = int(self.padding * self.scale_factor)
        
        pil_font = None
        try:
            if font_path and os.path.exists(font_path):
                pil_font = ImageFont.truetype(font_path, scaled_font_size)
            else:
                try: pil_font = ImageFont.truetype("arial.ttf", scaled_font_size) # Fallback
                except IOError: pil_font = ImageFont.load_default()
        except Exception as e:
            print(f"PNG: Font loading error: {e}. Using default font.")
            pil_font = ImageFont.load_default()

        line_actual_heights = []
        max_width = 0
        temp_image = Image.new("RGB", (1,1)); draw_temp = ImageDraw.Draw(temp_image)
        for line in lines:
            try: # Pillow >= 10
                bbox = draw_temp.textbbox((0,0), line, font=pil_font)
                text_width = bbox[2] - bbox[0]; text_height = bbox[3] - bbox[1]
            except AttributeError: # Pillow < 10 or other issue
                try: text_width, text_height = pil_font.getsize(line)
                except AttributeError: # Even older Pillow or specific font issue
                    bbox = pil_font.getbbox(line)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]

            line_actual_heights.append(text_height)
            if text_width > max_width: max_width = text_width
        
        line_spacing_ratio = 1.5
        scaled_line_height_for_stepping = int(scaled_font_size * line_spacing_ratio)
        total_text_block_height = 0
        if lines and line_actual_heights:
            # Height for the text block itself
            first_line_height = line_actual_heights[0] if line_actual_heights else scaled_font_size
            remaining_lines_height = (len(lines) - 1) * scaled_line_height_for_stepping if len(lines) > 1 else 0
            total_text_block_height = first_line_height + remaining_lines_height
            # A simpler alternative sum of actual heights + spacing:
            # total_text_block_height = sum(line_actual_heights) + max(0, len(lines) - 1) * (scaled_line_height_for_stepping - scaled_font_size) # From original
        elif lines: # Fallback if actual heights couldn't be determined
            total_text_block_height = len(lines) * scaled_line_height_for_stepping
        else: # No lines
            total_text_block_height = scaled_padding 

        img_width = int(max_width + scaled_padding * 2)
        img_height = int(total_text_block_height + scaled_padding * 2)

        # Ensure minimum dimensions
        min_width_scaled = int(300 * self.scale_factor) if lines else int(100 * self.scale_factor)
        min_height_scaled = int(100 * self.scale_factor) if lines else int(50 * self.scale_factor)
        img_width = max(img_width, min_width_scaled if max_width > 0 else scaled_padding * 2 + 10)
        img_height = max(img_height, min_height_scaled if total_text_block_height > 0 else scaled_padding * 2 + 10)


        image = Image.new("RGB", (img_width, img_height), self.bg_color)
        draw = ImageDraw.Draw(image)
        y_text = scaled_padding
        
        for i, line in enumerate(lines):
            # Centralize text if desired, for now, simple top-left alignment with padding
            line_y_pos = y_text
            if i > 0:
                y_text += scaled_line_height_for_stepping
            else: # First line uses its actual height for the next step if different
                 y_text += line_actual_heights[0] if line_actual_heights else scaled_line_height_for_stepping

            draw.text((scaled_padding, line_y_pos), line, font=pil_font, fill=self.text_color)
            
        try:
            image.save(output_filepath)
            print(f"图表已保存为 PNG: {output_filepath} (尺寸: {img_width}x{img_height})")
        except Exception as e:
            print(f"保存 PNG 图片失败: {e}")


class PdfOutputter(Outputter):
    def __init__(self, config_manager):
        super().__init__(config_manager, 'PDF')
        self.font_size_pt = self.config.getint('PDF', 'font_size_pt', fallback=12)
        self.padding_pt = self.config.getint('PDF', 'padding_pt', fallback=36)
        self.bg_color_rgb = parse_color_tuple(self.config.get('PDF', 'bg_color_rgb', fallback='255,255,255'))
        self.text_color_rgb = parse_color_tuple(self.config.get('PDF', 'text_color_rgb', fallback='0,0,0'))
        self.dpi = self.config.getfloat('PDF', 'dpi', fallback=300.0)

    def generate(self, text_content, font_path=None):
        output_filepath = self.get_output_path()
        ensure_output_dir(os.path.dirname(output_filepath))

        lines = text_content.strip().split('\n')
        font_size_px = points_to_pixels(self.font_size_pt, self.dpi)
        padding_px = points_to_pixels(self.padding_pt, self.dpi)
        
        pil_font = None
        try:
            if font_path and os.path.exists(font_path):
                pil_font = ImageFont.truetype(font_path, font_size_px)
                # print(f"PDF: Using font {font_path} (Size: {font_size_px}px for drawing, maps to {self.font_size_pt}pt)")
            else:
                try: pil_font = ImageFont.truetype("arial.ttf", font_size_px)
                except IOError: pil_font = ImageFont.load_default(); print("PDF: Warning: Arial not found, using Pillow default.")
        except Exception as e:
            print(f"PDF: Font loading error: {e}. Using Pillow default font.")
            pil_font = ImageFont.load_default()

        line_actual_heights_px = []
        max_width_px = 0
        temp_image = Image.new("RGB", (1,1)); draw_temp = ImageDraw.Draw(temp_image)

        for line in lines:
            try: # Pillow >= 10
                bbox = draw_temp.textbbox((0,0), line, font=pil_font)
                text_width_px = bbox[2] - bbox[0]; text_height_px = bbox[3] - bbox[1]
            except AttributeError: # Pillow < 10 or other issue
                try: text_width_px, text_height_px = pil_font.getsize(line)
                except AttributeError:
                    bbox = pil_font.getbbox(line)
                    text_width_px = bbox[2] - bbox[0]
                    text_height_px = bbox[3] - bbox[1]
            line_actual_heights_px.append(text_height_px)
            if text_width_px > max_width_px: max_width_px = text_width_px
        
        line_height_step_px = points_to_pixels(self.font_size_pt * 1.5, self.dpi) # 1.5 line spacing
        total_text_block_height_px = 0
        if lines and line_actual_heights_px:
            first_line_height = line_actual_heights_px[0] if line_actual_heights_px else font_size_px
            remaining_lines_height = (len(lines) - 1) * line_height_step_px if len(lines) > 1 else 0
            total_text_block_height_px = first_line_height + remaining_lines_height
        elif lines:
             total_text_block_height_px = len(lines) * line_height_step_px
        else: 
             total_text_block_height_px = points_to_pixels(self.font_size_pt, self.dpi) # Min height for empty

        img_width_px = max_width_px + 2 * padding_px
        img_height_px = total_text_block_height_px + 2 * padding_px

        if not lines or max_width_px == 0: # Ensure minimum size for empty or very small content
            img_width_px = max(img_width_px, points_to_pixels(200, self.dpi))
            img_height_px = max(img_height_px, points_to_pixels(100, self.dpi))

        image = Image.new("RGB", (int(img_width_px), int(img_height_px)), self.bg_color_rgb)
        draw = ImageDraw.Draw(image)
        current_y_px = padding_px
        
        for i, line in enumerate(lines):
            line_y_pos = current_y_px
            if i > 0 :
                current_y_px += line_height_step_px
            else: # First line
                current_y_px += line_actual_heights_px[0] if line_actual_heights_px else line_height_step_px
            draw.text((padding_px, line_y_pos), line, font=pil_font, fill=self.text_color_rgb)
            
        try:
            image.save(output_filepath, "PDF", resolution=self.dpi, title=os.path.splitext(self.output_filename_base)[0])
            print(f"图表已保存为 PDF: {output_filepath}")
        except Exception as e:
            print(f"保存 PDF 文件失败: {e}")


class HtmlOutputter(Outputter):
    def __init__(self, config_manager):
        super().__init__(config_manager, 'HTML')
        self.font_family = self.config.get('HTML', 'font_family', fallback="Arial, sans-serif")
        self.font_size_px = self.config.getint('HTML', 'font_size_px', fallback=16)
        self.text_color_hex = self.config.get('HTML', 'text_color_hex', fallback="#000000")
        self.bg_color_hex = self.config.get('HTML', 'bg_color_hex', fallback="#FFFFFF")
        self.padding_px = self.config.getint('HTML', 'padding_px', fallback=20)
        self.line_height_ratio = self.config.getfloat('HTML', 'line_height_ratio', fallback=1.5)

    def generate(self, text_content, font_path=None): # font_path is not used for HTML
        output_filepath = self.get_output_path()
        ensure_output_dir(os.path.dirname(output_filepath))

        lines = text_content.strip().split('\n')
        html_lines = []
        for line in lines:
            escaped_line = html.escape(line)
            html_lines.append(f'<div>{escaped_line if escaped_line.strip() else "&nbsp;"}</div>')

        html_body_content = ''.join(html_lines)
        if not html_body_content.strip() and not lines: # Handle truly empty input
             html_body_content = '<div>&nbsp;</div>' # Ensure body is not completely empty for valid HTML structure

        html_full_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{os.path.splitext(self.output_filename_base)[0]}</title>
    <style>
        body {{
            font-family: {self.font_family};
            font-size: {self.font_size_px}px;
            color: {self.text_color_hex};
            background-color: {self.bg_color_hex};
            margin: 0; 
            padding: {self.padding_px}px; 
            white-space: pre-wrap; 
        }}
        div {{
            line-height: {self.line_height_ratio};
            min-height: 1em; 
        }}
    </style>
</head>
<body>
    {html_body_content}
</body>
</html>
"""
        try:
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(html_full_content)
            print(f"图表已保存为 HTML: {output_filepath}")
        except Exception as e:
            print(f"保存 HTML 文件失败: {e}")



# --- Font Searching ---
def find_font(config_manager):
    font_candidates = config_manager.get_list('General', 'font_candidates')
    font_file_path = None

    # 1. Check script directory
    for font_name in font_candidates:
        if os.path.exists(font_name):
            print(f"找到字体 (脚本目录): {font_name}")
            return font_name
    
    # 2. Check system font directories
    system_font_dirs_str = ""
    if os.name == 'nt': # Windows
        system_font_dirs_str = config_manager.get('General', 'system_font_dirs_windows', fallback='')
    elif os.name == 'posix': # Linux, macOS
        system_font_dirs_str = config_manager.get('General', 'system_font_dirs_posix', fallback='')
    
    system_font_dirs = [d.strip() for d in system_font_dirs_str.split(',') if d.strip()]

    for f_dir_raw in system_font_dirs:
        f_dir = os.path.expanduser(f_dir_raw) # Expand ~
        if os.path.isdir(f_dir):
            for font_name in font_candidates:
                path_try = os.path.join(f_dir, font_name)
                if os.path.exists(path_try):
                    print(f"找到系统字体: {path_try}")
                    return path_try
    
    print("警告: 未能找到指定的候选字体。PNG/PDF 可能依赖系统默认或Pillow的回退字体。")
    return None

# --- Main Application Logic ---
def main():
    try:
        config_mgr = ConfigManager("config.ini")
    except FileNotFoundError as e:
        print(e)
        print("缺少配置文件ini")

    # Ensure output directory from config exists
    output_dir_general = config_mgr.get('General', 'output_directory', fallback='output_flowcharts')
    ensure_output_dir(output_dir_general)

    input_file_path = config_mgr.get('General', 'input_file', fallback="input.txt")
    flowchart_text = ""

    if not os.path.exists(input_file_path):
        print(f"提示: 输入文件 '{input_file_path}' 未找到。将创建一个包含示例内容的 '{input_file_path}'。")
        try:
            with open(input_file_path, "w", encoding="utf-8") as f:
                f.write("这是第一行流程文本。\n这是第二行 -> 特殊符号 <END>\n\n这是空行后的一行。\n\t有缩进的一行。")
            print(f"示例文件 '{input_file_path}' 已创建。")
        except Exception as e:
            print(f"创建示例文件 '{input_file_path}' 失败: {e}")
    
    try:
        with open(input_file_path, "r", encoding="utf-8") as f:
            flowchart_text = f.read()
        if not flowchart_text.strip() and flowchart_text != "": # Distinguish empty file from file with only whitespace
            print(f"警告: '{input_file_path}' 为空或仅包含空格。")
            # Keep flowchart_text as is, let outputters handle it.
        elif not flowchart_text: # File doesn't exist or truly empty after read
             flowchart_text = " " # Default to a single space to avoid errors in some drawing logic
             print(f"警告: '{input_file_path}' 为空。使用默认内容。")
    except Exception as e:
        print(f"读取文件 '{input_file_path}' 失败: {e}")
        flowchart_text = f"错误: 无法读取 {input_file_path}"

    active_font_path = find_font(config_mgr)

    outputter_map = {
        'PNG': PngOutputter,
        'PDF': PdfOutputter,
        'HTML': HtmlOutputter,
    }

    for section_name, OutputterClass in outputter_map.items():
        if config_mgr.getboolean(section_name, 'enabled', fallback=False):
            print(f"\n--- 正在生成 {section_name} ---")
            try:
                outputter_instance = OutputterClass(config_mgr)
                outputter_instance.generate(flowchart_text, font_path=active_font_path)
            except configparser.NoOptionError as e:
                print(f"配置错误: {section_name} 部分缺少选项 '{e.option}'. 跳过此格式。")
            except Exception as e:
                print(f"生成 {section_name} 时发生意外错误: {e}")
        else:
            print(f"\n--- {section_name} 输出已禁用 ---")
            
    print("\n所有已启用的任务完成。")

if __name__ == "__main__":
    main()
