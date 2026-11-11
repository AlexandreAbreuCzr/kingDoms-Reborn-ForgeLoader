#include "loader.hpp"
#include "json.hpp"
#include <fstream>
#include <iostream>
#include <vector>
#include <stdexcept>
#include <windows.h>
namespace fs=std::filesystem;using json=nlohmann::json;
static std::vector<std::string> logs;static std::string title;static float fps=0;
static void log(const char* s){logs.push_back(s);}static int setTitle(const char* s){title=s;return 1;}static int setFPS(float f){fps=f;return 1;}static float getFPS(){return fps;}
static void check(bool value,const char* msg){if(!value)throw std::runtime_error(msg);}
static void write(const fs::path& p,const std::string& s){fs::create_directories(p.parent_path());std::ofstream(p,std::ios::binary)<<s;}
static json manifest(const std::string& id){return {{"schema",1},{"id",id},{"name",id},{"version","1.0.0"},{"api_major",1},{"runtime","forgeloader-lua"},{"multiplayer","local"},{"game_builds",{"c676d4ac5533464cc2bbfefd6321c9a119d0f264069ddf265668f22d945d3df4"}},{"requires",json::object()},{"entrypoint","Scripts/main.lua"}};}
int main(int argc,char** argv){
    fs::path root=fs::temp_directory_path()/("forge-loader-test-"+std::to_string(GetCurrentProcessId()));
    try{
        fs::create_directories(root);auto mods=root/"Mods";
        auto add=[&](const std::string& id,const std::string& source,json m=json{}){if(m.is_null())m=manifest(id);write(mods/id/"mod.json",m.dump());write(mods/id/"Scripts/main.lua",source);};
        add("test.hello","assert(io==nil and os==nil and package==nil and debug==nil and loadfile==nil); forge.set_window_title('Lua works'); forge.on('tick',function(dt) assert(dt>=0); forge.set_fps_limit(60); end)");
        add("test.infinite","while true do end");
        add("test.memory","local a=string.rep('x',16*1024*1024)");
        add("test.error","error({})");
        add("test.tick_error","forge.on('tick',function() error('tick failed') end)");
        auto m=manifest("test.required");m["multiplayer"]="required";add("test.required","error('must not execute')",m);
        m=manifest("test.traversal");m["entrypoint"]="../outside.lua";add("test.traversal","",m);
        m=manifest("test.missing");m["requires"]={{"test.absent","1.0.0"}};add("test.missing","",m);
        m=manifest("test.dependent");m["requires"]={{"test.hello","1.0.0"}};add("test.dependent","assert(forge.get_fps_limit()==0)",m);
        m=manifest("test.cycle_a");m["requires"]={{"test.cycle_b","1.0.0"}};add("test.cycle_a","",m);
        m=manifest("test.cycle_b");m["requires"]={{"test.cycle_a","1.0.0"}};add("test.cycle_b","",m);
        m=manifest("test.disabled");m["enabled"]=false;add("test.disabled","error('must not run')",m);
        m=manifest("test.oldruntime");m["runtime"]="ue4ss-lua";add("test.oldruntime","",m);
        if(argc<2)throw std::runtime_error("source root missing");
        m=manifest("forge.native_hello");m["runtime"]="forgeloader-native";m["entrypoint"]="dlls/main.dll";write(mods/"forge.native_hello"/"mod.json",m.dump());fs::create_directories(mods/"forge.native_hello"/"dlls");fs::copy_file(fs::path(argv[1])/".local/portrait-build/forge_native.dll",mods/"forge.native_hello"/"dlls/main.dll");
        FLHostV1 host{sizeof(FLHostV1),1,log,setTitle,setFPS,getFPS};
        {forgeloader::Loader loader(mods,root/"report.json",host);loader.load();check(loader.loaded_count()==4,"expected 4 loaded before tick");check(title=="Lua works","Lua entrypoint was not executed");loader.tick(.016);check(fps==60,"Lua callback did not call host API");check(loader.loaded_count()==3,"tick error was not isolated");auto report=json::parse(std::ifstream(root/"report.json"));check(report["mods"].size()==14,"incomplete report");bool nativeTick=false;for(auto& line:logs)if(line.find("native tick executed")!=line.npos)nativeTick=true;check(nativeTick,"native callback was not executed");}
        // This path is freshly created inside the system temp directory above.
        std::error_code cleanup;fs::remove_all(root,cleanup); // DLL stays mapped until process exit by design.
        std::cout<<"Loader execution tests passed: Lua, native DLL, callbacks, dependencies, limits, errors, reports\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<" (fixtures preserved at "<<root<<")\n";return 1;}
}
