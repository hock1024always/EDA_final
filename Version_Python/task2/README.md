# BookShelf格式解析工具使用说明

## 1. 简介

BookShelf格式是电子设计自动化(EDA)领域中常用的一种文件格式，用于描述集成电路的物理设计信息。本工具用于解析BookShelf格式的文件，并生成相关统计信息和报告。

## 2. BookShelf格式文件说明

BookShelf格式通常包含以下几种文件：

1. **nodes文件(.nodes)**: 描述电路中的节点（单元）信息，包括节点名称、宽度、高度等。
2. **nets文件(.nets)**: 描述电路中的网络连接关系，包括网络名称、连接的节点等。
3. **pl文件(.pl)**: 描述节点的放置位置信息，包括坐标和方向。
4. **scl文件(.scl)**: 描述布局区域的行信息，包括行的位置、高度、可用站点等。
5. **wts文件(.wts)**: 描述权重信息。
6. **aux文件(.aux)**: 描述文件之间的关联关系。

## 3. 程序功能

本程序实现了以下功能：

1. 解析nodes文件，获取节点信息
2. 解析nets文件，获取网络连接信息
3. 解析pl文件，获取节点放置位置信息
4. 解析scl文件，获取布局区域信息
5. 汇总统计信息，包括：
   - 节点总数、终端节点数、非终端节点数
   - 网络总数、引脚总数、平均网络度数、最大/最小网络度数
   - 布局区域行数、芯片尺寸、芯片面积
   - 布局密度
6. 生成报告文件

## 4. 使用方法

### 4.1 命令行使用

```bash
python bookshelf_parser.py <设计文件路径> <设计名称>
```

例如：
```bash
python bookshelf_parser.py ./adaptec1 adaptec1
```

### 4.2 作为模块导入使用

```python
from bookshelf_parser import BookshelfParser

# 创建解析器实例
parser = BookshelfParser("./adaptec1", "adaptec1")

# 解析所有文件
parser.parse_all()

# 生成报告
parser.generate_report()

# 访问解析结果
nodes_info = parser.nodes_info
nets_info = parser.nets_info
pl_info = parser.pl_info
scl_info = parser.scl_info

# 访问统计信息
stats = parser.stats
```

### 4.3 示例脚本

本工具附带了一个示例脚本`run_example.py`，演示了如何使用BookshelfParser类解析adaptec1测试数据：

```bash
python run_example.py
```

## 5. 输出说明

程序运行后会在控制台输出解析过程和统计信息，同时会在设计文件所在目录生成一个报告文件`<设计名称>_report.txt`，包含以下信息：

1. 节点统计：总节点数、终端节点数、非终端节点数
2. 网络统计：总网络数、总引脚数、平均网络度数、最大/最小网络度数
3. 布局区域统计：总行数、芯片宽度、芯片高度、芯片面积
4. 布局密度

## 6. 程序结构

程序主要包含一个`BookshelfParser`类，该类提供了以下主要方法：

- `__init__(self, base_path, design_name)`: 初始化解析器
- `parse_nodes_file(self)`: 解析nodes文件
- `parse_nets_file(self)`: 解析nets文件
- `parse_pl_file(self)`: 解析pl文件
- `parse_scl_file(self)`: 解析scl文件
- `parse_all(self)`: 解析所有文件
- `generate_report(self)`: 生成报告

## 7. 注意事项

1. 本程序假设BookShelf格式文件符合标准格式，如果文件格式有误可能导致解析错误。
2. 对于大型设计文件，解析过程可能需要较长时间，特别是nets文件通常较大。
3. 程序使用正则表达式进行文本解析，对于特殊格式的文件可能需要调整解析逻辑。

## 8. 扩展功能

本程序可以进一步扩展以支持更多功能，例如：

1. 可视化布局结果
2. 支持修改和生成BookShelf格式文件
3. 集成布局优化算法
4. 支持更多BookShelf格式的变体

## 9. 参考资料

- BookShelf格式规范文档
- 电子设计自动化(EDA)相关教材和论文
