#!/usr/bin/env python3
"""
Markdown文件批量清洗工具
功能：批量清洗和标准化Markdown文件
"""

import os
import re
import argparse
import glob
from pathlib import Path
import logging
from typing import List, Set

class MarkdownCleaner:
    def __init__(self, config=None):
        self.config = config or {}
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('md_cleaner.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def read_file(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except Exception as e:
                self.logger.error(f"无法读取文件 {file_path}: {e}")
                return ""
    
    def write_file(self, file_path: str, content: str):
        """写入文件内容"""
        try:
            # 创建备份
            if self.config.get('backup', True):
                backup_path = file_path + '.bak'
                if not os.path.exists(backup_path):
                    import shutil
                    shutil.copy2(file_path, backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"成功清洗文件: {file_path}")
        except Exception as e:
            self.logger.error(f"写入文件失败 {file_path}: {e}")
    
    def remove_image_links(self, content: str) -> str:
        """删除图片链接"""
        if not self.config.get('remove_image_links', True):
            return content
        
        # 删除标准的Markdown图片语法 ![](path/to/image.jpg)
        pattern1 = r'!\[.*?\]\(.*?\.(jpg|jpeg|png|gif|bmp|webp).*?\)'
        content = re.sub(pattern1, '', content)
        
        # 删除HTML图片标签 <img src="path/to/image.jpg">
        pattern2 = r'<img.*?src=.*?\.(jpg|jpeg|png|gif|bmp|webp).*?>'
        content = re.sub(pattern2, '', content)
        
        # 删除可能的其他图片格式
        pattern3 = r'!\[.*?\]\(.*?\.(svg|ico|tiff).*?\)'
        content = re.sub(pattern3, '', content)
        
        self.logger.info("已删除图片链接")
        return content
    
    def remove_empty_lines(self, content: str) -> str:
        """移除多余空行"""
        if not self.config.get('remove_empty_lines', True):
            return content
        
        # 保留最多2个连续空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # 二次处理
        return content.strip() + '\n'
    
    def normalize_headings(self, content: str) -> str:
        """标准化标题格式"""
        if not self.config.get('normalize_headings', True):
            return content
        
        lines = content.split('\n')
        result = []
        
        for line in lines:
            # 统一 ATX 风格的标题（# 标题）
            if line.strip().startswith('#'):
                # 移除标题前后的 # 号
                line = re.sub(r'^#+\s*', '', line)
                line = re.sub(r'\s*#+\s*$', '', line)
                # 重新添加适当数量的 #
                heading_level = min(line.count('#') + 1, 6) if '#' in line else 1
                line = '#' * heading_level + ' ' + line.replace('#', '').strip()
            
            result.append(line)
        
        return '\n'.join(result)
    
    def format_tables(self, content: str) -> str:
        """格式化表格"""
        if not self.config.get('format_tables', True):
            return content
        
        lines = content.split('\n')
        result = []
        table_lines = []
        in_table = False
        
        for i, line in enumerate(lines):
            if '|' in line and not line.strip().startswith('|'):
                line = '|' + line + '|'
            
            if '|' in line:
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(line)
            else:
                if in_table and len(table_lines) >= 2:
                    # 处理表格
                    formatted_table = self._format_table_lines(table_lines)
                    result.extend(formatted_table)
                    table_lines = []
                    in_table = False
                result.append(line)
        
        # 处理文件末尾的表格
        if in_table and len(table_lines) >= 2:
            formatted_table = self._format_table_lines(table_lines)
            result.extend(formatted_table)
        
        return '\n'.join(result)
    
    def _format_table_lines(self, table_lines: List[str]) -> List[str]:
        """格式化表格行"""
        if len(table_lines) < 2:
            return table_lines
        
        # 计算每列的最大宽度
        col_widths = []
        for line in table_lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            for i, cell in enumerate(cells):
                if i >= len(col_widths):
                    col_widths.append(0)
                col_widths[i] = max(col_widths[i], len(cell))
        
        # 重新格式化表格
        formatted_lines = []
        for j, line in enumerate(table_lines):
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            formatted_cells = []
            
            for i, cell in enumerate(cells):
                if j == 1:  # 分隔线
                    formatted_cells.append('-' * (col_widths[i] + 2))
                else:
                    formatted_cells.append(f' {cell:<{col_widths[i]}} ')
            
            formatted_lines.append('|' + '|'.join(formatted_cells) + '|')
        
        return formatted_lines
    
    def remove_special_chars(self, content: str) -> str:
        """移除特殊字符"""
        if not self.config.get('remove_special_chars', False):
            return content
        
        # 移除不可见字符，保留换行符和制表符
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        return content
    
    def standardize_code_blocks(self, content: str) -> str:
        """标准化代码块"""
        if not self.config.get('standardize_code_blocks', True):
            return content
        
        # 统一代码块标记
        content = re.sub(r'```\s*(\w+)', r'```\1', content)
        content = re.sub(r'```\s*\n', '```\n', content)
        return content
    
    def fix_urls(self, content: str) -> str:
        """修复URL格式"""
        if not self.config.get('fix_urls', True):
            return content
        
        # 修复链接和图片格式
        content = re.sub(r'\!\[(.*?)\]\(\s*(.*?)\s*\)', r'![\1](\2)', content)
        content = re.sub(r'\[(.*?)\]\(\s*(.*?)\s*\)', r'[\1](\2)', content)
        return content
    
    def remove_trailing_whitespace(self, content: str) -> str:
        """移除行尾空白字符"""
        if not self.config.get('remove_trailing_whitespace', True):
            return content
        
        lines = content.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        return '\n'.join(cleaned_lines)
    
    def add_final_newline(self, content: str) -> str:
        """确保文件以换行符结束"""
        if not self.config.get('add_final_newline', True):
            return content
        
        return content.rstrip() + '\n'
    
    def clean_file(self, file_path: str):
        """清洗单个文件"""
        self.logger.info(f"开始处理文件: {file_path}")
        
        content = self.read_file(file_path)
        if not content:
            return
        
        original_content = content
        
        # 应用各种清洗函数
        cleaning_functions = [
            self.remove_image_links,  # 新增：删除图片链接
            self.remove_special_chars,
            self.normalize_headings,
            self.format_tables,
            self.standardize_code_blocks,
            self.fix_urls,
            self.remove_trailing_whitespace,
            self.remove_empty_lines,
            self.add_final_newline,
        ]
        
        for func in cleaning_functions:
            content = func(content)
        
        # 检查内容是否发生变化
        if content != original_content:
            self.write_file(file_path, content)
        else:
            self.logger.info(f"文件无需修改: {file_path}")
    
    def batch_clean(self, input_path: str):
        """批量清洗文件"""
        md_files = []
        
        if os.path.isfile(input_path):
            if input_path.lower().endswith('.md'):
                md_files = [input_path]
            else:
                self.logger.error("输入文件不是Markdown文件")
                return
        elif os.path.isdir(input_path):
            # 递归查找所有md文件
            pattern = os.path.join(input_path, '**', '*.md')
            md_files = glob.glob(pattern, recursive=True)
            
            # 同时查找 .markdown 文件
            pattern2 = os.path.join(input_path, '**', '*.markdown')
            md_files.extend(glob.glob(pattern2, recursive=True))
        else:
            self.logger.error("输入路径不存在")
            return
        
        self.logger.info(f"找到 {len(md_files)} 个Markdown文件")
        
        for md_file in md_files:
            self.clean_file(md_file)
        
        self.logger.info("批量清洗完成！")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Markdown文件批量清洗工具')
    parser.add_argument('input', help='输入文件或目录路径')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份文件')
    parser.add_argument('--no-format-tables', action='store_true', help='不格式化表格')
    parser.add_argument('--no-remove-images', action='store_true', help='不删除图片链接')
    parser.add_argument('--remove-special-chars', action='store_true', help='移除特殊字符')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 配置参数
    config = {
        'backup': not args.no_backup,
        'format_tables': not args.no_format_tables,
        'remove_image_links': not args.no_remove_images,  # 新增配置
        'remove_special_chars': args.remove_special_chars,
        'remove_empty_lines': True,
        'normalize_headings': True,
        'standardize_code_blocks': True,
        'fix_urls': True,
        'remove_trailing_whitespace': True,
        'add_final_newline': True,
    }
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    cleaner = MarkdownCleaner(config)
    cleaner.batch_clean(args.input)

if __name__ == "__main__":
    main()