#pragma once
#include <filesystem>
#include <memory>
#include <string>
#include "forgeloader_api.h"
namespace forgeloader {
class Loader {
public:
    Loader(std::filesystem::path mods, std::filesystem::path report, FLHostV1 host);
    ~Loader();
    void load();
    void tick(double seconds, bool lobby=false);
    std::string summary() const;
    size_t loaded_count() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl;
};
}
