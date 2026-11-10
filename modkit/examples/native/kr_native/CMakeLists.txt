# Add this directory from a parent project that provides the UE4SS target.
cmake_minimum_required(VERSION 3.22)
project(KingdomsNativeExample LANGUAGES CXX)
add_library(KingdomsNativeExample SHARED Sources/main.cpp)
target_link_libraries(KingdomsNativeExample PRIVATE UE4SS)
target_compile_features(KingdomsNativeExample PRIVATE cxx_std_23)
