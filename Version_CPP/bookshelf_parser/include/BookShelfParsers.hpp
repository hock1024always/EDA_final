#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <optional>

namespace bs {

struct Node {
    std::string name;
    int width = 0;
    int height = 0;
    bool terminal = false; // whether this is a terminal
};

struct Placement {
    std::string name;
    long long x = 0;
    long long y = 0;
    char orient = 'N'; // N,S,E,W, FN, FS, FE, FW etc. Only first char used here
    bool fixed = false; // if placement is fixed (e.g., contains FIXED)
};

struct Pin {
    std::string nodeName;
    char direction = 'U'; // I, O, B, U
    double xOffset = 0.0;
    double yOffset = 0.0;
};

struct Net {
    std::string name;
    std::vector<Pin> pins;
};

struct RowAttr {
    int coordinate = 0;
    int height = 0;
    int siteWidth = 0;
    int siteSpacing = 0;
    int siteOrient = 0;
    int siteSymmetry = 0;
    long long subrowOrigin = 0;
    long long numSites = 0;
};

struct Scl {
    int numRows = 0;
    std::vector<RowAttr> rows;
};

struct WtsEntry {
    std::string name;
    double weight = 1.0;
};

struct ParsedDesign {
    std::unordered_map<std::string, Node> nodes; // from .nodes
    std::unordered_map<std::string, Placement> placements; // from .pl
    std::vector<Net> nets; // from .nets
    Scl scl; // from .scl
    std::unordered_map<std::string, double> wts; // optional from .wts
};

// Parsing helpers
class Parser {
public:
    static std::unordered_map<std::string, Node> parseNodes(const std::string &filepath);
    static std::unordered_map<std::string, Placement> parsePl(const std::string &filepath);
    static std::vector<Net> parseNets(const std::string &filepath);
    static Scl parseScl(const std::string &filepath);
    static std::unordered_map<std::string, double> parseWts(const std::string &filepath);
};

// Utility: read a design by supplying directory and base name (e.g., adaptec1)
ParsedDesign parseDesign(const std::string &dir, const std::string &basename);

// Basic report to stdout
void printBasicReport(const ParsedDesign &d);

} // namespace bs
