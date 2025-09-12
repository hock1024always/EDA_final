#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始布局设计程序

该程序用于实现集成电路布局设计中的初始布局算法，基于二次规划方法。
程序读取BookShelf格式的布局数据文件，计算初始布局位置，并输出结果。
"""

# 确保正确处理中文字符
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import sys
import time
import math
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
import matplotlib.pyplot as plt

class BookshelfParser:
    """
    BookShelf格式文件解析器类
    
    该类用于解析BookShelf格式的布局数据文件，并计算相关统计信息。
    包括核心区域、行高、单元数量、网表统计等。
    """
    def __init__(self, directory):
        """
        初始化解析器，设置目录路径和初始化数据结构
        
        参数:
            directory (str): BookShelf格式文件所在的目录路径
        """
        self.directory = directory
        self.basename = os.path.basename(directory)
        
        # 文件路径初始化，假设所有文件都使用目录名作为基础名
        self.aux_file = os.path.join(directory, f"{self.basename}.aux")
        self.nodes_file = os.path.join(directory, f"{self.basename}.nodes")
        self.nets_file = os.path.join(directory, f"{self.basename}.nets")
        self.pl_file = os.path.join(directory, f"{self.basename}.pl")
        self.scl_file = os.path.join(directory, f"{self.basename}.scl")
        self.wts_file = os.path.join(directory, f"{self.basename}.wts")
        
        # 初始化数据结构
        # 节点和模块相关的计数器
        self.num_modules = 0    # 所有模块数量（包括可移动和固定的）
        self.num_nodes = 0      # 可移动节点数量
        self.num_terminals = 0  # 端子（固定节点）数量
        self.num_nets = 0       # 网表数量
        self.num_pins = 0       # 引脚数量
        self.max_net_degree = 0 # 最大网表度数
        
        # 核心区域相关信息
        self.core_lower_left = (0, 0)  # 核心区域左下角坐标
        self.core_upper_right = (0, 0)  # 核心区域右上角坐标
        self.row_height = 0            # 行高
        self.row_number = 0            # 行数
        self.site_step = 0             # 站点步长
        
        # 面积相关信息
        self.core_area = 0          # 核心区域面积
        self.cell_area = 0          # 单元面积
        self.movable_area = 0       # 可移动区域面积
        self.fixed_area = 0         # 固定区域面积
        self.fixed_area_in_core = 0  # 核心区域内的固定区域面积
        
        # 利用率相关信息
        self.placement_util = 0  # 放置利用率
        self.core_density = 0    # 核心密度
        
        # 单元和对象计数
        self.cell_count = 0    # 单元数量
        self.object_count = 0   # 对象数量
        self.fixed_count = 0    # 固定对象数量
        self.macro_count = 0    # 宏单元数量
        
        # 网表相关统计
        self.net_count = 0           # 网表总数
        self.pin_2_count = 0         # 2引脚网表数量
        self.pin_3_10_count = 0      # 3-10引脚网表数量
        self.pin_11_100_count = 0    # 11-100引脚网表数量
        self.pin_100_plus_count = 0  # 100+引脚网表数量
        self.total_pin_count = 0      # 总引脚数
        
        # Bin 设置（用于分区统计）
        self.bin_dimension = [512, 512]  # Bin的尺寸
        self.bin_step = [0, 0]          # Bin的步长
        
        # 初始布局相关数据结构
        self.nodes = {}  # 存储所有节点信息，键为节点名称，值为节点对象
        self.nets = []   # 存储所有网表信息
        self.fixed_nodes = {}  # 存储固定节点信息
        self.movable_nodes = {}  # 存储可移动节点信息
        
    def parse_aux(self):
        """
        解析.aux文件，获取其他文件的名称
        
        .aux文件是BookShelf格式的入口文件，它指定了其他相关文件的名称。
        文件格式通常为：“RowBasedPlacement : 文件1 文件2 文件3 文件4 文件5”
        """
        try:
            with open(self.aux_file, 'r') as f:
                line = f.readline().strip()  # 读取第一行
                if "RowBasedPlacement" in line:  # 检查是否包含关键字
                    files = line.split(':')[1].strip().split()  # 分割并获取文件名列表
                    if len(files) >= 5:  # 确保有足够的文件
                        # 更新文件路径
                        self.nodes_file = os.path.join(self.directory, files[0])  # 节点文件
                        self.nets_file = os.path.join(self.directory, files[1])   # 网表文件
                        self.wts_file = os.path.join(self.directory, files[2])    # 权重文件
                        self.pl_file = os.path.join(self.directory, files[3])     # 放置文件
                        self.scl_file = os.path.join(self.directory, files[4])    # 行结构文件
        except Exception as e:
            print(f"解析.aux文件时出错: {e}")

    def parse_nodes(self):
        """
        解析.nodes文件，获取节点信息
        
        .nodes文件定义了电路中的单元和端子信息，包括它们的尺寸。
        文件格式包含头部信息（总模块数和端子数）和每个单元的具体信息。
        """
        try:
            with open(self.nodes_file, 'r') as f:
                lines = f.readlines()
                
                # 解析头部信息
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith("NumNodes"):  # 总模块数
                        self.num_modules = int(line.split(':')[1].strip())
                    elif line.startswith("NumTerminals"):  # 端子数
                        self.num_terminals = int(line.split(':')[1].strip())
                        break
                
                # 计算其他相关数据
                self.num_nodes = self.num_modules - self.num_terminals  # 可移动节点数 = 总模块数 - 端子数
                self.cell_count = self.num_nodes                      # 单元数量
                self.object_count = self.num_modules                  # 对象数量
                self.fixed_count = self.num_terminals                # 固定对象数量
                self.macro_count = 0  # 宏单元数量默认为0
                
                # 解析每个节点的信息
                node_start = False
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith("NumNodes") or line.startswith("NumTerminals"):
                        node_start = True
                        continue
                    
                    if node_start:
                        parts = line.split()
                        if len(parts) >= 3:
                            node_name = parts[0]
                            width = int(parts[1])
                            height = int(parts[2])
                            
                            # 创建节点对象
                            node = {
                                'name': node_name,
                                'width': width,
                                'height': height,
                                'x': 0,  # 初始坐标设为0
                                'y': 0,
                                'is_fixed': False,  # 默认为可移动节点
                                'area': width * height
                            }
                            
                            # 判断是否为端子（固定节点）
                            if len(self.nodes) >= self.num_modules - self.num_terminals:
                                node['is_fixed'] = True
                                self.fixed_nodes[node_name] = node
                            else:
                                self.movable_nodes[node_name] = node
                                
                            self.nodes[node_name] = node
                
                # 计算单元总面积
                self.cell_area = sum(node['area'] for node in self.movable_nodes.values())
                self.movable_area = self.cell_area
                
        except Exception as e:
            print(f"解析.nodes文件时出错: {e}")
    
    def parse_nets(self):
        """
        解析.nets文件，获取网表信息
        
        .nets文件定义了电路中的网表连接关系，包括每个网表的度数和连接的引脚。
        文件格式包含头部信息（网表数和引脚数）和每个网表的具体连接信息。
        """
        try:
            with open(self.nets_file, 'r') as f:
                lines = f.readlines()
                
                # 解析头部信息
                for line in lines:
                    line = line.strip()
                    if line.startswith("NumNets"):  # 网表总数
                        self.num_nets = int(line.split(':')[1].strip())
                    elif line.startswith("NumPins"):  # 引脚总数
                        self.num_pins = int(line.split(':')[1].strip())
                        break
                
                # 设置网表相关计数
                self.net_count = self.num_nets            # 网表总数
                self.total_pin_count = self.num_pins      # 引脚总数
                
                # 解析每个网表的信息
                current_net = None
                net_pins = []
                net_degrees = []
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith("NumNets") or line.startswith("NumPins"):
                        continue
                    
                    if line.startswith("NetDegree"):
                        # 如果已经有一个网表正在解析，先保存它
                        if current_net is not None and net_pins:
                            self.nets.append({
                                'name': current_net,
                                'pins': net_pins,
                                'degree': len(net_pins)
                            })
                            net_degrees.append(len(net_pins))
                        
                        # 开始新网表的解析
                        parts = line.split(':')
                        degree = int(parts[1].strip().split()[0])
                        net_name = parts[1].strip().split()[1] if len(parts[1].strip().split()) > 1 else f"net_{len(self.nets)}"
                        current_net = net_name
                        net_pins = []
                    else:
                        # 解析引脚信息
                        parts = line.split()
                        if len(parts) >= 1:
                            node_name = parts[0]
                            pin_type = parts[1] if len(parts) > 1 else "I"  # 默认为输入引脚
                            
                            # 检查节点是否存在
                            if node_name in self.nodes:
                                net_pins.append({
                                    'node': node_name,
                                    'type': pin_type
                                })
                
                # 保存最后一个网表
                if current_net is not None and net_pins:
                    self.nets.append({
                        'name': current_net,
                        'pins': net_pins,
                        'degree': len(net_pins)
                    })
                    net_degrees.append(len(net_pins))
                
                # 计算网表度数统计
                if net_degrees:
                    self.max_net_degree = max(net_degrees)
                    self.pin_2_count = sum(1 for d in net_degrees if d == 2)
                    self.pin_3_10_count = sum(1 for d in net_degrees if 3 <= d <= 10)
                    self.pin_11_100_count = sum(1 for d in net_degrees if 11 <= d <= 100)
                    self.pin_100_plus_count = sum(1 for d in net_degrees if d > 100)
                
        except Exception as e:
            print(f"解析.nets文件时出错: {e}")
    
    def parse_scl(self):
        """
        解析.scl文件，获取行信息
        
        .scl文件定义了布局中的行结构信息，包括行数、行高、站点宽度等。
        这些信息用于确定核心区域的大小和形状。
        """
        try:
            with open(self.scl_file, 'r') as f:
                lines = f.readlines()
                
                # 初始化变量
                min_x = float('inf')
                max_x = float('-inf')
                min_y = float('inf')
                max_y = float('-inf')
                
                # 解析行数
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith("NumRows"):  # 解析行数
                        try:
                            self.row_number = int(line.split(':')[1].strip())
                        except (IndexError, ValueError):
                            print("警告: 无法解析行数")
                    elif line.startswith("CoreRow Horizontal"):  # 找到行定义块
                        # 解析行信息
                        row_info = {}
                        j = i + 1
                        while j < len(lines) and not lines[j].strip().startswith("End"):
                            row_line = lines[j].strip()
                            
                            if row_line.startswith("Coordinate"):  # Y坐标
                                try:
                                    y_coord = int(row_line.split(':')[1].strip())
                                    row_info['y'] = y_coord
                                    min_y = min(min_y, y_coord)
                                except (IndexError, ValueError):
                                    pass
                            elif row_line.startswith("Height"):  # 行高
                                try:
                                    height = int(row_line.split(':')[1].strip())
                                    row_info['height'] = height
                                    if self.row_height == 0:
                                        self.row_height = height
                                except (IndexError, ValueError):
                                    pass
                            elif row_line.startswith("Sitewidth"):  # 站点宽度
                                try:
                                    site_width = float(row_line.split(':')[1].strip())
                                    row_info['site_width'] = site_width
                                    if self.site_step == 0:
                                        self.site_step = site_width
                                except (IndexError, ValueError):
                                    pass
                            elif row_line.startswith("SubrowOrigin"):  # 子行起始点
                                try:
                                    parts = row_line.split(':')
                                    if len(parts) >= 3:
                                        x_origin = int(parts[1].strip().split()[0])
                                        num_sites = int(parts[2].strip().split()[1])
                                        
                                        row_info['x'] = x_origin
                                        row_info['num_sites'] = num_sites
                                        
                                        min_x = min(min_x, x_origin)
                                        max_x = max(max_x, x_origin + num_sites * self.site_step - 1)
                                        
                                        # 计算行的最大Y坐标
                                        if 'y' in row_info and 'height' in row_info:
                                            max_y = max(max_y, row_info['y'] + row_info['height'] - 1)
                                except (IndexError, ValueError):
                                    pass
                            
                            j += 1
                
                # 设置核心区域坐标
                if min_x != float('inf') and min_y != float('inf') and max_x != float('-inf') and max_y != float('-inf'):
                    self.core_lower_left = (min_x, min_y)
                    self.core_upper_right = (max_x, max_y)
                else:
                    # 如果无法解析，使用默认值
                    self.core_lower_left = (0, 0)
                    self.core_upper_right = (10000, 10000)
                
                # 计算核心区域面积
                width = self.core_upper_right[0] - self.core_lower_left[0] + 1
                height = self.core_upper_right[1] - self.core_lower_left[1] + 1
                self.core_area = width * height
                
        except Exception as e:
            print(f"解析.scl文件时出错: {e}")
    
    def parse_pl(self):
        """
        解析.pl文件，获取放置信息
        
        .pl文件定义了单元的放置位置，包括坐标和方向。
        文件格式包含每个单元的名称、x坐标、y坐标和方向。
        固定单元用'F'标记，可移动单元用'N'标记。
        """
        try:
            with open(self.pl_file, 'r') as f:
                lines = f.readlines()
                
                # 跳过头部信息
                start_line = 0
                for i, line in enumerate(lines):
                    if line.startswith("UCLA pl"):
                        start_line = i + 1
                        break
                
                # 解析每个节点的放置信息
                fixed_area = 0
                fixed_area_in_core = 0
                
                for line in lines[start_line:]:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 4:
                        node_name = parts[0]
                        x = float(parts[1])
                        y = float(parts[2])
                        orientation = parts[3]
                        
                        # 检查节点是否存在
                        if node_name in self.nodes:
                            node = self.nodes[node_name]
                            node['x'] = x
                            node['y'] = y
                            node['orientation'] = orientation
                            
                            # 检查是否为固定节点
                            if orientation == "F" or node_name in self.fixed_nodes:
                                node['is_fixed'] = True
                                self.fixed_nodes[node_name] = node
                                
                                # 计算固定区域面积
                                if 'area' in node:
                                    fixed_area += node['area']
                                    
                                    # 检查是否在核心区域内
                                    if (self.core_lower_left[0] <= x <= self.core_upper_right[0] and
                                        self.core_lower_left[1] <= y <= self.core_upper_right[1]):
                                        fixed_area_in_core += node['area']
                
                # 更新固定区域面积
                self.fixed_area = fixed_area
                self.fixed_area_in_core = fixed_area_in_core
                
        except Exception as e:
            print(f"解析.pl文件时出错: {e}")
    
    def parse_all(self):
        """
        解析所有文件并计算指标
        
        按顺序调用各个解析方法，并计算所需的时间。
        
        返回值:
            float: 解析所有文件并计算指标所需的时间（秒）
        """
        start_time = time.time()  # 记录开始时间
        
        # 按顺序调用各个解析方法
        self.parse_aux()           # 解析.aux文件，获取其他文件的名称
        self.parse_nodes()         # 解析.nodes文件，获取节点信息
        self.parse_nets()          # 解析.nets文件，获取网表信息
        self.parse_scl()           # 解析.scl文件，获取行信息
        self.parse_pl()            # 解析.pl文件，获取放置信息
        
        # 计算总耗时
        parse_time = time.time() - start_time
        return parse_time
    
    def build_quadratic_matrix(self):
        """
        构建二次解析器的矩阵
        
        根据网表连接关系构建二次解析器的矩阵，用于求解初始布局。
        使用稀疏矩阵表示以提高计算效率。
        
        返回值:
            tuple: 包含二次解析器的矩阵和向量 (A_x, b_x, A_y, b_y)
        """
        try:
            # 获取可移动节点列表
            movable_nodes_list = list(self.movable_nodes.keys())
            n = len(movable_nodes_list)
            
            # 创建节点名称到索引的映射
            node_to_idx = {node: i for i, node in enumerate(movable_nodes_list)}
            
            # 初始化稀疏矩阵的数据结构
            rows = []
            cols = []
            data = []
            
            # 初始化右侧向量
            b_x = np.zeros(n)
            b_y = np.zeros(n)
            
            # 对每个网表进行处理
            for net in self.nets:
                pins = net['pins']
                degree = len(pins)
                
                if degree <= 1:
                    continue  # 跳过只有一个引脚的网表
                
                # 计算每对节点之间的权重
                weight = 1.0 / (degree - 1)
                
                # 收集固定节点的信息
                fixed_x = 0
                fixed_y = 0
                fixed_count = 0
                
                # 处理固定节点
                for pin in pins:
                    node_name = pin['node']
                    if node_name in self.fixed_nodes:
                        node = self.fixed_nodes[node_name]
                        fixed_x += node['x']
                        fixed_y += node['y']
                        fixed_count += 1
                
                # 对每对可移动节点添加连接
                for i, pin_i in enumerate(pins):
                    node_i = pin_i['node']
                    
                    # 跳过固定节点
                    if node_i not in self.movable_nodes:
                        continue
                    
                    idx_i = node_to_idx[node_i]
                    
                    # 处理可移动节点之间的连接
                    for j, pin_j in enumerate(pins):
                        if i == j:
                            continue
                            
                        node_j = pin_j['node']
                        
                        if node_j in self.movable_nodes:
                            # 可移动节点之间的连接
                            idx_j = node_to_idx[node_j]
                            
                            # 添加对角线元素
                            rows.append(idx_i)
                            cols.append(idx_i)
                            data.append(weight)
                            
                            # 添加非对角线元素
                            rows.append(idx_i)
                            cols.append(idx_j)
                            data.append(-weight)
                    
                    # 处理固定节点对可移动节点的影响
                    if fixed_count > 0:
                        b_x[idx_i] += weight * fixed_x
                        b_y[idx_i] += weight * fixed_y
            
            # 创建稀疏矩阵
            A = sparse.coo_matrix((data, (rows, cols)), shape=(n, n))
            A = A.tocsr()  # 转换为CSR格式以提高计算效率
            
            return A, b_x, A, b_y
            
        except Exception as e:
            print(f"构建二次解析器矩阵时出错: {e}")
            return None, None, None, None
    
    def solve_quadratic_placement(self):
        """
        求解二次解析器并计算初始布局
        
        使用二次解析器求解初始布局问题，并更新节点的坐标。
        
        返回值:
            bool: 求解是否成功
        """
        try:
            # 构建二次解析器矩阵
            A_x, b_x, A_y, b_y = self.build_quadratic_matrix()
            
            if A_x is None or b_x is None or A_y is None or b_y is None:
                return False
            
            # 获取可移动节点列表
            movable_nodes_list = list(self.movable_nodes.keys())
            
            # 求解线性方程组
            try:
                x = spsolve(A_x, b_x)
                y = spsolve(A_y, b_y)
            except Exception as e:
                print(f"求解线性方程组时出错: {e}")
                return False
            
            # 更新节点坐标
            for i, node_name in enumerate(movable_nodes_list):
                node = self.movable_nodes[node_name]
                node['x'] = float(x[i])
                node['y'] = float(y[i])
            
            return True
            
        except Exception as e:
            print(f"求解二次解析器时出错: {e}")
            return False
    
    def legalize_placement(self):
        """
        合法化初始布局
        
        将初始布局结果调整到核心区域内，避免节点超出边界。
        这是一个简化的合法化过程，只进行边界检查。
        """
        try:
            # 获取核心区域边界
            min_x, min_y = self.core_lower_left
            max_x, max_y = self.core_upper_right
            
            # 对每个可移动节点进行合法化
            for node_name, node in self.movable_nodes.items():
                # 考虑节点尺寸
                width = node['width']
                height = node['height']
                
                # 调整X坐标
                if node['x'] < min_x:
                    node['x'] = min_x
                elif node['x'] + width > max_x:
                    node['x'] = max_x - width
                
                # 调整Y坐标
                if node['y'] < min_y:
                    node['y'] = min_y
                elif node['y'] + height > max_y:
                    node['y'] = max_y - height
            
            return True
            
        except Exception as e:
            print(f"合法化初始布局时出错: {e}")
            return False
    
    def write_placement_result(self, output_file):
        """
        将初始布局结果写入文件
        
        将初始布局结果写入.pl格式的文件中。
        
        参数:
            output_file (str): 输出文件路径
            
        返回值:
            bool: 写入是否成功
        """
        try:
            with open(output_file, 'w') as f:
                # 写入头部信息
                f.write("UCLA pl 1.0\n")
                f.write("# Generated by Initial Placement Program\n")
                f.write("# Date: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                
                # 写入固定节点信息
                for node_name, node in self.fixed_nodes.items():
                    f.write(f"{node_name}\t{node['x']:.6f}\t{node['y']:.6f}\t: F\n")
                
                # 写入可移动节点信息
                for node_name, node in self.movable_nodes.items():
                    f.write(f"{node_name}\t{node['x']:.6f}\t{node['y']:.6f}\t: N\n")
                
            return True
            
        except Exception as e:
            print(f"写入初始布局结果时出错: {e}")
            return False
    
    def visualize_placement(self, output_file=None):
        """
        可视化初始布局结果
        
        使用matplotlib将初始布局结果可视化。
        
        参数:
            output_file (str, optional): 输出图像文件路径，如果为None则显示图像
        """
        try:
            # 创建图形
            plt.figure(figsize=(12, 10))
            
            # 绘制核心区域
            min_x, min_y = self.core_lower_left
            max_x, max_y = self.core_upper_right
            width = max_x - min_x
            height = max_y - min_y
            plt.plot([min_x, max_x, max_x, min_x, min_x], [min_y, min_y, max_y, max_y, min_y], 'k-', linewidth=2)
            
            # 绘制固定节点
            for node_name, node in self.fixed_nodes.items():
                x = node['x']
                y = node['y']
                width = node['width']
                height = node['height']
                plt.plot([x, x+width, x+width, x, x], [y, y, y+height, y+height, y], 'r-')
                plt.text(x + width/2, y + height/2, node_name, fontsize=8, ha='center', va='center')
            
            # 绘制可移动节点
            for node_name, node in self.movable_nodes.items():
                x = node['x']
                y = node['y']
                width = node['width']
                height = node['height']
                plt.plot([x, x+width, x+width, x, x], [y, y, y+height, y+height, y], 'b-')
                
                # 对于大型节点显示名称
                if width * height > 100:
                    plt.text(x + width/2, y + height/2, node_name, fontsize=6, ha='center', va='center')
            
            # 设置图形属性
            plt.title(f'Initial Placement Result for {self.basename}')
            plt.xlabel('X Coordinate')
            plt.ylabel('Y Coordinate')
            plt.grid(True)
            
            # 保存或显示图形
            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"已将可视化结果保存到 {output_file}")
            else:
                plt.show()
                
            return True
            
        except Exception as e:
            print(f"可视化初始布局结果时出错: {e}")
            return False
    
    def print_placement_statistics(self):
        """
        打印初始布局统计信息
        
        计算并打印初始布局的各种统计信息。
        """
        try:
            # 计算布局统计信息
            total_wirelength = 0
            total_overlap = 0
            out_of_bounds = 0
            
            # 计算总布线长度
            for net in self.nets:
                pins = net['pins']
                if len(pins) <= 1:
                    continue
                    
                # 计算半周长布线长度
                min_x = float('inf')
                max_x = float('-inf')
                min_y = float('inf')
                max_y = float('-inf')
                
                for pin in pins:
                    node_name = pin['node']
                    if node_name in self.nodes:
                        node = self.nodes[node_name]
                        x = node['x'] + node['width'] / 2  # 使用节点中心
                        y = node['y'] + node['height'] / 2
                        
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)
                
                # 半周长布线长度
                wirelength = (max_x - min_x) + (max_y - min_y)
                total_wirelength += wirelength
            
            # 检查超出边界的节点
            min_x, min_y = self.core_lower_left
            max_x, max_y = self.core_upper_right
            
            for node_name, node in self.movable_nodes.items():
                x = node['x']
                y = node['y']
                width = node['width']
                height = node['height']
                
                if x < min_x or y < min_y or x + width > max_x or y + height > max_y:
                    out_of_bounds += 1
            
            # 打印统计信息
            print("\n初始布局统计信息:")
            print(f"\u603b节点数: {len(self.nodes)}")
            print(f"\u53ef移动节点数: {len(self.movable_nodes)}")
            print(f"\u56fa定节点数: {len(self.fixed_nodes)}")
            print(f"\u7f51表数: {len(self.nets)}")
            print(f"\u603b布线长度: {total_wirelength:.2f}")
            print(f"\u8d85出边界节点数: {out_of_bounds}")
            print(f"\u6838心区域: ({self.core_lower_left[0]}, {self.core_lower_left[1]}) - ({self.core_upper_right[0]}, {self.core_upper_right[1]})")
            
        except Exception as e:
            print(f"打印初始布局统计信息时出错: {e}")


class InitialPlacement:
    """
    初始布局类
    
    该类封装了初始布局的全过程，包括数据解析、二次解析器求解、合法化和结果输出。
    """
    def __init__(self, directory):
        """
        初始化初始布局对象
        
        参数:
            directory (str): BookShelf格式文件所在的目录路径
        """
        self.directory = directory
        self.basename = os.path.basename(directory)
        self.parser = BookshelfParser(directory)
        
    def run(self, output_dir=None, visualize=True):
        """
        运行初始布局算法
        
        执行完整的初始布局过程，包括数据解析、二次解析器求解、合法化和结果输出。
        
        参数:
            output_dir (str, optional): 输出目录路径，如果为None则使用输入目录
            visualize (bool): 是否可视化结果
            
        返回值:
            bool: 初始布局是否成功
        """
        try:
            # 设置输出目录
            if output_dir is None:
                output_dir = self.directory
            
            # 解析数据
            print(f"\u6b63在解析 {self.basename} 的BookShelf格式文件...")
            parse_time = self.parser.parse_all()
            print(f"\u6570据解析完成，耗时 {parse_time:.4f} 秒")
            
            # 求解二次解析器
            print("\u6b63在使用二次解析器计算初始布局...")
            start_time = time.time()
            success = self.parser.solve_quadratic_placement()
            if not success:
                print("\u4e8c次解析器求解失败")
                return False
            qp_time = time.time() - start_time
            print(f"\u4e8c次解析器求解完成，耗时 {qp_time:.4f} 秒")
            
            # 合法化初始布局
            print("\u6b63在合法化初始布局...")
            start_time = time.time()
            success = self.parser.legalize_placement()
            if not success:
                print("\u521d始布局合法化失败")
                return False
            legalize_time = time.time() - start_time
            print(f"\u521d始布局合法化完成，耗时 {legalize_time:.4f} 秒")
            
            # 输出结果
            output_pl_file = os.path.join(output_dir, f"{self.basename}_initial.pl")
            success = self.parser.write_placement_result(output_pl_file)
            if not success:
                print(f"\u5199入初始布局结果到 {output_pl_file} 失败")
                return False
            print(f"\u521d始布局结果已写入到 {output_pl_file}")
            
            # 打印统计信息
            self.parser.print_placement_statistics()
            
            # 可视化结果
            if visualize:
                output_img_file = os.path.join(output_dir, f"{self.basename}_initial.png")
                self.parser.visualize_placement(output_img_file)
            
            return True
            
        except Exception as e:
            print(f"\u8fd0行初始布局算法时出错: {e}")
            return False


def main():
    """
    主函数，程序的入口点
    """
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="初始布局程序")
    parser.add_argument("directory", help="BookShelf格式文件所在的目录路径")
    parser.add_argument("-o", "--output", help="输出目录路径，默认为输入目录")
    parser.add_argument("-v", "--visualize", action="store_true", help="是否可视化结果")
    args = parser.parse_args()
    
    # 创建初始布局对象并运行
    placement = InitialPlacement(args.directory)
    success = placement.run(args.output, args.visualize)
    
    if success:
        print("\n初始布局程序执行成功!")
        return 0
    else:
        print("\n初始布局程序执行失败!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
