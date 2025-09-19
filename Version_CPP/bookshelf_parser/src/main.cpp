#include "BookShelfParsers.hpp"

#include <iostream>
#include <string>
#include <stdexcept>
#include <fstream>
#include <limits>
#include <algorithm>
#include <sstream>
#include <iomanip>

using namespace bs;

static void print_usage(const char* prog) {
    std::cout << "用法:\n";
    std::cout << "  " << prog << " <dir> <basename> [output_file]\n";
    std::cout << "示例:\n";
    std::cout << "  " << prog << " /home/kksk996/综合设计III参考资料-v2.0-更新版/综合设计III参考资料-v2.0-更新版/任务2参考/BookShelf格式的解析/adaptec1 adaptec1 summary.txt\n";
}

struct BBox { long long minX, minY, maxX, maxY; };

static BBox computeCoreBBox(const Scl& scl) {
    long long minX = std::numeric_limits<long long>::max();
    long long minY = std::numeric_limits<long long>::max();
    long long maxX = std::numeric_limits<long long>::min();
    long long maxY = std::numeric_limits<long long>::min();
    for (const auto& r : scl.rows) {
        minX = std::min(minX, r.subrowOrigin);
        long long rowMaxX = r.subrowOrigin + r.numSites * 1LL * std::max(1, r.siteWidth);
        maxX = std::max(maxX, rowMaxX);
        minY = std::min<long long>(minY, r.coordinate);
        maxY = std::max<long long>(maxY, r.coordinate + r.height);
    }
    if (minX == std::numeric_limits<long long>::max()) {
        minX = minY = 0; maxX = maxY = 0;
    }
    return {minX, minY, maxX, maxY};
}

static std::string format_number_ll(long long v) {
    return std::to_string(v);
}

static std::string format_number_sz(size_t v) {
    return std::to_string(v);
}

