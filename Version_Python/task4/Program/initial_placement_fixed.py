#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Initial Placement Program

This program implements an initial placement algorithm for integrated circuit layout design,
based on quadratic programming method. It reads layout data files in BookShelf format,
calculates initial placement positions, and outputs the results.
"""

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
    BookShelf format file parser class
    
    This class is used to parse layout data files in BookShelf format and calculate related statistics.
    """
    def __init__(self, directory):
        """
        Initialize the parser, set directory path and initialize data structures
        
        Parameters:
            directory (str): Directory path of BookShelf format files
        """
        self.directory = directory
        self.basename = os.path.basename(directory)
        
        # File paths
        self.aux_file = os.path.join(directory, f"{self.basename}.aux")
        self.nodes_file = os.path.join(directory, f"{self.basename}.nodes")
        self.nets_file = os.path.join(directory, f"{self.basename}.nets")
        self.pl_file = os.path.join(directory, f"{self.basename}.pl")
        self.scl_file = os.path.join(directory, f"{self.basename}.scl")
        self.wts_file = os.path.join(directory, f"{self.basename}.wts")
        
        # Initialize data structures
        # Node and module related counters
        self.num_modules = 0    # Total number of modules (including movable and fixed)
        self.num_nodes = 0      # Number of movable nodes
        self.num_terminals = 0  # Number of terminals (fixed nodes)
        self.num_nets = 0       # Number of nets
        self.num_pins = 0       # Number of pins
        self.max_net_degree = 0 # Maximum net degree
        
        # Core region related information
        self.core_lower_left = (0, 0)  # Core region lower left coordinates
        self.core_upper_right = (0, 0)  # Core region upper right coordinates
        self.row_height = 0            # Row height
        self.row_number = 0            # Number of rows
        self.site_step = 0             # Site step
        
        # Area related information
        self.core_area = 0          # Core region area
        self.cell_area = 0          # Cell area
        self.movable_area = 0       # Movable area
        self.fixed_area = 0         # Fixed area
        self.fixed_area_in_core = 0  # Fixed area in core
        
        # Utilization related information
        self.placement_util = 0  # Placement utilization
        self.core_density = 0    # Core density
        
        # Cell and object counts
        self.cell_count = 0    # Cell count
        self.object_count = 0   # Object count
        self.fixed_count = 0    # Fixed object count
        self.macro_count = 0    # Macro count
        
        # Net related statistics
        self.net_count = 0           # Net count
        self.pin_2_count = 0         # 2-pin net count
        self.pin_3_10_count = 0      # 3-10 pin net count
        self.pin_11_100_count = 0    # 11-100 pin net count
        self.pin_100_plus_count = 0  # 100+ pin net count
        self.total_pin_count = 0      # Total pin count
        
        # Bin settings
        self.bin_dimension = [512, 512]  # Bin dimensions
        self.bin_step = [0, 0]          # Bin step
        
        # Initial placement related data structures
        self.nodes = {}  # Store all node information, key is node name, value is node object
        self.nets = []   # Store all net information
        self.fixed_nodes = {}  # Store fixed node information
        self.movable_nodes = {}  # Store movable node information
        
    def parse_aux(self):
        """
        Parse .aux file to get names of other files
        
        The .aux file is the entry file of BookShelf format, which specifies the names of other related files.
        """
        try:
            with open(self.aux_file, 'r') as f:
                line = f.readline().strip()  # Read the first line
                if "RowBasedPlacement" in line:  # Check if it contains the keyword
                    files = line.split(':')[1].strip().split()  # Split and get the file name list
                    if len(files) >= 5:  # Make sure there are enough files
                        # Update file paths
                        self.nodes_file = os.path.join(self.directory, files[0])  # Nodes file
                        self.nets_file = os.path.join(self.directory, files[1])   # Nets file
                        self.wts_file = os.path.join(self.directory, files[2])    # Weights file
                        self.pl_file = os.path.join(self.directory, files[3])     # Placement file
                        self.scl_file = os.path.join(self.directory, files[4])    # Row structure file
        except Exception as e:
            print(f"Error parsing .aux file: {e}")
    
    def parse_nodes(self):
        """
        Parse .nodes file to get node information
        
        The .nodes file defines the cells and terminals in the circuit, including their dimensions.
        """
        try:
            with open(self.nodes_file, 'r') as f:
                lines = f.readlines()
                
                # Parse header information
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith("NumNodes"):  # Total number of modules
                        self.num_modules = int(line.split(':')[1].strip())
                    elif line.startswith("NumTerminals"):  # Number of terminals
                        self.num_terminals = int(line.split(':')[1].strip())
                        break
                
                # Calculate other related data
                self.num_nodes = self.num_modules - self.num_terminals  # Number of movable nodes = Total modules - Terminals
                self.cell_count = self.num_nodes                      # Cell count
                self.object_count = self.num_modules                  # Object count
                self.fixed_count = self.num_terminals                # Fixed object count
                self.macro_count = 0  # Macro count default to 0
                
                # Parse information for each node
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
                            
                            # Create node object
                            node = {
                                'name': node_name,
                                'width': width,
                                'height': height,
                                'x': 0,  # Initial coordinates set to 0
                                'y': 0,
                                'is_fixed': False,  # Default to movable node
                                'area': width * height
                            }
                            
                            # Determine if it's a terminal (fixed node)
                            if len(self.nodes) >= self.num_modules - self.num_terminals:
                                node['is_fixed'] = True
                                self.fixed_nodes[node_name] = node
                            else:
                                self.movable_nodes[node_name] = node
                                
                            self.nodes[node_name] = node
                
                # Calculate total cell area
                self.cell_area = sum(node['area'] for node in self.movable_nodes.values())
                self.movable_area = self.cell_area
                
        except Exception as e:
            print(f"Error parsing .nodes file: {e}")
    
    def parse_nets(self):
        """
        Parse .nets file to get net information
        
        The .nets file defines the net connections in the circuit, including the degree of each net and the connected pins.
        """
        try:
            with open(self.nets_file, 'r') as f:
                lines = f.readlines()
                
                # Parse header information
                for line in lines:
                    line = line.strip()
                    if line.startswith("NumNets"):  # Total number of nets
                        self.num_nets = int(line.split(':')[1].strip())
                    elif line.startswith("NumPins"):  # Total number of pins
                        self.num_pins = int(line.split(':')[1].strip())
                        break
                
                # Set net related counts
                self.net_count = self.num_nets            # Net count
                self.total_pin_count = self.num_pins      # Total pin count
                
                # Parse information for each net
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
                        # If there's already a net being parsed, save it first
                        if current_net is not None and net_pins:
                            self.nets.append({
                                'name': current_net,
                                'pins': net_pins,
                                'degree': len(net_pins)
                            })
                            net_degrees.append(len(net_pins))
                        
                        # Start parsing a new net
                        parts = line.split(':')
                        degree = int(parts[1].strip().split()[0])
                        net_name = parts[1].strip().split()[1] if len(parts[1].strip().split()) > 1 else f"net_{len(self.nets)}"
                        current_net = net_name
                        net_pins = []
                    else:
                        # Parse pin information
                        parts = line.split()
                        if len(parts) >= 1:
                            node_name = parts[0]
                            pin_type = parts[1] if len(parts) > 1 else "I"  # Default to input pin
                            
                            # Check if the node exists
                            if node_name in self.nodes:
                                net_pins.append({
                                    'node': node_name,
                                    'type': pin_type
                                })
                
                # Save the last net
                if current_net is not None and net_pins:
                    self.nets.append({
                        'name': current_net,
                        'pins': net_pins,
                        'degree': len(net_pins)
                    })
                    net_degrees.append(len(net_pins))
                
                # Calculate net degree statistics
                if net_degrees:
                    self.max_net_degree = max(net_degrees)
                    self.pin_2_count = sum(1 for d in net_degrees if d == 2)
                    self.pin_3_10_count = sum(1 for d in net_degrees if 3 <= d <= 10)
                    self.pin_11_100_count = sum(1 for d in net_degrees if 11 <= d <= 100)
                    self.pin_100_plus_count = sum(1 for d in net_degrees if d > 100)
                
        except Exception as e:
            print(f"Error parsing .nets file: {e}")
    
    def parse_scl(self):
        """
        Parse .scl file to get row information
        
        The .scl file defines the row structure information in the layout, including the number of rows, row height, and site width.
        """
        try:
            with open(self.scl_file, 'r') as f:
                lines = f.readlines()
                
                # Initialize variables
                min_x = float('inf')
                max_x = float('-inf')
                min_y = float('inf')
                max_y = float('-inf')
                
                # Parse row number
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line.startswith("NumRows"):  # Parse row number
                        try:
                            self.row_number = int(line.split(':')[1].strip())
                        except (IndexError, ValueError):
                            print("Warning: Unable to parse row number")
                    elif line.startswith("CoreRow Horizontal"):  # Find row definition block
                        # Parse row information
                        row_info = {}
                        j = i + 1
                        while j < len(lines) and not lines[j].strip().startswith("End"):
                            row_line = lines[j].strip()
                            
                            if row_line.startswith("Coordinate"):  # Y coordinate
                                try:
                                    y_coord = int(row_line.split(':')[1].strip())
                                    row_info['y'] = y_coord
                                    min_y = min(min_y, y_coord)
                                except (IndexError, ValueError):
                                    pass
                            elif row_line.startswith("Height"):  # Row height
                                try:
                                    height = int(row_line.split(':')[1].strip())
                                    row_info['height'] = height
                                    if self.row_height == 0:
                                        self.row_height = height
                                except (IndexError, ValueError):
                                    pass
                            elif row_line.startswith("Sitewidth"):  # Site width
                                try:
                                    site_width = float(row_line.split(':')[1].strip())
                                    row_info['site_width'] = site_width
                                    if self.site_step == 0:
                                        self.site_step = site_width
                                except (IndexError, ValueError):
                                    pass
                            elif row_line.startswith("SubrowOrigin"):  # Subrow origin
                                try:
                                    parts = row_line.split(':')
                                    if len(parts) >= 3:
                                        x_origin = int(parts[1].strip().split()[0])
                                        num_sites = int(parts[2].strip().split()[1])
                                        
                                        row_info['x'] = x_origin
                                        row_info['num_sites'] = num_sites
                                        
                                        min_x = min(min_x, x_origin)
                                        max_x = max(max_x, x_origin + num_sites * self.site_step - 1)
                                        
                                        # Calculate maximum Y coordinate of the row
                                        if 'y' in row_info and 'height' in row_info:
                                            max_y = max(max_y, row_info['y'] + row_info['height'] - 1)
                                except (IndexError, ValueError):
                                    pass
                            
                            j += 1
                
                # Set core region coordinates
                if min_x != float('inf') and min_y != float('inf') and max_x != float('-inf') and max_y != float('-inf'):
                    self.core_lower_left = (min_x, min_y)
                    self.core_upper_right = (max_x, max_y)
                else:
                    # If parsing fails, use default values
                    self.core_lower_left = (0, 0)
                    self.core_upper_right = (10000, 10000)
                
                # Calculate core region area
                width = self.core_upper_right[0] - self.core_lower_left[0] + 1
                height = self.core_upper_right[1] - self.core_lower_left[1] + 1
                self.core_area = width * height
                
        except Exception as e:
            print(f"Error parsing .scl file: {e}")
    
    def parse_pl(self):
        """
        Parse .pl file to get placement information
        
        The .pl file defines the placement positions of cells, including coordinates and orientation.
        """
        try:
            with open(self.pl_file, 'r') as f:
                lines = f.readlines()
                
                # Skip header information
                start_line = 0
                for i, line in enumerate(lines):
                    if line.startswith("UCLA pl"):
                        start_line = i + 1
                        break
                
                # Parse placement information for each node
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
                        
                        # Check if the node exists
                        if node_name in self.nodes:
                            node = self.nodes[node_name]
                            node['x'] = x
                            node['y'] = y
                            node['orientation'] = orientation
                            
                            # Check if it's a fixed node
                            if orientation == "F" or node_name in self.fixed_nodes:
                                node['is_fixed'] = True
                                self.fixed_nodes[node_name] = node
                                
                                # Calculate fixed area
                                if 'area' in node:
                                    fixed_area += node['area']
                                    
                                    # Check if it's in the core region
                                    if (self.core_lower_left[0] <= x <= self.core_upper_right[0] and
                                        self.core_lower_left[1] <= y <= self.core_upper_right[1]):
                                        fixed_area_in_core += node['area']
                
                # Update fixed area
                self.fixed_area = fixed_area
                self.fixed_area_in_core = fixed_area_in_core
                
        except Exception as e:
            print(f"Error parsing .pl file: {e}")
    
    def parse_all(self):
        """
        Parse all files and calculate metrics
        
        Call each parsing method in sequence and calculate the time required.
        
        Returns:
            float: Time (in seconds) required to parse all files and calculate metrics
        """
        start_time = time.time()  # Record start time
        
        # Call each parsing method in sequence
        self.parse_aux()           # Parse .aux file to get names of other files
        self.parse_nodes()         # Parse .nodes file to get node information
        self.parse_nets()          # Parse .nets file to get net information
        self.parse_scl()           # Parse .scl file to get row information
        self.parse_pl()            # Parse .pl file to get placement information
        
        # Calculate total time
        parse_time = time.time() - start_time
        return parse_time
    
    def build_quadratic_matrix(self):
        """
        Build the matrix for quadratic solver
        
        Build the matrix for quadratic solver based on net connections, used to solve the initial placement.
        Use sparse matrix representation to improve computational efficiency.
        
        Returns:
            tuple: Containing the matrices and vectors for quadratic solver (A_x, b_x, A_y, b_y)
        """
        try:
            # Get the list of movable nodes
            movable_nodes_list = list(self.movable_nodes.keys())
            n = len(movable_nodes_list)
            
            # Create mapping from node name to index
            node_to_idx = {node: i for i, node in enumerate(movable_nodes_list)}
            
            # Initialize data structures for sparse matrix
            rows = []
            cols = []
            data = []
            
            # Initialize right-hand side vectors
            b_x = np.zeros(n)
            b_y = np.zeros(n)
            
            # Process each net
            for net in self.nets:
                pins = net['pins']
                degree = len(pins)
                
                if degree <= 1:
                    continue  # Skip nets with only one pin
                
                # Calculate weight between each pair of nodes
                weight = 1.0 / (degree - 1)
                
                # Collect information about fixed nodes
                fixed_x = 0
                fixed_y = 0
                fixed_count = 0
                
                # Process fixed nodes
                for pin in pins:
                    node_name = pin['node']
                    if node_name in self.fixed_nodes:
                        node = self.fixed_nodes[node_name]
                        fixed_x += node['x']
                        fixed_y += node['y']
                        fixed_count += 1
                
                # Add connections for each pair of movable nodes
                for i, pin_i in enumerate(pins):
                    node_i = pin_i['node']
                    
                    # Skip fixed nodes
                    if node_i not in self.movable_nodes:
                        continue
                    
                    idx_i = node_to_idx[node_i]
                    
                    # Process connections between movable nodes
                    for j, pin_j in enumerate(pins):
                        if i == j:
                            continue
                            
                        node_j = pin_j['node']
                        
                        if node_j in self.movable_nodes:
                            # Connection between movable nodes
                            idx_j = node_to_idx[node_j]
                            
                            # Add diagonal element
                            rows.append(idx_i)
                            cols.append(idx_i)
                            data.append(weight)
                            
                            # Add off-diagonal element
                            rows.append(idx_i)
                            cols.append(idx_j)
                            data.append(-weight)
                    
                    # Process influence of fixed nodes on movable nodes
                    if fixed_count > 0:
                        b_x[idx_i] += weight * fixed_x
                        b_y[idx_i] += weight * fixed_y
            
            # Create sparse matrix
            A = sparse.coo_matrix((data, (rows, cols)), shape=(n, n))
            A = A.tocsr()  # Convert to CSR format for computational efficiency
            
            return A, b_x, A, b_y
            
        except Exception as e:
            print(f"Error building quadratic matrix: {e}")
            return None, None, None, None
    
    def solve_quadratic_placement(self):
        """
        Solve quadratic placement and calculate initial placement
        
        Use quadratic solver to solve the initial placement problem and update node coordinates.
        
        Returns:
            bool: Whether the solution is successful
        """
        try:
            # Build quadratic matrix
            A_x, b_x, A_y, b_y = self.build_quadratic_matrix()
            
            if A_x is None or b_x is None or A_y is None or b_y is None:
                return False
            
            # Get the list of movable nodes
            movable_nodes_list = list(self.movable_nodes.keys())
            
            # Solve linear equation system
            try:
                x = spsolve(A_x, b_x)
                y = spsolve(A_y, b_y)
            except Exception as e:
                print(f"Error solving linear equation system: {e}")
                return False
            
            # Update node coordinates
            for i, node_name in enumerate(movable_nodes_list):
                node = self.movable_nodes[node_name]
                node['x'] = float(x[i])
                node['y'] = float(y[i])
            
            return True
            
        except Exception as e:
            print(f"Error solving quadratic placement: {e}")
            return False
    
    def legalize_placement(self):
        """
        Legalize initial placement
        
        Adjust the initial placement results to be within the core region, avoiding nodes exceeding boundaries.
        This is a simplified legalization process that only performs boundary checking.
        """
        try:
            # Get core region boundaries
            min_x, min_y = self.core_lower_left
            max_x, max_y = self.core_upper_right
            
            # Legalize each movable node
            for node_name, node in self.movable_nodes.items():
                # Consider node dimensions
                width = node['width']
                height = node['height']
                
                # Adjust X coordinate
                if node['x'] < min_x:
                    node['x'] = min_x
                elif node['x'] + width > max_x:
                    node['x'] = max_x - width
                
                # Adjust Y coordinate
                if node['y'] < min_y:
                    node['y'] = min_y
                elif node['y'] + height > max_y:
                    node['y'] = max_y - height
            
            return True
            
        except Exception as e:
            print(f"Error legalizing initial placement: {e}")
            return False
    
    def write_placement_result(self, output_file):
        """
        Write initial placement results to file
        
        Write the initial placement results to a .pl format file.
        
        Parameters:
            output_file (str): Output file path
            
        Returns:
            bool: Whether the write is successful
        """
        try:
            with open(output_file, 'w') as f:
                # Write header information
                f.write("UCLA pl 1.0\n")
                f.write("# Generated by Initial Placement Program\n")
                f.write("# Date: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                
                # Write fixed node information
                for node_name, node in self.fixed_nodes.items():
                    f.write(f"{node_name}\t{node['x']:.6f}\t{node['y']:.6f}\t: F\n")
                
                # Write movable node information
                for node_name, node in self.movable_nodes.items():
                    f.write(f"{node_name}\t{node['x']:.6f}\t{node['y']:.6f}\t: N\n")
                
            return True
            
        except Exception as e:
            print(f"Error writing initial placement results: {e}")
            return False
    
    def visualize_placement(self, output_file=None):
        """
        Visualize initial placement results
        
        Use matplotlib to visualize the initial placement results.
        
        Parameters:
            output_file (str, optional): Output image file path, if None then display the image
        """
        try:
            # Create figure
            plt.figure(figsize=(12, 10))
            
            # Draw core region
            min_x, min_y = self.core_lower_left
            max_x, max_y = self.core_upper_right
            width = max_x - min_x
            height = max_y - min_y
            plt.plot([min_x, max_x, max_x, min_x, min_x], [min_y, min_y, max_y, max_y, min_y], 'k-', linewidth=2)
            
            # Draw fixed nodes
            for node_name, node in self.fixed_nodes.items():
                x = node['x']
                y = node['y']
                width = node['width']
                height = node['height']
                plt.plot([x, x+width, x+width, x, x], [y, y, y+height, y+height, y], 'r-')
                plt.text(x + width/2, y + height/2, node_name, fontsize=8, ha='center', va='center')
            
            # Draw movable nodes
            for node_name, node in self.movable_nodes.items():
                x = node['x']
                y = node['y']
                width = node['width']
                height = node['height']
                plt.plot([x, x+width, x+width, x, x], [y, y, y+height, y+height, y], 'b-')
                
                # Show name for large nodes
                if width * height > 100:
                    plt.text(x + width/2, y + height/2, node_name, fontsize=6, ha='center', va='center')
            
            # Set figure properties
            plt.title(f'Initial Placement Result for {self.basename}')
            plt.xlabel('X Coordinate')
            plt.ylabel('Y Coordinate')
            plt.grid(True)
            
            # Save or display figure
            if output_file:
                plt.savefig(output_file, dpi=300, bbox_inches='tight')
                plt.close()
                print(f"Visualization result saved to {output_file}")
            else:
                plt.show()
                
            return True
            
        except Exception as e:
            print(f"Error visualizing initial placement results: {e}")
            return False
    
    def print_placement_statistics(self):
        """
        Print initial placement statistics
        
        Calculate and print various statistics about the initial placement.
        """
        try:
            # Calculate placement statistics
            total_wirelength = 0
            total_overlap = 0
            out_of_bounds = 0
            
            # Calculate total wirelength
            for net in self.nets:
                pins = net['pins']
                if len(pins) <= 1:
                    continue
                    
                # Calculate half-perimeter wirelength
                min_x = float('inf')
                max_x = float('-inf')
                min_y = float('inf')
                max_y = float('-inf')
                
                for pin in pins:
                    node_name = pin['node']
                    if node_name in self.nodes:
                        node = self.nodes[node_name]
                        x = node['x'] + node['width'] / 2  # Use node center
                        y = node['y'] + node['height'] / 2
                        
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)
                
                # Half-perimeter wirelength
                wirelength = (max_x - min_x) + (max_y - min_y)
                total_wirelength += wirelength
            
            # Check nodes out of bounds
            min_x, min_y = self.core_lower_left
            max_x, max_y = self.core_upper_right
            
            for node_name, node in self.movable_nodes.items():
                x = node['x']
                y = node['y']
                width = node['width']
                height = node['height']
                
                if x < min_x or y < min_y or x + width > max_x or y + height > max_y:
                    out_of_bounds += 1
            
            # Print statistics
            print("\nInitial Placement Statistics:")
            print(f"Total nodes: {len(self.nodes)}")
            print(f"Movable nodes: {len(self.movable_nodes)}")
            print(f"Fixed nodes: {len(self.fixed_nodes)}")
            print(f"Nets: {len(self.nets)}")
            print(f"Total wirelength: {total_wirelength:.2f}")
            print(f"Nodes out of bounds: {out_of_bounds}")
            print(f"Core region: ({self.core_lower_left[0]}, {self.core_lower_left[1]}) - ({self.core_upper_right[0]}, {self.core_upper_right[1]})")
            
        except Exception as e:
            print(f"Error printing initial placement statistics: {e}")


