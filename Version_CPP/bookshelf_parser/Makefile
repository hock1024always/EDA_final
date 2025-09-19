CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
INCLUDES := -Iinclude
SRC := src/BookShelfParsers.cpp src/main.cpp
BIN := bookshelf_parser

all: $(BIN)

$(BIN): $(SRC)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(SRC) -o $(BIN)

clean:
	rm -f $(BIN)

.PHONY: all clean
