#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BookShelf格式解析工具示例脚本
演示如何使用BookshelfParser类解析adaptec1测试数据
"""

import os
import sys
from bookshelf_parser import BookshelfParser

def main():
    """示例主函数"""
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置测试数据路径和设计名称
    design_path = os.path.join(current_dir, "adaptec1")
    design_name = "adaptec1"
    
    print(f"开始解析测试数据: {design_name}")
    print(f"数据路径: {design_path}")
    
    # 创建解析器实例
    parser = BookshelfParser(design_path, design_name)
    
    # 解析所有文件
    parser.parse_all()
    
    # 生成报告
    parser.generate_report()
    
    print("\n示例运行完成!")

if __name__ == "__main__":
    main()