class InitialPlacement:
    """
    Initial Placement Class
    
    This class encapsulates the entire initial placement process, including data parsing,
    quadratic solver solution, legalization, and result output.
    """
    def __init__(self, directory):
        """
        Initialize the initial placement object
        
        Parameters:
            directory (str): Directory path of BookShelf format files
        """
        self.directory = directory
        self.basename = os.path.basename(directory)
        self.parser = BookshelfParser(directory)
        
    def run(self, output_dir=None, visualize=True):
        """
        Run the initial placement algorithm
        
        Execute the complete initial placement process, including data parsing,
        quadratic solver solution, legalization, and result output.
        
        Parameters:
            output_dir (str, optional): Output directory path, if None then use input directory
            visualize (bool): Whether to visualize the results
            
        Returns:
            bool: Whether the initial placement is successful
        """
        try:
            # Set output directory
            if output_dir is None:
                output_dir = self.directory
            
            # Parse data
            print(f"Parsing BookShelf format files in {self.basename}...")
            parse_time = self.parser.parse_all()
            print(f"Data parsing completed, time: {parse_time:.4f} seconds")
            
            # Solve quadratic placement
            print("Calculating initial placement using quadratic solver...")
            start_time = time.time()
            success = self.parser.solve_quadratic_placement()
            if not success:
                print("Quadratic solver solution failed")
                return False
            qp_time = time.time() - start_time
            print(f"Quadratic solver solution completed, time: {qp_time:.4f} seconds")
            
            # Legalize initial placement
            print("Legalizing initial placement...")
            start_time = time.time()
            success = self.parser.legalize_placement()
            if not success:
                print("Initial placement legalization failed")
                return False
            legalize_time = time.time() - start_time
            print(f"Initial placement legalization completed, time: {legalize_time:.4f} seconds")
            
            # Output results
            output_pl_file = os.path.join(output_dir, f"{self.basename}_initial.pl")
            success = self.parser.write_placement_result(output_pl_file)
            if not success:
                print(f"Failed to write initial placement results to {output_pl_file}")
                return False
            print(f"Initial placement results written to {output_pl_file}")
            
            # Print statistics
            self.parser.print_placement_statistics()
            
            # Visualize results
            if visualize:
                output_img_file = os.path.join(output_dir, f"{self.basename}_initial.png")
                self.parser.visualize_placement(output_img_file)
            
            return True
            
        except Exception as e:
            print(f"Error running initial placement algorithm: {e}")
            return False


def main():
    """
    Main function, entry point of the program
    """
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Initial Placement Program")
    parser.add_argument("directory", help="Directory path of BookShelf format files")
    parser.add_argument("-o", "--output", help="Output directory path, default is input directory")
    parser.add_argument("-v", "--visualize", action="store_true", help="Whether to visualize the results")
    args = parser.parse_args()
    
    # Create initial placement object and run
    placement = InitialPlacement(args.directory)
    success = placement.run(args.output, args.visualize)
    
    if success:
        print("\nInitial placement program executed successfully!")
        return 0
    else:
        print("\nInitial placement program execution failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
