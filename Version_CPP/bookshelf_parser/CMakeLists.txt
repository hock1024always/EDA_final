cmake_minimum_required(VERSION 3.12)
project(bookshelf_parser LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(bookshelf_parser
    src/main.cpp
    src/BookShelfParsers.cpp
)

target_include_directories(bookshelf_parser PRIVATE include)

# Enable more warnings
if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(bookshelf_parser PRIVATE -Wall -Wextra -Wpedantic)
endif()
