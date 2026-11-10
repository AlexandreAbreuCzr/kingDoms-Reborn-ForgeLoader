// UE4SS C++ example. Source only: not built or validated in Kingdoms Reborn.
// Build against a pinned, tested UE4SS SDK as described in README.md.
#include <Mod/CppUserModBase.hpp>
#include <DynamicOutput/DynamicOutput.hpp>

class NativeExample final : public RC::CppUserModBase {
public:
    NativeExample() {
        ModName = STR("Kingdoms native example");
        ModVersion = STR("0.1.0");
        ModDescription = STR("Native SDK entry point");
        ModAuthors = STR("Kingdoms ModKit examples");
    }
    auto on_unreal_init() -> void override {
        RC::Output::send<RC::LogLevel::Verbose>(STR("[examples.native] Unreal initialized\n"));
    }
};
extern "C" __declspec(dllexport) RC::CppUserModBase* start_mod() { return new NativeExample(); }
extern "C" __declspec(dllexport) void uninstall_mod(RC::CppUserModBase* mod) { delete mod; }
