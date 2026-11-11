// Included inside the portrait runtime's namespace. All engine API calls run
// from FEngineLoop::Tick on the game thread; the UI only reads snapshots.
std::unique_ptr<forgeloader::Loader> mods;
std::filesystem::path modsRoot,loaderData;
std::atomic<bool> modsReady{false},modsStarted{false};
DWORD modsThread=0;
Tick originalEngineTick=nullptr;
bool nativeLoadActive=false,choosingMod=false;
std::vector<void*> nativeLoadHooks;
void beginNativeLoad(){nativeLoadHooks.clear();nativeLoadActive=true;}
void finishNativeLoad(bool success){
    nativeLoadActive=false;
    if(!success)for(auto it=nativeLoadHooks.rbegin();it!=nativeLoadHooks.rend();++it)MH_RemoveHook(*it);
    nativeLoadHooks.clear();
}
int nativeHook(uintptr_t rva,void* detour,void** original){
    if(!base||GetCurrentThreadId()!=modsThread||!nativeLoadActive||!detour||!original)return 1;
    auto* dos=reinterpret_cast<IMAGE_DOS_HEADER*>(base);auto* nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(base+dos->e_lfanew);
    if(rva>=nt->OptionalHeader.SizeOfImage)return 1;
    auto* section=IMAGE_FIRST_SECTION(nt);bool executable=false;
    for(unsigned i=0;i<nt->FileHeader.NumberOfSections;++i)if((section[i].Characteristics&IMAGE_SCN_MEM_EXECUTE)&&rva>=section[i].VirtualAddress&&rva-section[i].VirtualAddress<section[i].Misc.VirtualSize){executable=true;break;}
    if(!executable)return 1;
    auto* target=reinterpret_cast<void*>(base+rva);
    try{nativeLoadHooks.push_back(target);}catch(...){return 1;}
    if(MH_CreateHook(target,detour,original)!=MH_OK){nativeLoadHooks.pop_back();return 2;}
    if(MH_EnableHook(target)!=MH_OK){MH_RemoveHook(target);nativeLoadHooks.pop_back();*original=nullptr;return 3;}
    return 0; // Same result convention as the supplied KR214 runtime.
}
void modLog(const char* text){
    log(text);
    auto file=loaderData/L"runtime.log";
    HANDLE h=CreateFileW(file.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE)return;LARGE_INTEGER size{};GetFileSizeEx(h,&size);
    if(size.QuadPart<1024*1024){DWORD written;WriteFile(h,text,DWORD(strlen(text)),&written,nullptr);WriteFile(h,"\r\n",2,&written,nullptr);}CloseHandle(h);
}
std::wstring utf8(const std::string& text){int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),int(text.size()),nullptr,0);if(n<=0)return {};std::wstring out(n,0);MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),int(text.size()),out.data(),n);return out;}
int modTitle(const char* text){if(GetCurrentThreadId()!=modsThread||!gameWindow||!text)return 0;auto title=utf8(text);return !title.empty()&&SetWindowTextW(gameWindow,title.c_str());}
void* engine(){return *reinterpret_cast<void**>(base+0x1587d668);}
float modGetFPS(){auto* e=engine();return GetCurrentThreadId()==modsThread&&e?api<float(__fastcall*)(void*)>(0x35075b0)(e):0;}
int modSetFPS(float fps){
    if(GetCurrentThreadId()!=modsThread||!std::isfinite(fps)||(fps!=0&&(fps<15||fps>240)))return 0;
    auto* e=engine();if(!e)return 0;api<void(__fastcall*)(void*,float)>(0x35198e0)(e,fps);
    char line[128];sprintf_s(line,"Engine FPS limit requested=%.1f readback=%.1f",fps,modGetFPS());modLog(line);return std::abs(modGetFPS()-fps)<0.1f;
}
int clampVideo214(unsigned option,int cap,float* before,float* after){
    if(GetCurrentThreadId()!=modsThread||!before||!after)return 0;
    struct Setting {const wchar_t* name;int min,max;};
    static constexpr Setting settings[]={{L"r.ScreenPercentage",50,100},{L"r.ShadowQuality",0,5},{L"r.VolumetricFog",0,1},{L"r.SSR.Quality",0,4},{L"r.MotionBlurQuality",0,4}};
    if(option>=sizeof(settings)/sizeof(settings[0])||cap<settings[option].min||cap>settings[option].max)return 0;
    auto* manager=*reinterpret_cast<void**>(base+0x156d3cc0);if(!manager)return 0;
    auto* var=api<void*(__fastcall*)(void*,const wchar_t*,bool)>(0x1b9c0e0)(manager,settings[option].name,false);if(!var)return 0;
    auto* vtable=*reinterpret_cast<uintptr_t**>(var);
    auto flags=reinterpret_cast<uint32_t(__fastcall*)(void*)>(vtable[0x18/8])(var);
    auto get=reinterpret_cast<float(__fastcall*)(void*)>(vtable[0x98/8]);
    *before=*after=get(var);if(!std::isfinite(*before))return 3;
    if(*before<=cap&&!(option==0&&*before<=0))return 1;
    if(flags&4)return 3; // Read-only variable.
    wchar_t value[16];swprintf_s(value,L"%d",cap);
    // Respect the engine's existing priority so in-game settings can still win.
    reinterpret_cast<void(__fastcall*)(void*,const wchar_t*,uint32_t)>(vtable[0x80/8])(var,value,flags&0xff000000u);
    *after=get(var);return std::abs(*after-cap)<0.01f?2:3;
}
bool prepareMods(){
    try{wchar_t path[32768];if(!GetModuleFileNameW(nullptr,path,32768))return false;
        modsRoot=std::filesystem::path(path).parent_path().parent_path().parent_path().parent_path()/L"Mods";
        if(!GetEnvironmentVariableW(L"LOCALAPPDATA",path,32768))return false;
        loaderData=std::filesystem::path(path)/L"PunCity"/L"Saved"/L"ForgeLoader";std::filesystem::create_directories(loaderData);
        FLHostV1 host{sizeof(FLHostV1),FORGELOADER_ABI_VERSION,modLog,modTitle,modSetFPS,modGetFPS};
        mods=std::make_unique<forgeloader::Loader>(modsRoot,loaderData/L"mods-status.json",host,forgeloader::NativeLoadHooks{beginNativeLoad,finishNativeLoad});modsReady.store(true);return true;
    }catch(const std::exception& e){log(e.what());return false;}
}
void __fastcall hookedEngineTick(void* self){
    originalEngineTick(self);
    if(!modsReady.load()||!gameWindow)return;
    static bool stopped=false;if(stopped)return;
    try{
        if(!modsStarted.load()){modsThread=GetCurrentThreadId();mods->load();modsStarted.store(true);modLog("ForgeLoader 0.2.2-KR214: mods initialized on game thread");}
        static auto previous=std::chrono::steady_clock::now();auto now=std::chrono::steady_clock::now();double dt=std::min(1.0,std::chrono::duration<double>(now-previous).count());previous=now;mods->tick(dt);
    }catch(const std::exception& e){modLog(e.what());stopped=true;}
}
void modsLobbyTick(){if(modsStarted.load()&&GetCurrentThreadId()==modsThread)try{mods->tick(0,true);}catch(const std::exception& e){modLog(e.what());}}
void chooseMod(HWND panel){
    auto root=modsRoot.parent_path();auto script=root/L"ForgeLoader"/L"Install-Mod.ps1";
    std::error_code ec;
    if(!std::filesystem::is_regular_file(script,ec)){
        MessageBoxW(gameWindow,L"Reinstale o ForgeLoader KR214 para recuperar o instalador de mods.",L"Instalar mod",MB_OK|MB_ICONERROR);return;
    }
    choosingMod=true;ShowWindow(panel,SW_HIDE);
    wchar_t file[32768]{};OPENFILENAMEW picker{};picker.lStructSize=sizeof(picker);picker.hwndOwner=gameWindow;picker.lpstrTitle=L"Instalar mod ForgeLoader";
    picker.lpstrFilter=L"Mods ForgeLoader (*.flmod;*.zip)\0*.flmod;*.zip\0\0";picker.lpstrFile=file;picker.nMaxFile=32768;
    picker.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST|OFN_NOCHANGEDIR;
    bool selected=GetOpenFileNameW(&picker)!=FALSE;choosingMod=false;
    if(!selected){if(CommDlgExtendedError())modLog("KR214 mod file picker failed");return;}
    wchar_t system[MAX_PATH]{};auto length=GetSystemDirectoryW(system,MAX_PATH);if(!length||length>=MAX_PATH)return;
    auto powershell=std::filesystem::path(system)/L"WindowsPowerShell"/L"v1.0"/L"powershell.exe";
    auto args=L"-NoProfile -STA -ExecutionPolicy Bypass -File \""+script.wstring()+L"\" -GamePath \""+root.wstring()+L"\" -Package \""+file+L"\"";
    auto result=ShellExecuteW(gameWindow,L"open",powershell.c_str(),args.c_str(),root.c_str(),SW_HIDE);
    if(reinterpret_cast<INT_PTR>(result)<=32){modLog("KR214 mod installer launch failed");MessageBoxW(gameWindow,L"Nao foi possivel abrir o instalador. Use ForgeLoader\\Instalar-Mod.cmd.",L"Instalar mod",MB_OK|MB_ICONERROR);}
    else modLog("KR214 mod installer launched from in-game picker");
}
LRESULT CALLBACK modsPanelProc(HWND panel,UINT msg,WPARAM wp,LPARAM lp){
    if(msg==WM_COMMAND){
        if(LOWORD(wp)==10){auto summary=utf8(mods->summary());if(summary.empty())summary=L"Aguardando inicializacao do jogo.";MessageBoxW(gameWindow,summary.c_str(),L"Meus mods - reinicie apos instalar",MB_OK|MB_ICONINFORMATION);}
        if(LOWORD(wp)==11)ShellExecuteW(gameWindow,L"open",modsRoot.c_str(),nullptr,nullptr,SW_SHOWNORMAL);
        if(LOWORD(wp)==12){chooseMod(panel);}
        return 0;
    }
    if(msg==WM_MOUSEACTIVATE)return MA_NOACTIVATE;
    if(msg==WM_TIMER){POINT origin{};RECT rect{};HWND foreground=GetForegroundWindow();bool show=!choosingMod&&IsWindowVisible(gameWindow)&&!IsIconic(gameWindow)&&(foreground==gameWindow||GetAncestor(foreground,GA_ROOTOWNER)==gameWindow);
        if(ClientToScreen(gameWindow,&origin)&&GetClientRect(gameWindow,&rect))SetWindowPos(panel,HWND_TOP,origin.x+std::max(8L,rect.right-330),origin.y+8,322,40,SWP_NOACTIVATE);
        if(show!=bool(IsWindowVisible(panel)))ShowWindow(panel,show?SW_SHOWNOACTIVATE:SW_HIDE);return 0;
    }
    return DefWindowProcW(panel,msg,wp,lp);
}
void createModsPanel(){
    HINSTANCE instance=GetModuleHandleW(L"KingdomsPortraits.dll");WNDCLASSW cls{};cls.lpfnWndProc=modsPanelProc;cls.hInstance=instance;cls.lpszClassName=L"ForgeLoaderModsPanel";cls.hbrBackground=reinterpret_cast<HBRUSH>(COLOR_BTNFACE+1);RegisterClassW(&cls);
    HWND panel=CreateWindowExW(WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE,cls.lpszClassName,L"ForgeLoader",WS_POPUP|WS_BORDER,16,16,322,40,gameWindow,nullptr,instance,nullptr);
    for(int i=0;i<3;++i)CreateWindowExW(0,L"BUTTON",i==0?L"Meus mods":i==1?L"Abrir pasta":L"Instalar mod",WS_VISIBLE|WS_CHILD|BS_PUSHBUTTON,4+106*i,4,102,30,panel,reinterpret_cast<HMENU>(INT_PTR(10+i)),instance,nullptr);
    SetTimer(panel,1,250,nullptr);modLog("ForgeLoader Mods panel created");
}
