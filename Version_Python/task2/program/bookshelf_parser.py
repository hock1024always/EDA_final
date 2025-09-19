#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BookShelf格式解析工具
用于解析和汇总BookShelf格式的电路布局文件
"""

import os
import re
import sys
import time
from collections import defaultdict


class BookshelfParser:
    """BookShelf格式解析器类"""
    
    def __init__(self, base_path, design_name):
        """
        初始化解析器
        
        参数:
            base_path: 文件所在的基础路径
            design_name: 设计名称，用于构建文件名
        """
        self.base_path = base_path
        self.design_name = design_name
        
        # 文件路径
        self.nodes_file = os.path.join(base_path, f"{design_name}.nodes")
        self.nets_file = os.path.join(base_path, f"{design_name}.nets")
        self.pl_file = os.path.join(base_path, f"{design_name}.pl")
        self.scl_file = os.path.join(base_path, f"{design_name}.scl")
        self.wts_file = os.path.join(base_path, f"{design_name}.wts")
        self.aux_file = os.path.join(base_path, f"{design_name}.aux")
        
        # 解析结果存储
        self.nodes_info = {}  # 节点信息
        self.nets_info = {}   # 网络信息
        self.pl_info = {}     # 布局信息
        self.scl_info = {}    # 布局区域信息
        
        # 统计信息
        self.stats = {
            "total_nodes": 0,
            "terminal_nodes": 0,
            "non_terminal_nodes": 0,
            "total_nets": 0,
            "total_pins": 0,
            "total_rows": 0,
            "chip_width": 0,
            "chip_height": 0,
            "chip_area": 0,
            "avg_net_degree": 0,
            "max_net_degree": 0,
            "min_net_degree": float('inf'),
        }
    
    def parse_nodes_file(self):
        """解析.nodes文件，获取节点信息"""
        print(f"正在解析节点文件: {self.nodes_file}")
        
        try:
            with open(self.nodes_file, 'r') as f:
                lines = f.readlines()
                
            # 跳过注释行
            data_lines = [line.strip() for line in lines if not line.strip().startswith('#') and line.strip()]
            
            # 解析节点数量和终端节点数量
            for line in data_lines:
                if "NumNodes" in line:
                    self.stats["total_nodes"] = int(re.search(r'NumNodes\s*:\s*(\d+)', line).group(1))
                elif "NumTerminals" in line:
                    self.stats["terminal_nodes"] = int(re.search(r'NumTerminals\s*:\s*(\d+)', line).group(1))
            
            self.stats["non_terminal_nodes"] = self.stats["total_nodes"] - self.stats["terminal_nodes"]
            
            # 解析节点详细信息
            node_pattern = re.compile(r'^\s*(\S+)\s+(\d+)\s+(\d+)')
            for line in data_lines:
                match = node_pattern.match(line)
                if match:
                    node_name, width, height = match.groups()
                    self.nodes_info[node_name] = {
                        "width": int(width),
                        "height": int(height),
                        "is_terminal": False  # 默认为非终端节点
                    }
            
            # 标记终端节点（前terminal_nodes个节点为终端节点）
            terminal_count = 0
            for node_name in self.nodes_info:
                if terminal_count < self.stats["terminal_nodes"]:
                    self.nodes_info[node_name]["is_terminal"] = True
                    terminal_count += 1
                else:
                    break
                    
            print(f"节点文件解析完成，共{self.stats['total_nodes']}个节点，其中{self.stats['terminal_nodes']}个终端节点")
            
        except Exception as e:
            print(f"解析节点文件时出错: {str(e)}")
            raise
    
    def parse_nets_file(self):
        """解析.nets文件，获取网络信息"""
        print(f"正在解析网络文件: {self.nets_file}")
        
        try:
            with open(self.nets_file, 'r') as f:
                content = f.read()
            
            # 解析网络数量和引脚数量
            num_nets_match = re.search(r'NumNets\s*:\s*(\d+)', content)
            num_pins_match = re.search(r'NumPins\s*:\s*(\d+)', content)
            
            if num_nets_match and num_pins_match:
                self.stats["total_nets"] = int(num_nets_match.group(1))
                self.stats["total_pins"] = int(num_pins_match.group(1))
            
            # 解析每个网络的信息
            net_sections = re.split(r'NetDegree\s*:\s*\d+\s+\S+', content)[1:]  # 分割每个网络部分
            net_headers = re.findall(r'NetDegree\s*:\s*(\d+)\s+(\S+)', content)  # 提取网络头部信息
            
            if len(net_sections) != len(net_headers):
                print(f"警告: 网络部分数量({len(net_sections)})与网络头部数量({len(net_headers)})不匹配")
            
            net_degrees = []
            for i, (degree, net_name) in enumerate(net_headers):
                if i < len(net_sections):
                    degree = int(degree)
                    net_degrees.append(degree)
                    
                    # 更新最大和最小网络度数
                    self.stats["max_net_degree"] = max(self.stats["max_net_degree"], degree)
                    self.stats["min_net_degree"] = min(self.stats["min_net_degree"], degree)
                    
                    # 解析网络连接的节点
                    section = net_sections[i]
                    pins = re.findall(r'\s*(\S+)\s+([IO])\s*:', section)
                    
                    self.nets_info[net_name] = {
                        "degree": degree,
                        "pins": pins  # 格式: [(node_name, direction), ...]
                    }
            
            # 计算平均网络度数
            if net_degrees:
                self.stats["avg_net_degree"] = sum(net_degrees) / len(net_degrees)
            
            print(f"网络文件解析完成，共{self.stats['total_nets']}个网络，{self.stats['total_pins']}个引脚")
            
        except Exception as e:
            print(f"解析网络文件时出错: {str(e)}")
            raise
    
    def parse_pl_file(self):
        """解析.pl文件，获取布局信息"""
        print(f"正在解析布局文件: {self.pl_file}")
        
        try:
            with open(self.pl_file, 'r') as f:
                lines = f.readlines()
            
            # 跳过注释行
            data_lines = [line.strip() for line in lines if not line.strip().startswith('#') and line.strip()]
            
            # 解析节点位置信息
            pl_pattern = re.compile(r'^\s*(\S+)\s+(\d+)\s+(\d+)\s*:\s*([NFS])')
            for line in data_lines:
                match = pl_pattern.match(line)
                if match:
                    node_name, x, y, orientation = match.groups()
                    self.pl_info[node_name] = {
                        "x": int(x),
                        "y": int(y),
                        "orientation": orientation  # N: 北, S: 南, F: 翻转
                    }
            
            print(f"布局文件解析完成，共{len(self.pl_info)}个节点的位置信息")
            
        except Exception as e:
            print(f"解析布局文件时出错: {str(e)}")
            raise
    
    def parse_scl_file(self):
        """解析.scl文件，获取布局区域信息"""
        print(f"正在解析布局区域文件: {self.scl_file}")
        
        try:
            with open(self.scl_file, 'r') as f:
                content = f.read()
            
            # 解析行数
            num_rows_match = re.search(r'NumRows\s*:\s*(\d+)', content)
            if num_rows_match:
                self.stats["total_rows"] = int(num_rows_match.group(1))
            
            # 解析每一行的信息
            row_sections = re.findall(r'CoreRow\s+Horizontal(.*?)End', content, re.DOTALL)
            
            max_x = 0
            max_y = 0
            
            for i, section in enumerate(row_sections):
                coordinate_match = re.search(r'Coordinate\s*:\s*(\d+)', section)
                height_match = re.search(r'Height\s*:\s*(\d+)', section)
                subrow_match = re.search(r'SubrowOrigin\s*:\s*(\d+)\s+NumSites\s*:\s*(\d+)', section)
                
                if coordinate_match and height_match and subrow_match:
                    y = int(coordinate_match.group(1))
                    height = int(height_match.group(1))
                    x = int(subrow_match.group(1))
                    num_sites = int(subrow_match.group(2))
                    
                    # 更新最大坐标
                    max_y = max(max_y, y + height)
                    max_x = max(max_x, x + num_sites)
                    
                    self.scl_info[i] = {
                        "y": y,
                        "height": height,
                        "x": x,
                        "num_sites": num_sites
                    }
            
            # 更新芯片尺寸信息
            self.stats["chip_width"] = max_x
            self.stats["chip_height"] = max_y
            self.stats["chip_area"] = max_x * max_y
            
            print(f"布局区域文件解析完成，共{self.stats['total_rows']}行，芯片尺寸: {max_x} x {max_y}")
            
        except Exception as e:
            print(f"解析布局区域文件时出错: {str(e)}")
            raise
    
    def parse_all(self):
        """解析所有文件"""
        start_time = time.time()
        print(f"开始解析设计: {self.design_name}")
        
        self.parse_nodes_file()
        self.parse_nets_file()
        self.parse_pl_file()
        self.parse_scl_file()
        
        end_time = time.time()
        print(f"解析完成，耗时: {end_time - start_time:.2f}秒")
    
    def generate_report(self, language="chinese"):
        """生成汇总报告
        
        参数:
            language: 输出语言，可选值为"chinese"或"english"
        """
        # 计算布局密度
        total_cell_area = sum(node["width"] * node["height"] for node in self.nodes_info.values() 
                             if not node["is_terminal"])
        density = total_cell_area / self.stats["chip_area"] if self.stats["chip_area"] > 0 else 0
        
        # 计算可移动区域面积
        movable_area = total_cell_area
        
        # 计算固定区域面积
        fixed_area = sum(node["width"] * node["height"] for node in self.nodes_info.values() 
                        if node["is_terminal"])
        
        # 计算核心区域面积
        core_area = self.stats["chip_area"]
        
        # 计算固定区域在核心区域中的面积
        fixed_area_in_core = fixed_area
        
        # 计算放置利用率
        placement_util = movable_area / (core_area - fixed_area_in_core) if (core_area - fixed_area_in_core) > 0 else 0
        
        # 计算核心密度
        core_density = (movable_area + fixed_area_in_core) / core_area if core_area > 0 else 0
        
        # 计算不同度数的网络数量
        net_degree_counts = {"2": 0, "3-10": 0, "11-100": 0, "100+": 0}
        for net in self.nets_info.values():
            degree = net["degree"]
            if degree == 2:
                net_degree_counts["2"] += 1
            elif 3 <= degree <= 10:
                net_degree_counts["3-10"] += 1
            elif 11 <= degree <= 100:
                net_degree_counts["11-100"] += 1
            else:
                net_degree_counts["100+"] += 1
        
        if language == "chinese":
            print("\n" + "="*50)
            print(f"设计名称: {self.design_name} 汇总报告")
            print("="*50)
            
            print("\n节点统计:")
            print(f"  总节点数: {self.stats['total_nodes']}")
            print(f"  终端节点数: {self.stats['terminal_nodes']}")
            print(f"  非终端节点数: {self.stats['non_terminal_nodes']}")
            
            print("\n网络统计:")
            print(f"  总网络数: {self.stats['total_nets']}")
            print(f"  总引脚数: {self.stats['total_pins']}")
            print(f"  平均网络度数: {self.stats['avg_net_degree']:.2f}")
            print(f"  最大网络度数: {self.stats['max_net_degree']}")
            print(f"  最小网络度数: {self.stats['min_net_degree']}")
            
            print("\n布局区域统计:")
            print(f"  总行数: {self.stats['total_rows']}")
            print(f"  芯片宽度: {self.stats['chip_width']}")
            print(f"  芯片高度: {self.stats['chip_height']}")
            print(f"  芯片面积: {self.stats['chip_area']}")
            
            print(f"\n布局密度: {density:.4f}")
            print("="*50)
            
            # 将报告保存到文件
            report_file = os.path.join(self.base_path, f"{self.design_name}_report.txt")
            with open(report_file, 'w') as f:
                f.write(f"设计名称: {self.design_name} 汇总报告\n")
                f.write("="*50 + "\n\n")
                
                f.write("节点统计:\n")
                f.write(f"  总节点数: {self.stats['total_nodes']}\n")
                f.write(f"  终端节点数: {self.stats['terminal_nodes']}\n")
                f.write(f"  非终端节点数: {self.stats['non_terminal_nodes']}\n\n")
                
                f.write("网络统计:\n")
                f.write(f"  总网络数: {self.stats['total_nets']}\n")
                f.write(f"  总引脚数: {self.stats['total_pins']}\n")
                f.write(f"  平均网络度数: {self.stats['avg_net_degree']:.2f}\n")
                f.write(f"  最大网络度数: {self.stats['max_net_degree']}\n")
                f.write(f"  最小网络度数: {self.stats['min_net_degree']}\n\n")
                
                f.write("布局区域统计:\n")
                f.write(f"  总行数: {self.stats['total_rows']}\n")
                f.write(f"  芯片宽度: {self.stats['chip_width']}\n")
                f.write(f"  芯片高度: {self.stats['chip_height']}\n")
                f.write(f"  芯片面积: {self.stats['chip_area']}\n\n")
                
                f.write(f"布局密度: {density:.4f}\n")
                f.write("="*50 + "\n")
            
            print(f"报告已保存到: {report_file}")
        
        elif language == "english":
            # 获取核心区域的左下角和右上角坐标
            lower_left_x = min(row["x"] for row in self.scl_info.values())
            lower_left_y = min(row["y"] for row in self.scl_info.values())
            upper_right_x = self.stats["chip_width"]
            upper_right_y = self.stats["chip_height"]
            
            # 格式化输出
            print("Use BOOKSHELF placement format")
            print(f"Reading AUX file: {self.base_path}/{os.path.basename(self.aux_file)}")
            
            # 从aux文件中读取文件列表
            try:
                with open(self.aux_file, 'r') as f:
                    aux_content = f.read()
                    files = re.findall(r':\s+([^\n]+)', aux_content)
                    if files:
                        print(" ".join(files[0].strip().split()))
            except Exception:
                # 如果无法读取aux文件，则使用默认文件列表
                print(f"{self.design_name}.nodes {self.design_name}.nets {self.design_name}.wts {self.design_name}.pl {self.design_name}.scl")
            
            print(f"Set core region from site info: lower left: ({lower_left_x},{lower_left_y}) to upper right: ({upper_right_x},{upper_right_y})")
            print(f"NumModules: {self.stats['total_nodes']}")
            print(f"NumNodes: {self.stats['non_terminal_nodes']} (= {self.stats['non_terminal_nodes']//1000}k)")
            print(f"Terminals: {self.stats['terminal_nodes']}")
            print(f"Nets: {self.stats['total_nets']}")
            print(f"Pins: {self.stats['total_pins']}")
            print(f"Max net degree= {self.stats['max_net_degree']}")
            print(f"Initialize module position with file: {self.design_name}.pl")
            print("<<<< DATABASE SUMMARIES >>>>")
            print(f"Core region: lower left: ({lower_left_x},{lower_left_y}) to upper right: ({upper_right_x},{upper_right_y})")
            
            # 获取行高和行数
            row_height = next(iter(self.scl_info.values()))["height"] if self.scl_info else 0
            print(f"Row Height/Number: {row_height} / {self.stats['total_rows']} (site step 1.000000)")
            
            # 输出面积信息
            print(f"Core Area: {core_area} ({core_area:.5e})")
            print(f"Cell Area: {total_cell_area} ({(total_cell_area/core_area*100):.2f}%)")
            print(f"Movable Area: {movable_area} ({(movable_area/core_area*100):.2f}%)")
            print(f"Fixed Area: {fixed_area} ({(fixed_area/core_area*100):.2f}%)")
            print(f"Fixed Area in Core: {fixed_area_in_core} ({(fixed_area_in_core/core_area*100):.2f}%)")
            print(f"Placement Util.: {placement_util*100:.2f}% (=move/freeSites)")
            print(f"Core Density: {core_density*100:.2f}% (=usedArea/core)")
            
            # 输出节点和网络信息
            print(f"Cell #: {self.stats['non_terminal_nodes']} (={self.stats['non_terminal_nodes']//1000}k)")
            print(f"Object #: {self.stats['total_nodes']} (={self.stats['total_nodes']//1000}k) (fixed: {self.stats['terminal_nodes']}) (macro: 0)")
            print(f"Net #: {self.stats['total_nets']} (={self.stats['total_nets']//1000}k)")
            print(f"Max net degree=: {self.stats['max_net_degree']}")
            
            # 输出引脚度数分布
            print(f"Pin 2 ({net_degree_counts['2']}) 3-10 ({net_degree_counts['3-10']}) 11-100 ({net_degree_counts['11-100']}) 100- ({net_degree_counts['100+']})")
            print(f"Pin #: {self.stats['total_pins']}")
            
            # 将英文报告保存到文件
            report_file = os.path.join(self.base_path, f"{self.design_name}_report_english.txt")
            with open(report_file, 'w') as f:
                f.write("Use BOOKSHELF placement format\n")
                f.write(f"Reading AUX file: {self.base_path}/{os.path.basename(self.aux_file)}\n")
                f.write(f"{self.design_name}.nodes {self.design_name}.nets {self.design_name}.wts {self.design_name}.pl {self.design_name}.scl\n")
                f.write(f"Set core region from site info: lower left: ({lower_left_x},{lower_left_y}) to upper right: ({upper_right_x},{upper_right_y})\n")
                f.write(f"NumModules: {self.stats['total_nodes']}\n")
                f.write(f"NumNodes: {self.stats['non_terminal_nodes']} (= {self.stats['non_terminal_nodes']//1000}k)\n")
                f.write(f"Terminals: {self.stats['terminal_nodes']}\n")
                f.write(f"Nets: {self.stats['total_nets']}\n")
                f.write(f"Pins: {self.stats['total_pins']}\n")
                f.write(f"Max net degree= {self.stats['max_net_degree']}\n")
                f.write(f"Initialize module position with file: {self.design_name}.pl\n")
                f.write("<<<< DATABASE SUMMARIES >>>>\n")
                f.write(f"Core region: lower left: ({lower_left_x},{lower_left_y}) to upper right: ({upper_right_x},{upper_right_y})\n")
                f.write(f"Row Height/Number: {row_height} / {self.stats['total_rows']} (site step 1.000000)\n")
                f.write(f"Core Area: {core_area} ({core_area:.5e})\n")
                f.write(f"Cell Area: {total_cell_area} ({(total_cell_area/core_area*100):.2f}%)\n")
                f.write(f"Movable Area: {movable_area} ({(movable_area/core_area*100):.2f}%)\n")
                f.write(f"Fixed Area: {fixed_area} ({(fixed_area/core_area*100):.2f}%)\n")
                f.write(f"Fixed Area in Core: {fixed_area_in_core} ({(fixed_area_in_core/core_area*100):.2f}%)\n")
                f.write(f"Placement Util.: {placement_util*100:.2f}% (=move/freeSites)\n")
                f.write(f"Core Density: {core_density*100:.2f}% (=usedArea/core)\n")
                f.write(f"Cell #: {self.stats['non_terminal_nodes']} (={self.stats['non_terminal_nodes']//1000}k)\n")
                f.write(f"Object #: {self.stats['total_nodes']} (={self.stats['total_nodes']//1000}k) (fixed: {self.stats['terminal_nodes']}) (macro: 0)\n")
                f.write(f"Net #: {self.stats['total_nets']} (={self.stats['total_nets']//1000}k)\n")
                f.write(f"Max net degree=: {self.stats['max_net_degree']}\n")
                f.write(f"Pin 2 ({net_degree_counts['2']}) 3-10 ({net_degree_counts['3-10']}) 11-100 ({net_degree_counts['11-100']}) 100- ({net_degree_counts['100+']})\n")
                f.write(f"Pin #: {self.stats['total_pins']}\n")
            
            print(f"\nEnglish report saved to: {report_file}")


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("用法: python bookshelf_parser.py <设计文件路径> <设计名称> [language]")
        print("例如: python bookshelf_parser.py ./adaptec1 adaptec1")
        print("language参数可选值: chinese(默认), english")
        return
    
    base_path = sys.argv[1]
    design_name = sys.argv[2]
    
    # 默认使用中文输出，如果指定了language参数则使用指定的语言
    language = "chinese"
    if len(sys.argv) > 3:
        language = sys.argv[3].lower()
        if language not in ["chinese", "english"]:
            print(f"不支持的语言: {language}，使用默认语言(chinese)")
            language = "chinese"
    
    parser = BookshelfParser(base_path, design_name)
    parser.parse_all()
    parser.generate_report(language)


if __name__ == "__main__":
    main()
