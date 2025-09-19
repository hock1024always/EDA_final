# BookShelf 格式解析器（C++17 / CMake）

本项目实现对 ISPD/IBM 常见的 BookShelf 格式数据进行解析，支持 `.nodes`、`.pl`、`.nets`、`.scl`、`.wts` 五类文件，并在命令行输出基础统计与一致性检查结果。已在 `adaptec1` 示例数据上验证（仅抽样读取前缀以验证格式）。

## 功能概述

- 解析 `.nodes`：读取节点名称、宽度、高度、是否 `terminal`。
- 解析 `.pl`：读取节点的放置坐标 `(x, y)`、朝向 `orient`、是否 `FIXED`。
- 解析 `.nets`：读取网络、每个网络包含若干 pin（节点名、引脚方向、相对偏移）。
- 解析 `.scl`：读取核心行（CoreRow）信息，包括 `NumRows` 与每行属性（坐标、高度、步进、子行原点、站点数量等）。
- 解析 `.wts`：读取可选的对象权重。
- 输出基础报告：节点/终端/放置记录/网络/引脚/行块数量统计，并做简单一致性检查（`.nodes` 中有但 `.pl` 缺失的位置、`.nets` 中连接到未知节点的引脚数）。

## 使用方法

1. 构建

```bash
mkdir -p build && cd build
cmake ..
cmake --build . -j
```

2. 运行

```bash
./bookshelf_parser <数据目录> <基名>
# 示例：
./bookshelf_parser \
  /home/kksk996/综合设计III参考资料-v2.0-更新版/综合设计III参考资料-v2.0-更新版/任务2参考/BookShelf格式的解析/adaptec1 \
  adaptec1
```

程序会自动读取：
- `<目录>/<基名>.nodes`
- `<目录>/<基名>.pl`
- `<目录>/<基名>.nets`
- `<目录>/<基名>.scl`
- `<目录>/<基名>.wts`（若存在则解析）

## 输入格式简述

以下摘要来自 BookShelf 规范及示例文件（详细请参考 `BookShelf格式的解析.pdf`）：

- `.nodes`
  - 头部包含：`UCLA nodes 1.0`、`NumNodes`、`NumTerminals` 等。
  - 数据行形如：`name width height [terminal]`。

- `.pl`
  - 头部可包含：`UCLA pl 1.0`。
  - 数据行形如：`name x y : Orient [FIXED|PLACED|UNPLACED]`，`Orient` 为 `N/S/E/W/...`。

- `.nets`
  - 头部包含：`UCLA nets 1.0`、`NumNets`、`NumPins`。
  - 每个网络以 `NetDegree : <d> <netName>` 开始，随后 `d` 行 pin：`nodeName <I|O|B|U> : xOffset yOffset`。

- `.scl`
  - 头部包含：`UCLA scl 1.0`、`NumRows : N`。
  - 每个 `CoreRow ... End` 块内含多行属性：`Coordinate/Height/Sitewidth/Sitespacing/Siteorient/Sitesymmetry/SubrowOrigin/NumSites` 等。

- `.wts`
  - 头部可包含：`UCLA wts 1.0`。
  - 数据行通常为：`name weight`（可选）。

注：以上文件普遍允许以 `#` 开头的注释，解析器会自动忽略空行与注释行。

## 代码结构

- `include/BookShelfParsers.hpp`
  - 定义了核心数据结构：`Node`、`Placement`、`Pin`、`Net`、`RowAttr`、`Scl`、`ParsedDesign`。
  - 声明解析入口：`Parser::parseNodes/parsePl/parseNets/parseScl/parseWts`，以及组合方法 `parseDesign(dir, base)`。
  - 提供 `printBasicReport` 用于输出统计与检查结果。

- `src/BookShelfParsers.cpp`
  - 实现上述解析逻辑。采用逐行读取，支持大文件，尽量容错并忽略无关字段。

- `src/main.cpp`
  - 简单命令行入口，调用 `parseDesign` 并输出报告。

- `CMakeLists.txt`
  - 标准 CMake 构建配置，C++17，启用常见编译警告。

## 设计与实现说明

- 解析器使用文本行扫描与宽字符分割，不依赖外部库，便于在受限环境编译。
- `.nets` 解析支持按 `NetDegree` 计数边界，读满后立即刷新网络，减少内存峰值。
- `.pl` 的 `Orient` 仅记录首字符（如 `N`），若需要完整八向（N,S,E,W, FN,FS,FE,FW），可在结构体中扩展为字符串。
- `.wts` 文件在示例中可能为空，仅作可选解析，不影响整体流程。
- 一致性检查面向常见错误：
  - `.nodes` 中存在、`.pl` 未给出坐标的节点数量；
  - `.nets` 中 pin 指向未知节点的数量（有些数据集的网络端点可能不是标准单元名，属于原始数据特性）。

## 可能的扩展

- 导出为自定义二进制或 JSON 以便下游工具消费。
- 增加几何合法性校验（超出边界、重叠检测）。
- 支持多线程解析极大文件（当前单线程已可应对百万行量级）。
- 增加命令行参数以选择只解析某些文件并输出摘要。

## 许可证

此示例解析器以学习用途为主，可自由修改与扩展。
