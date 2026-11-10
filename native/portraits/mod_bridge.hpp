// Included inside the portrait runtime's namespace. All engine API calls run
// from FEngineLoop::Tick on the game thread; the UI only reads snapshots.
std::unique_ptr<forgeloader::Loader> mods;
std::filesystem::path modsRoot,loaderData;
std::atomic<bool> modsReady{false},modsStarted{false};
DWORD modsThread=0;
Tick originalEngineTick=nullptr;
void modLog(const char* text){
    log(text);
    auto file=loaderData/L"runtime.log";
    HANDLE h=CreateFileW(file.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(h==INVALID_HANDLE_VALUE)return;LARGE_INTEGER size{};GetFileSizeEx(h,&size);
    if(size.QuadPart<1024*1024){DWORD written;WriteFile(h,text,DWORD(strlen(text)),&written,nullptr);WriteFile(h,"\r\n",2,&written,nullptr);}CloseHandle(h);
}
std::wstring utf8(const std::string& text){int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),int(text.size()),nullptr,0);if(n<=0)return {};std::wstring out(n,0);MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),int(text.size()),out.data(),n);return out;}
int modTitle(const char* text){if(GetCurrentThreadId()!=modsThread||!gameWindow||!text)return 0;auto title=utf8(text);return !title.empty()&&SetWindowTextW(gameWindow,title.c_str());}
void* engine(){return *reinterpret_cast<void**>(base+0x1684f468);}
float modGetFPS(){auto* e=engine();return GetCurrentThreadId()==modsThread&&e?api<float(__fastcall*)(void*)>(0x4339280)(e):0;}
int modSetFPS(float fps){
    if(GetCurrentThreadId()!=modsThread||!std::isfinite(fps)||(fps!=0&&(fps<15||fps>240)))return 0;
    auto* e=engine();if(!e)return 0;api<void(__fastcall*)(void*,float)>(0x434b5b0)(e,fps);
    char line[128];sprintf_s(line,"Engine FPS limit requested=%.1f readback=%.1f",fps,modGetFPS());modLog(line);return std::abs(modGetFPS()-fps)<0.1f;
}
bool prepareMods(){
    try{wchar_t path[32768];if(!GetModuleFileNameW(nullptr,path,32768))return false;
        modsRoot=std::filesystem::path(path).parent_path().parent_path().parent_path().parent_path()/L"Mods";
        if(!GetEnvironmentVariableW(L"LOCALAPPDATA",path,32768))return false;
        loaderData=std::filesystem::path(path)/L"PunCity"/L"Saved"/L"ForgeLoader";std::filesystem::create_directories(loaderData);
        FLHostV1 host{sizeof(FLHostV1),FORGELOADER_ABI_VERSION,modLog,modTitle,modSetFPS,modGetFPS};
        mods=std::make_unique<forgeloader::Loader>(modsRoot,loaderData/L"mods-status.json",host);modsReady.store(true);return true;
    }catch(const std::exception& e){log(e.what());return false;}
}
void __fastcall hookedEngineTick(void* self){
    originalEngineTick(self);
    if(!modsReady.load()||!gameWindow)return;
    static bool stopped=false;if(stopped)return;
    try{
        if(!modsStarted.load()){modsThread=GetCurrentThreadId();mods->load();modsStarted.store(true);modLog("ForgeLoader 0.2.0: mods initialized on game thread");}
        static auto previous=std::chrono::steady_clock::now();auto now=std::chrono::steady_clock::now();double dt=std::min(1.0,std::chrono::duration<double>(now-previous).count());previous=now;mods->tick(dt);
    }catch(const std::exception& e){modLog(e.what());stopped=true;}
}
void modsLobbyTick(){if(modsStarted.load()&&GetCurrentThreadId()==modsThread)try{mods->tick(0,true);}catch(const std::exception& e){modLog(e.what());}}
LRESULT CALLBACK modsPanelProc(HWND panel,UINT msg,WPARAM wp,LPARAM lp){
    if(msg==WM_COMMAND){
        if(LOWORD(wp)==10){auto summary=utf8(mods->summary());if(summary.empty())summary=L"Aguardando inicializacao do jogo.";MessageBoxW(gameWindow,summary.c_str(),L"Meus mods - reinicie apos instalar",MB_OK|MB_ICONINFORMATION);}
        if(LOWORD(wp)==11)ShellExecuteW(gameWindow,L"open",modsRoot.c_str(),nullptr,nullptr,SW_SHOWNORMAL);
        if(LOWORD(wp)==12){auto installer=modsRoot.parent_path()/L"ForgeLoader"/L"Instalar-Mod.cmd";if(std::filesystem::is_regular_file(installer))ShellExecuteW(gameWindow,L"open",installer.c_str(),nullptr,nullptr,SW_SHOWNORMAL);else MessageBoxW(gameWindow,L"Use Instalar-Mod.cmd do pacote ForgeLoader ou copie a pasta do mod para Mods e reinicie.",L"Instalar mod",MB_OK);}
        return 0;
    }
    if(msg==WM_MOUSEACTIVATE)return MA_NOACTIVATE;
    if(msg==WM_TIMER){POINT origin{};RECT rect{};HWND foreground=GetForegroundWindow();bool show=IsWindowVisible(gameWindow)&&!IsIconic(gameWindow)&&(foreground==gameWindow||GetAncestor(foreground,GA_ROOTOWNER)==gameWindow);
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
