#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <commdlg.h>
#include <objidl.h>
#include <gdiplus.h>
#include <wincrypt.h>
#include <string>
#include <vector>
#include <mutex>
#include <atomic>
#include <map>
#include <memory>
#include <algorithm>
#include <cstring>
#include "MinHook.h"
#include "protocol.hpp"
#include "panel_state.hpp"
#pragma comment(lib,"gdiplus.lib")
#pragma comment(lib,"comdlg32.lib")
#pragma comment(lib,"ole32.lib")
#pragma comment(lib,"advapi32.lib")

namespace {
using Bytes=std::vector<uint8_t>;
struct FString {wchar_t* data;int num,max;};
struct Info {alignas(8) uint8_t bytes[96];FString& portrait(){return *reinterpret_cast<FString*>(bytes+72);}};
struct Weak {int index=-1,serial=0;};
struct ByteArray {const uint8_t* data;int num,max;};
static_assert(sizeof(FString)==16 && sizeof(Info)==96 && sizeof(Weak)==8);
uintptr_t base=0;HWND gameWindow=nullptr;std::atomic<ULONGLONG> lastLobby{0};
std::atomic<bool> settingsOpen{false};bool choosingFile=false;
std::mutex pendingMutex;Bytes pendingJpeg;int pendingAction=0;std::wstring lastFallback;
void log(const char* text){
    wchar_t path[MAX_PATH];if(!GetEnvironmentVariableW(L"LOCALAPPDATA",path,MAX_PATH))return;
    std::wstring dir=std::wstring(path)+L"\\PunCity\\Saved\\PortraitMod";CreateDirectoryW(dir.c_str(),nullptr);
    std::wstring name=dir+L"\\runtime.log";
    HANDLE h=CreateFileW(name.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE)return;LARGE_INTEGER size{};GetFileSizeEx(h,&size);
    if(size.QuadPart<262144){DWORD written;WriteFile(h,text,DWORD(strlen(text)),&written,nullptr);WriteFile(h,"\r\n",2,&written,nullptr);}CloseHandle(h);
}
template<class T>T api(uintptr_t rva){return reinterpret_cast<T>(base+rva);}
using UI=void(__fastcall*)(void*,const Info*,void*,const void*,const void*);
using Lobby=void(__fastcall*)(void*,void*,int,const void*);
using Getter=Info*(__fastcall*)(void*,Info*,int);
using Setter=void(__fastcall*)(void*,uint64_t,void*);
using Tick=void(__fastcall*)(void*);
UI originalUI=nullptr;Lobby originalLobby=nullptr;Getter originalGet=nullptr;Setter originalSet=nullptr;
Tick originalTick=nullptr;
struct Context {krphoto::Photo photo;int playerId=-1;bool lobby=false;};
thread_local Context* context=nullptr;
struct Scope {Context* before;Scope(Context* now):before(context){context=now;}~Scope(){context=before;}};
std::wstring read(const FString& s){if(!s.data||s.num<1||s.num>int(krphoto::MaxToken+1)||s.max<s.num)return {};return std::wstring(s.data,s.num-1);}
void assign(FString& dest,const std::wstring& text){
    int count=int(text.size()+1);if(dest.max<count){dest.data=static_cast<wchar_t*>(api<void*(__fastcall*)(void*,size_t,uint32_t)>(0x2a0d480)(dest.data,size_t(count)*2,0));dest.max=count;}
    memcpy(dest.data,text.c_str(),size_t(count)*2);dest.num=count;
}
void normalize(Info* info,const krphoto::Photo& photo){
    auto& s=info->portrait();const auto& fallback=photo.fallback.empty()?lastFallback:photo.fallback;
    if(s.data&&s.max>int(fallback.size())){memcpy(s.data,fallback.c_str(),(fallback.size()+1)*2);s.num=int(fallback.size()+1);}
}
bool mainController(void* p){
    if(!p)return false;void* wanted=api<void*(__fastcall*)()>(0x295c6a0)();
    void* cls=*reinterpret_cast<void**>(static_cast<uint8_t*>(p)+16);
    for(int i=0;cls&&i<32;++i){if(cls==wanted)return true;cls=*reinterpret_cast<void**>(static_cast<uint8_t*>(cls)+64);}return false;
}
void publish(void* widget){
    int action;Bytes image;
    {std::lock_guard<std::mutex> lock(pendingMutex);action=pendingAction;if(!action)return;image=pendingJpeg;}
    void* controller=api<void*(__fastcall*)(const void*,int)>(0x3f82d20)(widget,0);
    if(!mainController(controller))return;
    int id=*reinterpret_cast<int*>(static_cast<uint8_t*>(controller)+0x5b0);if(id<0||id>63)return;
    {std::lock_guard<std::mutex> lock(pendingMutex);if(pendingAction!=action)return;pendingAction=0;pendingJpeg.clear();}
    // Native leader settings own this preview. Updating only GameInstance left
    // the old preview on screen and Finalizado would send the old portrait back.
    Info* info=reinterpret_cast<Info*>(static_cast<uint8_t*>(widget)+0x4a0);
    try{
        std::wstring current=read(info->portrait());auto old=krphoto::decode(current);
        std::wstring fallback=old.marked?old.fallback:current;if(!krphoto::valid_name(fallback))throw std::runtime_error("missing fallback");
        std::wstring token=action==2?fallback:krphoto::encode(fallback,image);
        assign(info->portrait(),token);
        api<void(__fastcall*)(void*)>(0x28c9f00)(widget);
        api<void(__fastcall*)(void*,const Info*)>(0x295ffc0)(controller,info);
        log(action==2?"Portrait restore requested through game RPC":"Photo submitted through game RPC");
    }catch(...){log("Photo submission refused: invalid local portrait or allocation failure");}
}
bool dimensions(const Bytes& jpeg){
    if(jpeg.empty()||jpeg.size()>krphoto::MaxJpeg)return false;
    IStream* stream=nullptr;if(FAILED(CreateStreamOnHGlobal(nullptr,TRUE,&stream)))return false;
    ULONG written;stream->Write(jpeg.data(),ULONG(jpeg.size()),&written);LARGE_INTEGER z{};stream->Seek(z,STREAM_SEEK_SET,nullptr);
    bool valid=false;{Gdiplus::Bitmap bitmap(stream);valid=bitmap.GetLastStatus()==Gdiplus::Ok&&bitmap.GetWidth()==128&&bitmap.GetHeight()==128;}stream->Release();return valid;
}
void* texture(const krphoto::Photo& photo){
    if(!photo.valid)return nullptr;
    struct Entry {Weak weak;ULONGLONG accessed;};static std::map<std::string,Entry> cache;
    std::string key=krphoto::base64(photo.jpeg);auto it=cache.find(key);
    if(it!=cache.end()){it->second.accessed=GetTickCount64();if(auto* obj=api<void*(__fastcall*)(const Weak*)>(0x2cc1c90)(&it->second.weak))return obj;}
    if(!dimensions(photo.jpeg))return nullptr;
    ByteArray buffer{photo.jpeg.data(),int(photo.jpeg.size()),int(photo.jpeg.size())};
    void* result=api<void*(__fastcall*)(const ByteArray*)>(0x3ff17e0)(&buffer);if(!result)return nullptr;
    if(cache.size()>=64){auto oldest=std::min_element(cache.begin(),cache.end(),[](auto& a,auto& b){return a.second.accessed<b.second.accessed;});cache.erase(oldest);}
    Entry entry{};api<void(__fastcall*)(Weak*,const void*)>(0x2cbf950)(&entry.weak,result);entry.accessed=GetTickCount64();cache[key]=entry;
    log("Photo texture decoded for a player");return result;
}
void __fastcall hookedSet(void* material,uint64_t name,void* value){
    if(context&&context->photo.valid){
        static uint64_t character=0;if(!character)api<void*(__fastcall*)(uint64_t*,const char*,int)>(0x2adf640)(&character,"Character",1);
        if(name==character){if(auto* custom=texture(context->photo))value=custom;}
    }
    originalSet(material,name,value);
}
void __fastcall hookedUI(void* self,const Info* info,void* faction,const void* logos,const void* portraits){
    static bool observed=false;if(!observed){observed=true;log("Player portrait UI reached");}
    Context local;auto value=read(const_cast<Info*>(info)->portrait());local.photo=krphoto::decode(value);
    if(!local.photo.marked&&context&&context->lobby&&context->photo.valid)local.photo=context->photo;
    if(!local.photo.marked&&krphoto::valid_name(value))lastFallback=value;
    Scope scope(&local);
    if(local.photo.marked){Info copy=*info;std::wstring fallback=local.photo.fallback.empty()?lastFallback:local.photo.fallback;
        FString borrowed{fallback.data(),int(fallback.size()+1),int(fallback.size()+1)};copy.portrait()=borrowed;originalUI(self,&copy,faction,logos,portraits);
    }else originalUI(self,info,faction,logos,portraits);
}
Info* __fastcall hookedGet(void* self,Info* output,int id){
    Info* result=originalGet(self,output,id);
    if(context&&context->lobby){auto value=read(result->portrait());auto photo=krphoto::decode(value);
        if(photo.marked){if(id==context->playerId)context->photo=photo;normalize(result,photo);}
        else if(krphoto::valid_name(value))lastFallback=value;
    }return result;
}
void __fastcall hookedLobby(void* self,void* element,int id,const void* save){
    static bool observed=false;if(!observed){observed=true;log("Lobby portrait UI reached");}
    Context local;local.lobby=true;local.playerId=id;Scope scope(&local);originalLobby(self,element,id,save);
}
void __fastcall hookedTick(void* self){
    originalTick(self);
    // PDB: ULobbyUI::LobbyChooseLogoOverlay +0x3c0, UWidget::Visibility +0xc3.
    auto* overlay=*reinterpret_cast<uint8_t**>(static_cast<uint8_t*>(self)+0x3c0);
    bool open=overlay&&krphoto::settings_visible(overlay[0xc3]);
    bool previous=settingsOpen.exchange(open);lastLobby.store(GetTickCount64());
    if(open&&!previous)log("Leader settings opened; photo panel requested");
    if(!open&&previous)log("Leader settings closed; photo panel hidden");
    if(open)publish(self);
}
bool jpegEncoder(CLSID& id){UINT count=0,size=0;Gdiplus::GetImageEncodersSize(&count,&size);Bytes storage(size);auto* codecs=reinterpret_cast<Gdiplus::ImageCodecInfo*>(storage.data());
    if(Gdiplus::GetImageEncoders(count,size,codecs)!=Gdiplus::Ok)return false;
    for(UINT i=0;i<count;++i)if(wcscmp(codecs[i].MimeType,L"image/jpeg")==0){id=codecs[i].Clsid;return true;}return false;
}
Bytes convert(const wchar_t* filename){
    WIN32_FILE_ATTRIBUTE_DATA file{};if(!GetFileAttributesExW(filename,GetFileExInfoStandard,&file)||file.nFileSizeHigh||file.nFileSizeLow>20*1024*1024)throw std::runtime_error("file size");
    Gdiplus::Bitmap source(filename);UINT w=source.GetWidth(),h=source.GetHeight();if(source.GetLastStatus()!=Gdiplus::Ok||!w||!h||w>8192||h>8192)throw std::runtime_error("invalid image");
    Gdiplus::Bitmap normalized(128,128,PixelFormat24bppRGB);Gdiplus::Graphics graphics(&normalized);graphics.Clear(Gdiplus::Color(0xffffffffu));graphics.SetInterpolationMode(Gdiplus::InterpolationModeHighQualityBicubic);
    UINT side=std::min(w,h);graphics.DrawImage(&source,Gdiplus::Rect(0,0,128,128),INT((w-side)/2),INT((h-side)/2),INT(side),INT(side),Gdiplus::UnitPixel);
    CLSID encoder;if(!jpegEncoder(encoder))throw std::runtime_error("JPEG codec missing");
    for(ULONG quality:{80UL,60UL,40UL,20UL}){
        IStream* stream=nullptr;if(FAILED(CreateStreamOnHGlobal(nullptr,TRUE,&stream)))throw std::runtime_error("stream");
        Gdiplus::EncoderParameters settings{};settings.Count=1;settings.Parameter[0].Guid=Gdiplus::EncoderQuality;settings.Parameter[0].Type=Gdiplus::EncoderParameterValueTypeLong;settings.Parameter[0].NumberOfValues=1;settings.Parameter[0].Value=&quality;
        auto status=normalized.Save(stream,&encoder,&settings);STATSTG stat{};stream->Stat(&stat,STATFLAG_NONAME);Bytes out;
        if(status==Gdiplus::Ok&&stat.cbSize.QuadPart<=krphoto::MaxJpeg){out.resize(size_t(stat.cbSize.QuadPart));LARGE_INTEGER z{};stream->Seek(z,STREAM_SEEK_SET,nullptr);ULONG read;stream->Read(out.data(),ULONG(out.size()),&read);}
        stream->Release();if(!out.empty())return out;
    }throw std::runtime_error("image too large");
}
LRESULT CALLBACK panelProc(HWND panel,UINT msg,WPARAM wp,LPARAM lp){
    if(msg==WM_COMMAND){
        if(LOWORD(wp)==2){std::lock_guard<std::mutex> lock(pendingMutex);pendingAction=2;return 0;}
        if(LOWORD(wp)==1){choosingFile=true;ShowWindow(panel,SW_HIDE);wchar_t file[32768]{};OPENFILENAMEW ofn{};ofn.lStructSize=sizeof(ofn);ofn.hwndOwner=gameWindow;ofn.lpstrFilter=L"Fotos PNG e JPG\0*.png;*.jpg;*.jpeg\0\0";ofn.lpstrFile=file;ofn.nMaxFile=32768;ofn.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
            if(GetOpenFileNameW(&ofn))try{Bytes jpeg=convert(file);
                if(MessageBoxW(gameWindow,L"Usar esta foto como retrato e envia-la aos participantes desta partida?\nTodos precisam instalar esta mesma versao do mod.",L"Foto do jogador",MB_OKCANCEL|MB_ICONQUESTION)==IDOK){std::lock_guard<std::mutex> lock(pendingMutex);pendingJpeg=std::move(jpeg);pendingAction=1;}
            }catch(...){MessageBoxW(gameWindow,L"Nao foi possivel importar. Use PNG/JPG de ate 20 MB e 8192 pixels por lado.",L"Importar foto",MB_OK|MB_ICONERROR);}choosingFile=false;SetForegroundWindow(gameWindow);return 0;
        }
    }
    if(msg==WM_MOUSEACTIVATE)return MA_NOACTIVATE;
    if(msg==WM_TIMER){
        RECT rect{};POINT origin{};HWND foreground=GetForegroundWindow();
        bool foregroundOwned=foreground&&(foreground==gameWindow||GetAncestor(foreground,GA_ROOTOWNER)==gameWindow);
        bool show=krphoto::panel_visible(GetTickCount64(),lastLobby.load(),settingsOpen.load(),
                  IsWindowVisible(gameWindow)&&!IsIconic(gameWindow),foregroundOwned,choosingFile);
        if(GetClientRect(gameWindow,&rect)&&ClientToScreen(gameWindow,&origin))
            SetWindowPos(panel,HWND_TOP,origin.x+16,origin.y+std::max(16L,rect.bottom-88),350,66,SWP_NOACTIVATE);
        if(show!=bool(IsWindowVisible(panel))){ShowWindow(panel,show?SW_SHOWNOACTIVATE:SW_HIDE);log(show?"Photo panel shown":"Photo panel hidden");}
        return 0;
    }
    return DefWindowProcW(panel,msg,wp,lp);
}
BOOL CALLBACK findWindow(HWND w,LPARAM){DWORD pid=0;GetWindowThreadProcessId(w,&pid);RECT r{};GetClientRect(w,&r);if(pid==GetCurrentProcessId()&&IsWindowVisible(w)&&r.right>640&&r.bottom>400){gameWindow=w;return FALSE;}return TRUE;}
bool matchingExecutable(){
    auto* dos=reinterpret_cast<IMAGE_DOS_HEADER*>(base);
    if(dos->e_magic!=IMAGE_DOS_SIGNATURE)return false;
    auto* nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(base+dos->e_lfanew);
    if(nt->Signature!=IMAGE_NT_SIGNATURE||nt->FileHeader.TimeDateStamp!=0x698c804c||nt->OptionalHeader.SizeOfImage!=0x16cc7000)return false;
    wchar_t path[32768];if(!GetModuleFileNameW(nullptr,path,32768))return false;
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return false;
    HCRYPTPROV provider=0;HCRYPTHASH hash=0;bool valid=false;
    if(CryptAcquireContextW(&provider,nullptr,nullptr,PROV_RSA_AES,CRYPT_VERIFYCONTEXT)&&CryptCreateHash(provider,CALG_SHA_256,0,0,&hash)){
        uint8_t block[65536];DWORD count=0;bool ok=true;
        for(;;){if(!ReadFile(file,block,sizeof(block),&count,nullptr)){ok=false;break;}if(!count)break;if(!CryptHashData(hash,block,count,0)){ok=false;break;}}
        uint8_t digest[32];DWORD size=32;if(ok&&CryptGetHashParam(hash,HP_HASHVAL,digest,&size,0)){
            static const uint8_t expected[32]={0xa5,0xd2,0x38,0x56,0x60,0xd9,0xe8,0x19,0xd2,0xaa,0x07,0x3c,0xdd,0x9c,0x1d,0x74,0xc0,0x51,0x49,0xc9,0x61,0x7f,0x37,0xcb,0xb8,0xb3,0x1e,0x83,0x70,0x8c,0x4e,0x24};
            valid=size==32&&memcmp(digest,expected,32)==0;
        }
    }
    if(hash)CryptDestroyHash(hash);if(provider)CryptReleaseContext(provider,0);CloseHandle(file);return valid;
}
DWORD WINAPI run(void*){
    base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    if(!matchingExecutable()){log("Unsupported executable; hooks refused");return 1;}
    Gdiplus::GdiplusStartupInput input;ULONG_PTR gdip=0;if(Gdiplus::GdiplusStartup(&gdip,&input,nullptr)!=Gdiplus::Ok)return 1;
    if(MH_Initialize()!=MH_OK)return 1;
    if(MH_CreateHook(reinterpret_cast<void*>(base+0x27b11a0),reinterpret_cast<void*>(hookedUI),reinterpret_cast<void**>(&originalUI))!=MH_OK||
       MH_CreateHook(reinterpret_cast<void*>(base+0x28c8200),reinterpret_cast<void*>(hookedLobby),reinterpret_cast<void**>(&originalLobby))!=MH_OK||
       MH_CreateHook(reinterpret_cast<void*>(base+0x288f2c0),reinterpret_cast<void*>(hookedGet),reinterpret_cast<void**>(&originalGet))!=MH_OK||
       MH_CreateHook(reinterpret_cast<void*>(base+0x28bd8f0),reinterpret_cast<void*>(hookedTick),reinterpret_cast<void**>(&originalTick))!=MH_OK||
       MH_CreateHook(reinterpret_cast<void*>(base+0x408c7d0),reinterpret_cast<void*>(hookedSet),reinterpret_cast<void**>(&originalSet))!=MH_OK||MH_EnableHook(MH_ALL_HOOKS)!=MH_OK){MH_DisableHook(MH_ALL_HOOKS);MH_Uninitialize();log("Hook installation failed; hooks removed");return 1;}
    log("Portrait runtime v3 initialized; original D3D policy; leader settings panel");
    while(!gameWindow){EnumWindows(findWindow,0);Sleep(250);}
    HINSTANCE instance=GetModuleHandleW(L"KingdomsPortraits.dll");WNDCLASSW cls{};cls.lpfnWndProc=panelProc;cls.hInstance=instance;cls.lpszClassName=L"KRPortraitPanel1";cls.hbrBackground=reinterpret_cast<HBRUSH>(COLOR_BTNFACE+1);RegisterClassW(&cls);
    // Owned popup is composed above the DirectX surface. A GDI child HWND can
    // be covered by the game's swap chain. No topmost flag or separate process.
    HWND panel=CreateWindowExW(WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,cls.lpszClassName,L"Fotos do lider",WS_POPUP|WS_BORDER,16,16,350,66,gameWindow,nullptr,instance,nullptr);
    if(!panel){log("Photo panel creation failed");return 1;}log("Owned photo panel created for game window");
    CreateWindowExW(0,L"BUTTON",L"Importar foto",WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,6,5,160,30,panel,reinterpret_cast<HMENU>(1),instance,nullptr);
    CreateWindowExW(0,L"BUTTON",L"Remover foto",WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,174,5,166,30,panel,reinterpret_cast<HMENU>(2),instance,nullptr);
    CreateWindowExW(0,L"STATIC",L"Retrato compartilhado - todos precisam do mod",WS_VISIBLE|WS_CHILD,6,40,338,20,panel,nullptr,instance,nullptr);
    SetTimer(panel,1,250,nullptr);MSG message{};while(GetMessageW(&message,nullptr,0,0)>0){TranslateMessage(&message);DispatchMessageW(&message);}return 0;
}
}
extern "C" __declspec(dllexport) void KingdomsPortraitsMarker(){}
BOOL APIENTRY DllMain(HMODULE module,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(module);HANDLE thread=CreateThread(nullptr,0,run,nullptr,0,nullptr);if(thread)CloseHandle(thread);}return TRUE;}
