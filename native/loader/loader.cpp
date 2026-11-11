#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "loader.hpp"
#include "json.hpp"
extern "C" {
#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
}
#include <fstream>
#include <map>
#include <set>
#include <regex>
#include <mutex>
#include <chrono>
#include <algorithm>
#include <cstdlib>
#include <cmath>
#include <cstring>

namespace forgeloader {
namespace fs=std::filesystem;
using json=nlohmann::json;
constexpr const char* GameHash="c676d4ac5533464cc2bbfefd6321c9a119d0f264069ddf265668f22d945d3df4";
constexpr size_t MemoryLimit=8*1024*1024, ScriptLimit=1024*1024;
struct Mod {
    std::string id,version,name,status,error;
    fs::path folder,entry;
    json manifest;
    lua_State* state=nullptr;
    size_t allocated=0;
    int ticks=0,lobbyTicks=0;
    int budget=0;
    std::chrono::steady_clock::time_point deadline;
    HMODULE library=nullptr;
    FLModV1 native{};
    FLHostV1* host=nullptr;
    bool failed=false;
    ~Mod(){if(state)lua_close(state);/* Native modules remain mapped until process exit. */}
};
static bool inside(const fs::path& root,const fs::path& path){
    auto a=fs::weakly_canonical(root),b=fs::weakly_canonical(path);
    auto ai=a.begin(),bi=b.begin();for(;ai!=a.end();++ai,++bi){if(bi==b.end()||_wcsicmp(ai->c_str(),bi->c_str())!=0)return false;}return true;
}
static fs::path entry_path(const fs::path& root,const std::string& entry){
    if(entry.empty()||entry.find('\\')!=entry.npos||entry.find(':')!=entry.npos)throw std::runtime_error("invalid entrypoint path");
    fs::path relative=fs::u8path(entry);
    if(relative.is_absolute())throw std::runtime_error("absolute entrypoint");
    for(auto& part:relative)if(part==L"..")throw std::runtime_error("entrypoint traversal");
    auto path=root/relative;if(!inside(root,path)||!fs::is_regular_file(path))throw std::runtime_error("entrypoint missing or outside mod");return path;
}
static std::string read_small(const fs::path& path,size_t limit){
    if(fs::file_size(path)>limit)throw std::runtime_error("file exceeds loader limit");
    std::ifstream input(path,std::ios::binary);if(!input)throw std::runtime_error("cannot read file");
    return {std::istreambuf_iterator<char>(input),{}};
}
static Mod* current(lua_State* state){return *static_cast<Mod**>(lua_getextraspace(state));}
static void* allocate(void* ud,void* ptr,size_t oldSize,size_t size){
    auto& mod=*static_cast<Mod*>(ud);if(!ptr)oldSize=0;
    if(size==0){mod.allocated-=oldSize;free(ptr);return nullptr;}
    if(size>oldSize&&size-oldSize>MemoryLimit-mod.allocated)return nullptr;
    void* result=realloc(ptr,size);if(result)mod.allocated=mod.allocated-oldSize+size;return result;
}
static void budget_hook(lua_State* state,lua_Debug*){
    auto* mod=current(state);mod->budget-=1000;
    if(mod->budget<=0||std::chrono::steady_clock::now()>mod->deadline)luaL_error(state,"mod execution budget exceeded");
}
static void begin_call(Mod& mod){mod.budget=200000;mod.deadline=std::chrono::steady_clock::now()+std::chrono::milliseconds(50);lua_sethook(mod.state,budget_hook,LUA_MASKCOUNT,1000);}
static void end_call(Mod& mod){lua_sethook(mod.state,nullptr,0,0);}
static int api_log(lua_State* state){
    auto* mod=current(state);const char* text=luaL_checkstring(state,1);
    std::string line="["+mod->id+"] "+std::string(text).substr(0,2048);mod->host->log(line.c_str());return 0;
}
static int api_title(lua_State* state){
    auto* mod=current(state);size_t size;const char* text=luaL_checklstring(state,1,&size);
    if(size==0||size>200||memchr(text,0,size))return luaL_error(state,"title must have 1..200 UTF-8 bytes");
    lua_pushboolean(state,mod->host->set_window_title(text));return 1;
}
static int api_set_fps(lua_State* state){
    auto* mod=current(state);float fps=float(luaL_checknumber(state,1));
    if(!std::isfinite(fps)||(fps!=0&&(fps<15||fps>240)))return luaL_error(state,"fps must be 0 or between 15 and 240");
    lua_pushboolean(state,mod->host->set_fps_limit(fps));return 1;
}
static int api_get_fps(lua_State* state){lua_pushnumber(state,current(state)->host->get_fps_limit());return 1;}
static int api_on(lua_State* state){
    auto* mod=current(state);const char* event=luaL_checkstring(state,1);luaL_checktype(state,2,LUA_TFUNCTION);
    int* ref=strcmp(event,"tick")==0?&mod->ticks:strcmp(event,"lobby_tick")==0?&mod->lobbyTicks:nullptr;
    if(!ref)return luaL_error(state,"supported events: tick, lobby_tick");
    if(*ref)return luaL_error(state,"one callback per event per mod");
    lua_pushvalue(state,2);*ref=luaL_ref(state,LUA_REGISTRYINDEX);return 0;
}
static void push_json(lua_State* state,const json& value,int depth=0){
    if(depth>16)throw std::runtime_error("settings nesting exceeds limit");
    if(value.is_object()){lua_newtable(state);for(auto it=value.begin();it!=value.end();++it){push_json(state,it.value(),depth+1);lua_setfield(state,-2,it.key().c_str());}}
    else if(value.is_array()){lua_newtable(state);int n=1;for(auto& item:value){push_json(state,item,depth+1);lua_rawseti(state,-2,n++);}}
    else if(value.is_boolean())lua_pushboolean(state,value.get<bool>());
    else if(value.is_number())lua_pushnumber(state,value.get<double>());
    else if(value.is_string()){auto s=value.get<std::string>();lua_pushlstring(state,s.data(),s.size());}
    else lua_pushnil(state);
}
static const char* lua_error_text(lua_State* state){const char* s=lua_tostring(state,-1);return s?s:"non-string Lua error";}
static void init_lua(Mod& mod){
    mod.state=lua_newstate(allocate,&mod);if(!mod.state)throw std::runtime_error("cannot allocate Lua state");
    *static_cast<Mod**>(lua_getextraspace(mod.state))=&mod;
    for(auto lib: {std::pair<const char*,lua_CFunction>{"_G",luaopen_base},{LUA_TABLIBNAME,luaopen_table},{LUA_STRLIBNAME,luaopen_string},{LUA_MATHLIBNAME,luaopen_math},{LUA_UTF8LIBNAME,luaopen_utf8}}){luaL_requiref(mod.state,lib.first,lib.second,1);lua_pop(mod.state,1);}
    for(const char* name:{"dofile","loadfile","load","print"}){lua_pushnil(mod.state);lua_setglobal(mod.state,name);}
    lua_newtable(mod.state);
    for(auto f:{std::pair<const char*,lua_CFunction>{"log",api_log},{"set_window_title",api_title},{"set_fps_limit",api_set_fps},{"get_fps_limit",api_get_fps},{"on",api_on}}){lua_pushcfunction(mod.state,f.second);lua_setfield(mod.state,-2,f.first);}
    lua_pushstring(mod.state,"0.2.2-KR214");lua_setfield(mod.state,-2,"version");
    push_json(mod.state,mod.manifest.value("settings",json::object()));lua_setfield(mod.state,-2,"config");lua_setglobal(mod.state,"forge");
    auto source=read_small(mod.entry,ScriptLimit);
    if(luaL_loadbufferx(mod.state,source.data(),source.size(),mod.id.c_str(),"t")!=LUA_OK)throw std::runtime_error(lua_error_text(mod.state));
    begin_call(mod);int result=lua_pcall(mod.state,0,0,0);end_call(mod);
    if(result!=LUA_OK)throw std::runtime_error(lua_error_text(mod.state));
}
struct Loader::Impl {
    fs::path mods,report;FLHostV1 host;NativeLoadHooks hooks;std::map<std::string,std::unique_ptr<Mod>> entries;
    mutable std::mutex mutex;std::string snapshot;size_t count=0;bool loaded=false;
    void fail(Mod& m,const std::string& error){m.failed=true;m.status="error";m.error=error.substr(0,2048);host.log(("["+m.id+"] ERROR: "+m.error).c_str());}
    void save(){
        json data={{"loader_version","0.2.2-KR214"},{"api_major",1},{"game_sha256",GameHash},{"mods",json::array()}};
        std::string text="ForgeLoader 0.2.0\nPasta: Mods/\n\n";size_t active=0;
        for(auto& pair:entries){auto& m=*pair.second;if(m.status=="loaded")++active;
            data["mods"].push_back({{"id",m.id},{"version",m.version},{"status",m.status},{"error",m.error}});
            text+=m.id+": "+m.status+(m.error.empty()?"":" - "+m.error)+"\n";
        }
        if(entries.empty())text+="Nenhum mod encontrado. Instale um arquivo .flmod ou copie sua pasta para Mods/.\n";
        {std::lock_guard<std::mutex> lock(mutex);snapshot=text;count=active;}
        try{fs::create_directories(report.parent_path());auto temp=report;temp+=L".tmp";std::ofstream out(temp,std::ios::binary);out<<data.dump(2);out.close();MoveFileExW(temp.c_str(),report.c_str(),MOVEFILE_REPLACE_EXISTING);}catch(...){}
    }
    bool start(const std::string& id,std::set<std::string>& visiting){
        auto& mod=*entries.at(id);if(mod.status=="loaded")return true;if(mod.failed||mod.status=="disabled")return false;
        if(!visiting.insert(id).second){fail(mod,"dependency cycle");return false;}
        for(auto it=mod.manifest["requires"].begin();it!=mod.manifest["requires"].end();++it){
            if(it.key()=="core.shared_portraits"){if(it.value()!="3.0.0"){fail(mod,"unsupported portraits dependency");return false;}continue;}
            if(it.key()=="core.loader"){if(it.value()!="0.2.1"){fail(mod,"requires ForgeLoader 0.2.2-KR214");return false;}continue;}
            auto dep=entries.find(it.key());if(dep==entries.end()||dep->second->version!=it.value()||!start(it.key(),visiting)){fail(mod,"missing, incompatible or failed dependency: "+it.key());return false;}
        }
        visiting.erase(id);
        try{
            std::string runtime=mod.manifest["runtime"];
            if(runtime=="forgeloader-lua")init_lua(mod);
            else {
                mod.library=LoadLibraryExW(mod.entry.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_SYSTEM32);
                if(!mod.library)throw std::runtime_error("native DLL could not be loaded");
                auto entry=reinterpret_cast<FLStartModV1>(GetProcAddress(mod.library,"ForgeMod_Load"));if(!entry)throw std::runtime_error("missing ForgeMod_Load export");
                struct HookScope {NativeLoadHooks hooks;bool committed=false;~HookScope(){if(hooks.finish)hooks.finish(committed);}} scope{hooks};
                if(hooks.begin)hooks.begin();
                mod.native.size=sizeof(FLModV1);mod.native.abi_version=FORGELOADER_ABI_VERSION;
                if(!entry(&host,&mod.native)||mod.native.size!=sizeof(FLModV1)||mod.native.abi_version!=FORGELOADER_ABI_VERSION||!mod.native.id||!mod.native.version||mod.id!=mod.native.id||mod.version!=mod.native.version)throw std::runtime_error("native ABI, id or version mismatch");
                scope.committed=true;
            }
            mod.status="loaded";host.log(("["+mod.id+"] LOADED "+mod.version).c_str());return true;
        }catch(const std::exception& e){fail(mod,e.what());return false;}
    }
};
Loader::Loader(fs::path mods,fs::path report,FLHostV1 host,NativeLoadHooks hooks):impl(std::make_unique<Impl>()) {impl->mods=std::move(mods);impl->report=std::move(report);impl->host=host;impl->hooks=hooks;}
Loader::~Loader()=default;
void Loader::load(){
    if(impl->loaded)return;impl->loaded=true;fs::create_directories(impl->mods);
    std::regex idPattern("^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$"),versionPattern("^[0-9]+\\.[0-9]+\\.[0-9]+$");
    std::vector<fs::path> folders;for(auto& item:fs::directory_iterator(impl->mods))if(item.is_directory())folders.push_back(item.path());std::sort(folders.begin(),folders.end());
    for(auto& folder:folders){
        if(impl->entries.size()>=128){impl->host.log("Mod limit reached (128)");break;}
        auto mod=std::make_unique<Mod>();mod->folder=folder;mod->id=folder.filename().u8string();mod->host=&impl->host;
        try{
            if(!inside(impl->mods,folder)||fs::is_symlink(folder))throw std::runtime_error("mod directory outside Mods");
            auto m=json::parse(read_small(folder/L"mod.json",65536));mod->manifest=m;
            mod->id=m.at("id").get<std::string>();mod->version=m.at("version").get<std::string>();mod->name=m.at("name").get<std::string>();
            if(!std::regex_match(mod->id,idPattern)||mod->id.rfind("core.",0)==0||!std::regex_match(mod->version,versionPattern))throw std::runtime_error("invalid mod id/version");
            if(m.at("schema")!=1||m.at("api_major")!=1)throw std::runtime_error("manifest/API major not supported");
            if(!m.value("enabled",true)){mod->status="disabled";}else{
                if(m.at("multiplayer")!="local")throw std::runtime_error("shared gameplay mods require a handshake; this runtime currently loads local mods only");
                auto builds=m.at("game_builds");if(!builds.is_array()||std::find(builds.begin(),builds.end(),GameHash)==builds.end())throw std::runtime_error("game build not supported by mod");
                auto runtime=m.at("runtime").get<std::string>();if(runtime!="forgeloader-lua"&&runtime!="forgeloader-native")throw std::runtime_error("unsupported runtime; UE4SS mods need porting to ForgeLoader API");
                if(!m.contains("requires"))mod->manifest["requires"]=json::object();
                if(!mod->manifest["requires"].is_object())throw std::runtime_error("requires must be an object");
                for(auto it=mod->manifest["requires"].begin();it!=mod->manifest["requires"].end();++it)if(!std::regex_match(it.key(),idPattern)||!it.value().is_string()||!std::regex_match(it.value().get<std::string>(),versionPattern))throw std::runtime_error("invalid dependency id/version");
                mod->entry=entry_path(folder,m.at("entrypoint"));
                if(runtime=="forgeloader-native"&&mod->entry.extension()!=L".dll")throw std::runtime_error("native entrypoint must be a DLL");
                mod->status="pending";
            }
        }catch(const std::exception& e){impl->fail(*mod,e.what());}
        if(impl->entries.count(mod->id)){impl->fail(*impl->entries.at(mod->id),"duplicate mod id");continue;}
        impl->entries[mod->id]=std::move(mod);
    }
    for(auto& pair:impl->entries){auto& mod=*pair.second;if(mod.failed||mod.status=="disabled")continue;
        try{auto conflicts=mod.manifest.value("conflicts",json::array());if(!conflicts.is_array())throw std::runtime_error("conflicts must be an array");for(auto& conflict:conflicts){std::string id=conflict;if(impl->entries.count(id)&&impl->entries.at(id)->status!="disabled"){impl->fail(mod,"conflicting mod: "+id);impl->fail(*impl->entries.at(id),"conflicting mod: "+mod.id);}}}catch(const std::exception& e){impl->fail(mod,e.what());}
    }
    for(auto& pair:impl->entries){std::set<std::string> visiting;impl->start(pair.first,visiting);}impl->save();
}
void Loader::tick(double seconds,bool lobby){
    if(!impl->loaded)return;bool changed=false;
    for(auto& pair:impl->entries){auto& mod=*pair.second;if(mod.status!="loaded")continue;
        if(mod.state){int ref=lobby?mod.lobbyTicks:mod.ticks;if(!ref)continue;lua_rawgeti(mod.state,LUA_REGISTRYINDEX,ref);lua_pushnumber(mod.state,seconds);begin_call(mod);int rc=lua_pcall(mod.state,1,0,0);end_call(mod);
            if(rc!=LUA_OK){std::string error=lua_error_text(mod.state);lua_pop(mod.state,1);impl->fail(mod,error);changed=true;}
        }else{auto callback=lobby?mod.native.on_lobby_tick:mod.native.on_tick;if(callback)callback(seconds);}
    }if(changed)impl->save();
}
std::string Loader::summary()const{std::lock_guard<std::mutex> lock(impl->mutex);return impl->snapshot;}
size_t Loader::loaded_count()const{std::lock_guard<std::mutex> lock(impl->mutex);return impl->count;}
}