static std::string make_summary(const std::string& dir, const std::string& base, const ParsedDesign& d) {
    // counts
    const size_t numModules = d.nodes.size();
    size_t terminals = 0;
    for (const auto &kv : d.nodes) if (kv.second.terminal) ++terminals;
    const size_t numNodes = numModules - terminals;
    const size_t netCount = d.nets.size();
    size_t pinCount = 0; int maxDegree = 0;
    size_t bucket2 = 0, bucket3_10 = 0, bucket11_100 = 0, bucket100p = 0;
    for (const auto& net : d.nets) {
        int deg = static_cast<int>(net.pins.size());
        pinCount += deg;
        maxDegree = std::max(maxDegree, deg);
        if (deg == 2) ++bucket2;
        else if (deg >= 3 && deg <= 10) ++bucket3_10;
        else if (deg >= 11 && deg <= 100) ++bucket11_100;
        else if (deg > 100) ++bucket100p;
    }

    // core bbox from .scl
    BBox core = computeCoreBBox(d.scl);
    long long coreW = std::max(0LL, core.maxX - core.minX);
    long long coreH = std::max(0LL, core.maxY - core.minY);
    long long coreArea = coreW * coreH;

    // area stats
    long long movableArea = 0;
    long long fixedArea = 0;
    long long fixedInCore = 0;
    for (const auto &kv : d.nodes) {
        const Node &n = kv.second;
        long long area = 1LL * n.width * n.height;
        bool isFixed = n.terminal;
        auto itp = d.placements.find(n.name);
        if (itp != d.placements.end()) {
            if (itp->second.fixed) isFixed = true;
        }
        if (isFixed) {
            fixedArea += area;
            if (itp != d.placements.end()) {
                long long x = itp->second.x;
                long long y = itp->second.y;
                // simple in-core check using origin point
                if (x >= core.minX && x < core.maxX && y >= core.minY && y < core.maxY) fixedInCore += area;
            }
        } else {
            movableArea += area;
        }
    }
    long long cellArea = movableArea; // 与示例一致，Cell Area=Movable Area
    long long freeSitesArea = std::max(0LL, coreArea - fixedInCore);

    auto pct = [](long long num, long long den) -> double {
        if (den <= 0) return 0.0; return 100.0 * double(num) / double(den);
    };

    double placementUtil = pct(movableArea, freeSitesArea); // (=move/freeSites)
    double coreDensity = pct(movableArea + fixedInCore, coreArea); // (=usedArea/core)

    // compose summary text
    std::ostringstream oss;
    oss << "Use BOOKSHELF placement format\n";
    oss << "Reading AUX file: " << base << "/" << base << ".aux "
        << base << ".nodes " << base << ".nets " << base << ".wts " << base << ".pl " << base << ".scl\n";
    oss << "Set core region from site info: lower left: (" << core.minX << "," << core.minY << ") to upper right: (" << core.maxX << "," << core.maxY << ")\n";
    oss << "NumModules: " << format_number_sz(numModules) << "\n";
    oss << "NumNodes: " << format_number_sz(numNodes) << " (= " << (numNodes/1000) << "k)\n";
    oss << "Terminals: " << format_number_sz(terminals) << "\n";
    oss << "Nets: " << format_number_sz(netCount) << "\n";
    oss << "Pins: " << format_number_sz(pinCount) << "\n";
    oss << "Max net degree= " << maxDegree << "\n";
    oss << "Initialize module position with file: " << base << ".pl\n";
    oss << "<<<< DATABASE SUMMARIES >>>>\n";
    oss << "Core region: lower left: (" << core.minX << "," << core.minY << ") to upper right: (" << core.maxX << "," << core.maxY << ")\n";
    // 由于 site step 未显式给出，这里以 Sitewidth 为步长（常见为1）
    int rowHeight = d.scl.rows.empty() ? 0 : d.scl.rows.front().height;
    int siteStep = d.scl.rows.empty() ? 0 : std::max(1, d.scl.rows.front().siteWidth);
    oss << "Row Height/Number: " << rowHeight << " / " << d.scl.rows.size() << " (site step " << siteStep << ".000000)\n";
    oss << "Core Area: " << coreArea << " (" << std::scientific << std::uppercase << (double)coreArea << std::nouppercase << std::defaultfloat << ")\n";
    oss << "Cell Area: " << cellArea << " (" << std::scientific << std::uppercase << (double)cellArea << std::nouppercase << std::defaultfloat << ")\n";
    oss << "Movable Area: " << movableArea << " (" << std::scientific << std::uppercase << (double)movableArea << std::nouppercase << std::defaultfloat << ")\n";
    oss << "Fixed Area: " << fixedArea << " (" << std::scientific << std::uppercase << (double)fixedArea << std::nouppercase << std::defaultfloat << ")\n";
    oss << "Fixed Area in Core: " << fixedInCore << " (" << std::scientific << std::uppercase << (double)fixedInCore << std::nouppercase << std::defaultfloat << ")\n";
    oss << "Placement Util.: " << std::fixed << std::setprecision(2) << placementUtil << "% (=move/freeSites)\n";
    oss << "Core Density: " << std::fixed << std::setprecision(2) << coreDensity << "% (=usedArea/core)\n";
    oss << "Cell #: " << numNodes << " (=" << (numNodes/1000) << "k)\n";
    oss << "Object #: " << numModules << " (=" << (numModules/1000) << "k) (fixed: " << terminals << ") (macro: 0)\n";
    oss << "Net #: " << netCount << " (=" << (netCount/1000) << "k)\n";
    oss << "Max net degree=: " << maxDegree << "\n";
    oss << "Pin 2 (" << bucket2 << ") 3-10 (" << bucket3_10 << ") 11-100 (" << bucket11_100 << ") 100- (" << bucket100p << ")\n";
    oss << "Pin #: " << pinCount << "\n";
    return oss.str();
}

int main(int argc, char** argv) {
    if (argc < 3) {
        print_usage(argv[0]);
        return 1;
    }
    std::string dir = argv[1];
    std::string base = argv[2];
    std::string outPath = (argc >= 4 ? argv[3] : std::string("summary.txt"));
    try {
        ParsedDesign d = parseDesign(dir, base);
        std::string report = make_summary(dir, base, d);
        // print to stdout
        std::cout << report;
        // write to file
        std::ofstream ofs(outPath);
        if (ofs) { ofs << report; }
        else {
            std::cerr << "无法写入输出文件: " << outPath << "\n";
        }
    } catch (const std::exception &e) {
        std::cerr << "解析失败: " << e.what() << "\n";
        return 2;
    }
    return 0;
}
