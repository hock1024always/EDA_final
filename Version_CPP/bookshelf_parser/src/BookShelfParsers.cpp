#include "BookShelfParsers.hpp"

#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <cctype>

namespace bs {

namespace {

inline std::string trim(const std::string &s) {
    size_t b = 0, e = s.size();
    while (b < e && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
    while (e > b && std::isspace(static_cast<unsigned char>(s[e-1]))) --e;
    return s.substr(b, e - b);
}

inline bool starts_with(const std::string &s, const std::string &p) {
    return s.size() >= p.size() && std::equal(p.begin(), p.end(), s.begin());
}

inline std::vector<std::string> split_ws(const std::string &s) {
    std::vector<std::string> out;
    std::istringstream iss(s);
    std::string tok;
    while (iss >> tok) out.push_back(tok);
    return out;
}

inline bool safe_getline(std::ifstream &ifs, std::string &line) {
    line.clear();
    if (!std::getline(ifs, line)) return false;
    return true;
}

} // anonymous

std::unordered_map<std::string, Node> Parser::parseNodes(const std::string &filepath) {
    std::unordered_map<std::string, Node> nodes;
    std::ifstream ifs(filepath);
    if (!ifs) {
        throw std::runtime_error("Failed to open nodes file: " + filepath);
    }
    std::string line;
    // Skip header, comments
    while (safe_getline(ifs, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (starts_with(line, "UCLA")) continue;
        if (starts_with(line, "NumNodes") || starts_with(line, "NumTerminals")) continue;
        // data line: name width height [terminal]
        auto toks = split_ws(line);
        if (toks.empty()) continue;
        if (toks.size() >= 3) {
            Node n;
            n.name = toks[0];
            n.width = std::stoi(toks[1]);
            n.height = std::stoi(toks[2]);
            if (toks.size() >= 4) {
                std::string t = toks[3];
                std::transform(t.begin(), t.end(), t.begin(), [](unsigned char c){return std::tolower(c);});
                if (t.find("terminal") != std::string::npos) n.terminal = true;
            }
            nodes[n.name] = n;
        }
    }
    return nodes;
}

std::unordered_map<std::string, Placement> Parser::parsePl(const std::string &filepath) {
    std::unordered_map<std::string, Placement> pls;
    std::ifstream ifs(filepath);
    if (!ifs) {
        throw std::runtime_error("Failed to open pl file: " + filepath);
    }
    std::string line;
    while (safe_getline(ifs, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (starts_with(line, "UCLA")) continue;
        // Example: name x y : N | name x y : N  # comment | name x y : N /FIXED
        // We will split by spaces while keeping ':' as token by replacing ':' with ' : '
        for (char &c : line) { if (c == ':') c = ' '; }
        auto toks = split_ws(line);
        if (toks.size() < 4) continue;
        Placement p;
        p.name = toks[0];
        try {
            p.x = std::stoll(toks[1]);
            p.y = std::stoll(toks[2]);
        } catch (...) { continue; }
        // Find orient token (single char like N,S,E,W, or strings like FN,FS)
        // After coordinates, the next token should be orientation.
        if (toks.size() >= 4) {
            std::string o = toks[3];
            if (!o.empty()) p.orient = static_cast<char>(std::toupper(static_cast<unsigned char>(o[0])));
        }
        // Detect flags like FIXED / PLACED / UNPLACED
        for (size_t i = 4; i < toks.size(); ++i) {
            std::string t = toks[i];
            std::transform(t.begin(), t.end(), t.begin(), [](unsigned char c){return std::toupper(c);});
            if (t.find("FIXED") != std::string::npos) p.fixed = true;
        }
        pls[p.name] = p;
    }
    return pls;
}

std::vector<Net> Parser::parseNets(const std::string &filepath) {
    std::vector<Net> nets;
    std::ifstream ifs(filepath);
    if (!ifs) {
        throw std::runtime_error("Failed to open nets file: " + filepath);
    }
    std::string line;
    Net cur;
    int expectedDegree = -1;
    auto flush = [&]() {
        if (!cur.name.empty()) {
            nets.push_back(cur);
            cur = Net{};
            expectedDegree = -1;
        }
    };

    while (safe_getline(ifs, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (starts_with(line, "UCLA") || starts_with(line, "NumNets") || starts_with(line, "NumPins")) continue;
        if (starts_with(line, "NetDegree")) {
            // New net block
            // Format: NetDegree : <d> <netName>
            flush();
            for (char &c : line) { if (c == ':' ) c = ' '; }
            auto toks = split_ws(line);
            // toks: NetDegree, d, netName
            if (toks.size() >= 3) {
                try {
                    expectedDegree = std::stoi(toks[1]);
                } catch (...) { expectedDegree = -1; }
                cur.name = toks[2];
            }
            continue;
        }
        // Pin line example: "\to197239\tI : -0.500000\t-6.000000"
        // Normalize ':'
        for (char &c : line) { if (c == ':' ) c = ' '; }
        auto toks = split_ws(line);
        if (toks.size() >= 4) {
            Pin pin;
            pin.nodeName = toks[0];
            if (!pin.nodeName.empty() && (pin.nodeName[0] == 'o' || pin.nodeName[0] == 'p' || pin.nodeName[0] == 'n')) {
                // keep as is
            }
            if (!toks[1].empty()) pin.direction = static_cast<char>(std::toupper(static_cast<unsigned char>(toks[1][0])));
            try {
                pin.xOffset = std::stod(toks[2]);
                pin.yOffset = std::stod(toks[3]);
            } catch (...) {
                pin.xOffset = pin.yOffset = 0.0;
            }
            cur.pins.push_back(pin);
            if (expectedDegree > 0 && static_cast<int>(cur.pins.size()) == expectedDegree) {
                flush();
            }
        }
    }
    // flush last
    if (!cur.name.empty()) flush();
    return nets;
}

Scl Parser::parseScl(const std::string &filepath) {
    Scl scl;
    std::ifstream ifs(filepath);
    if (!ifs) {
        throw std::runtime_error("Failed to open scl file: " + filepath);
    }
    std::string line;
    RowAttr current{};
    bool inRow = false;
    while (safe_getline(ifs, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (starts_with(line, "UCLA")) continue;
        if (starts_with(line, "NumRows")) {
            // NumRows : <n>
            for (char &c : line) { if (c == ':' ) c = ' '; }
            auto toks = split_ws(line);
            if (toks.size() >= 2) {
                try { scl.numRows = std::stoi(toks[1]); } catch (...) { scl.numRows = 0; }
            }
            continue;
        }
        if (starts_with(line, "CoreRow")) {
            inRow = true;
            current = RowAttr{};
            continue;
        }
        if (starts_with(line, "End")) {
            if (inRow) {
                scl.rows.push_back(current);
                inRow = false;
            }
            continue;
        }
        // parse attributes
        if (inRow) {
            // Key : value [possibly with extra tokens]
            for (char &c : line) { if (c == ':' ) c = ' '; }
            auto toks = split_ws(line);
            if (toks.size() >= 2) {
                std::string key = toks[0];
                if (key == "Coordinate") current.coordinate = std::stoi(toks[1]);
                else if (key == "Height") current.height = std::stoi(toks[1]);
                else if (key == "Sitewidth") current.siteWidth = std::stoi(toks[1]);
                else if (key == "Sitespacing") current.siteSpacing = std::stoi(toks[1]);
                else if (key == "Siteorient") current.siteOrient = std::stoi(toks[1]);
                else if (key == "Sitesymmetry") current.siteSymmetry = std::stoi(toks[1]);
                else if (key == "SubrowOrigin") {
                    current.subrowOrigin = std::stoll(toks[1]);
                    // look for NumSites key as well
                    for (size_t i = 2; i + 1 < toks.size(); ++i) {
                        if (toks[i] == "NumSites") {
                            current.numSites = std::stoll(toks[i+1]);
                            break;
                        }
                    }
                }
            }
        }
    }
    return scl;
}

std::unordered_map<std::string, double> Parser::parseWts(const std::string &filepath) {
    std::unordered_map<std::string, double> wts;
    std::ifstream ifs(filepath);
    if (!ifs) {
        // wts is optional -> return empty
        return wts;
    }
    std::string line;
    while (safe_getline(ifs, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (starts_with(line, "UCLA")) continue;
        auto toks = split_ws(line);
        if (toks.size() >= 2) {
            try {
                wts[toks[0]] = std::stod(toks[1]);
            } catch (...) {}
        }
    }
    return wts;
}

ParsedDesign parseDesign(const std::string &dir, const std::string &basename) {
    auto join = [](const std::string &a, const std::string &b){
        if (a.empty()) return b;
        if (a.back() == '/') return a + b;
        return a + "/" + b;
    };

    ParsedDesign d;
    const std::string nodesPath = join(dir, basename + ".nodes");
    const std::string plPath    = join(dir, basename + ".pl");
    const std::string netsPath  = join(dir, basename + ".nets");
    const std::string sclPath   = join(dir, basename + ".scl");
    const std::string wtsPath   = join(dir, basename + ".wts");

    d.nodes = Parser::parseNodes(nodesPath);
    d.placements = Parser::parsePl(plPath);
    d.nets = Parser::parseNets(netsPath);
    d.scl = Parser::parseScl(sclPath);
    d.wts = Parser::parseWts(wtsPath);
    return d;
}

void printBasicReport(const ParsedDesign &d) {
    std::cout << "[BookShelf 设计解析报告]\n";
    std::cout << "节点数量(.nodes): " << d.nodes.size() << "\n";
    size_t terminals = 0;
    for (const auto &kv : d.nodes) if (kv.second.terminal) ++terminals;
    std::cout << "终端数量(terminal): " << terminals << "\n";
    std::cout << "放置记录(.pl): " << d.placements.size() << "\n";
    std::cout << "网络数量(.nets): " << d.nets.size() << "\n";
    size_t pins = 0;
    for (const auto &net : d.nets) pins += net.pins.size();
    std::cout << "引脚数量(估算): " << pins << "\n";
    std::cout << "行数(.scl NumRows): " << d.scl.numRows << ", 解析到行块: " << d.scl.rows.size() << "\n";
    std::cout << ".wts 记录数: " << d.wts.size() << "\n";

    // 简单一致性检查
    size_t missingPl = 0;
    for (const auto &kv : d.nodes) {
        if (!d.placements.count(kv.first)) ++missingPl;
    }
    std::cout << "缺失放置信息的节点: " << missingPl << "\n";

    size_t pinsOnUnknownNodes = 0;
    for (const auto &net : d.nets) {
        for (const auto &pin : net.pins) {
            if (!d.nodes.count(pin.nodeName)) ++pinsOnUnknownNodes;
        }
    }
    std::cout << "连接到未知节点的引脚: " << pinsOnUnknownNodes << "\n";
}

} // namespace bs
