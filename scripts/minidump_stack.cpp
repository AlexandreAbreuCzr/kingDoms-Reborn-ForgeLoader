// Offline stack unwinding from captured memory and local images/PDBs only.
#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dbghelp.h>
#include <d3d11.h>
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <cstring>
#pragma comment(lib,"dbghelp.lib")
namespace fs=std::filesystem;
struct Range{ULONG64 address;const unsigned char* bytes;size_t size;};
struct Image{ULONG64 address;std::vector<unsigned char> bytes;};
std::vector<Range> ranges;std::vector<Image> images;
std::vector<unsigned char> load(const fs::path& p){std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
PVOID CALLBACK functionTable(HANDLE,DWORD64 address){
    for(auto& image:images){auto& b=image.bytes;if(b.size()<64)continue;auto* dos=reinterpret_cast<IMAGE_DOS_HEADER*>(b.data());
        if(dos->e_lfanew<0||size_t(dos->e_lfanew)+sizeof(IMAGE_NT_HEADERS64)>b.size())continue;
        auto* nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(b.data()+dos->e_lfanew);if(address<image.address||address-image.address>=nt->OptionalHeader.SizeOfImage)continue;
        auto dir=nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION];auto* sec=IMAGE_FIRST_SECTION(nt);auto pc=address-image.address;
        for(unsigned i=0;i<nt->FileHeader.NumberOfSections;++i)if(dir.VirtualAddress>=sec[i].VirtualAddress&&dir.VirtualAddress-sec[i].VirtualAddress+dir.Size<=sec[i].SizeOfRawData){
            auto off=sec[i].PointerToRawData+dir.VirtualAddress-sec[i].VirtualAddress;if(size_t(off)+dir.Size>b.size())return nullptr;
            auto* f=reinterpret_cast<RUNTIME_FUNCTION*>(b.data()+off);size_t low=0,high=dir.Size/sizeof(*f);
            while(low<high){auto mid=(low+high)/2;if(pc<f[mid].BeginAddress)high=mid;else if(pc>=f[mid].EndAddress)low=mid+1;else return &f[mid];}
        }return nullptr;
    }return nullptr;
}
BOOL CALLBACK readMemory(HANDLE,DWORD64 address,PVOID out,DWORD size,LPDWORD actual){
    *actual=0;
    for(auto& r:ranges)if(address>=r.address&&address-r.address<r.size){auto n=std::min<size_t>(size,r.size-size_t(address-r.address));memcpy(out,r.bytes+(address-r.address),n);*actual=DWORD(n);return TRUE;}
    for(auto& image:images){auto& b=image.bytes;if(b.size()<sizeof(IMAGE_DOS_HEADER))continue;
        auto* dos=reinterpret_cast<IMAGE_DOS_HEADER*>(b.data());if(dos->e_magic!=IMAGE_DOS_SIGNATURE||dos->e_lfanew<0||size_t(dos->e_lfanew)+sizeof(IMAGE_NT_HEADERS64)>b.size())continue;
        auto* nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(b.data()+dos->e_lfanew);if(address<image.address||address-image.address>=nt->OptionalHeader.SizeOfImage)continue;
        auto rva=address-image.address;
        if(rva<nt->OptionalHeader.SizeOfHeaders&&rva+size<=b.size()){memcpy(out,b.data()+rva,size);*actual=size;return TRUE;}
        auto* sec=IMAGE_FIRST_SECTION(nt);
        for(unsigned i=0;i<nt->FileHeader.NumberOfSections;++i)if(rva>=sec[i].VirtualAddress&&rva-sec[i].VirtualAddress+size<=sec[i].SizeOfRawData){
            auto at=sec[i].PointerToRawData+rva-sec[i].VirtualAddress;if(at+size<=b.size()){memcpy(out,b.data()+at,size);*actual=size;return TRUE;}
        }
    }return FALSE;
}
void frame(HANDLE process,DWORD64 address){
    char buffer[sizeof(SYMBOL_INFO)+4096]{};auto* symbol=reinterpret_cast<SYMBOL_INFO*>(buffer);symbol->SizeOfStruct=sizeof(SYMBOL_INFO);symbol->MaxNameLen=4095;DWORD64 delta=0;
    IMAGEHLP_MODULE64 mod{};mod.SizeOfStruct=sizeof(mod);
    std::cout<<"  0x"<<std::hex<<address<<" ";
    if(SymGetModuleInfo64(process,address,&mod))std::cout<<mod.ModuleName<<"+0x"<<address-mod.BaseOfImage<<" ";
    if(SymFromAddr(process,address,&delta,symbol))std::cout<<symbol->Name<<"+0x"<<delta;
    std::cout<<std::dec<<"\n";
}
void textureDetails(HANDLE process,const CONTEXT& ctx,DWORD64 address){
    auto base=SymGetModuleBase64(process,address);if(!base)return;auto rva=address-base;
    if(rva==0x2f535d8)std::cout<<"  CAPTURED CreateTexture2D HRESULT=0x"<<std::hex<<DWORD(ctx.Rsi)<<std::dec<<"\n";
    if(rva==0x2f517f3){D3D11_TEXTURE2D_DESC desc{};DWORD got=0;
        if(readMemory(process,ctx.Rdi,&desc,sizeof(desc),&got)&&got==sizeof(desc))
            std::cout<<"  CAPTURED TEXTURE "<<desc.Width<<"x"<<desc.Height<<" mips="<<desc.MipLevels<<" array="<<desc.ArraySize<<" format="<<desc.Format<<" samples="<<desc.SampleDesc.Count<<" usage="<<desc.Usage<<" bind="<<desc.BindFlags<<" cpu="<<desc.CPUAccessFlags<<" misc="<<desc.MiscFlags<<"\n";
    }
}
int wmain(int argc,wchar_t** argv){
    if(argc!=3){std::cerr<<"Usage: minidump_stack dump.dmp local-game-exe\n";return 2;}
    auto dump=load(argv[1]);if(dump.size()<sizeof(MINIDUMP_HEADER))return 3;
    auto* header=reinterpret_cast<MINIDUMP_HEADER*>(dump.data());if(header->Signature!=MINIDUMP_SIGNATURE)return 4;
    auto valid=[&](ULONG64 rva,ULONG64 size){return rva<=dump.size()&&size<=dump.size()-rva;};
    auto stream=[&](ULONG type)->void*{PMINIDUMP_DIRECTORY directory=nullptr;void* result=nullptr;ULONG size=0;
        if(!MiniDumpReadDumpStream(dump.data(),type,&directory,&result,&size)||!valid(directory->Location.Rva,size))return nullptr;return result;};
    auto* modules=static_cast<MINIDUMP_MODULE_LIST*>(stream(ModuleListStream));
    auto* threads=static_cast<MINIDUMP_THREAD_LIST*>(stream(ThreadListStream));
    auto* error=static_cast<MINIDUMP_EXCEPTION_STREAM*>(stream(ExceptionStream));if(!modules||!threads)return 5;
    HANDLE process=GetCurrentProcess();SymSetOptions(SYMOPT_UNDNAME|SYMOPT_EXACT_SYMBOLS|SYMOPT_FAIL_CRITICAL_ERRORS|SYMOPT_DEFERRED_LOADS);
    fs::path game=fs::absolute(argv[2]);if(!SymInitializeW(process,game.parent_path().c_str(),FALSE))return 6;
    for(ULONG i=0;i<modules->NumberOfModules;++i){auto& m=modules->Modules[i];if(!valid(m.ModuleNameRva,4))continue;
        auto length=*reinterpret_cast<ULONG*>(dump.data()+m.ModuleNameRva);if(!valid(m.ModuleNameRva+4,length))continue;
        fs::path path(std::wstring(reinterpret_cast<wchar_t*>(dump.data()+m.ModuleNameRva+4),length/2));
        if(path.filename().wstring().find(L"PrototypeCity")!=std::wstring::npos)path=game;
        if(fs::exists(path)){
            auto loaded=SymLoadModuleExW(process,nullptr,path.c_str(),nullptr,m.BaseOfImage,m.SizeOfImage,nullptr,0);
            if(loaded)images.push_back({m.BaseOfImage,load(path)});
        }
        std::wcout<<L"MODULE "<<path.filename().wstring()<<L" base=0x"<<std::hex<<m.BaseOfImage<<std::dec<<L"\n";
    }
    if(auto* memory=static_cast<MINIDUMP_MEMORY_LIST*>(stream(MemoryListStream)))for(ULONG i=0;i<memory->NumberOfMemoryRanges;++i){auto& m=memory->MemoryRanges[i];if(valid(m.Memory.Rva,m.Memory.DataSize))ranges.push_back({m.StartOfMemoryRange,dump.data()+m.Memory.Rva,m.Memory.DataSize});}
    for(ULONG i=0;i<threads->NumberOfThreads;++i){auto& t=threads->Threads[i];if(valid(t.Stack.Memory.Rva,t.Stack.Memory.DataSize))ranges.push_back({t.Stack.StartOfMemoryRange,dump.data()+t.Stack.Memory.Rva,t.Stack.Memory.DataSize});}
    if(error)std::cout<<"EXCEPTION thread="<<error->ThreadId<<" code=0x"<<std::hex<<error->ExceptionRecord.ExceptionCode<<" address=0x"<<error->ExceptionRecord.ExceptionAddress<<std::dec<<"\n";
    for(ULONG i=0;i<threads->NumberOfThreads;++i){auto& t=threads->Threads[i];auto loc=t.ThreadContext;if(error&&t.ThreadId==error->ThreadId)loc=error->ThreadContext;
        if(!valid(loc.Rva,loc.DataSize)||loc.DataSize<sizeof(CONTEXT))continue;
        CONTEXT ctx{};memcpy(&ctx,dump.data()+loc.Rva,sizeof(ctx));
        std::cout<<"THREAD "<<t.ThreadId<<(error&&t.ThreadId==error->ThreadId?" EXCEPTION":"")<<"\n";
        STACKFRAME64 stack{};stack.AddrPC.Offset=ctx.Rip;stack.AddrPC.Mode=AddrModeFlat;stack.AddrStack.Offset=ctx.Rsp;stack.AddrStack.Mode=AddrModeFlat;stack.AddrFrame.Offset=ctx.Rbp;stack.AddrFrame.Mode=AddrModeFlat;
        frame(process,ctx.Rip);DWORD64 previous=0;
        for(int n=0;n<55;++n){if(!StackWalk64(IMAGE_FILE_MACHINE_AMD64,process,nullptr,&stack,&ctx,readMemory,functionTable,SymGetModuleBase64,nullptr)||!stack.AddrPC.Offset||stack.AddrPC.Offset==previous)break;if(!SymGetModuleBase64(process,stack.AddrPC.Offset))break;frame(process,stack.AddrPC.Offset);textureDetails(process,ctx,stack.AddrPC.Offset);previous=stack.AddrPC.Offset;}
    }
    SymCleanup(process);
}
