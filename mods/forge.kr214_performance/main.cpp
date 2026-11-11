#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include "../../native/loader/kr214_video_api.h"

extern "C" __declspec(dllexport) int __cdecl ForgeMod_Load(const FLHostV1* api,FLModV1* mod){
    if(!api||api->size!=sizeof(FLHostV1)||api->abi_version!=1||!mod||mod->size!=sizeof(FLModV1))return 0;
    auto module=GetModuleHandleW(L"KingdomsPortraits.dll");
    auto clamp=module?reinterpret_cast<FLVideoClamp214>(GetProcAddress(module,"ForgeLoader_ClampVideo214")):nullptr;
    if(!clamp){api->log("[forge.kr214_performance] requires the updated KR214 ForgeLoader runtime");return 0;}
    struct Limit {unsigned option;int cap;const char* name;};
    constexpr Limit limits[]={{FL214_SCREEN_PERCENTAGE,85,"3D resolution"},{FL214_SHADOW_QUALITY,2,"shadows"},{FL214_VOLUMETRIC_FOG,0,"volumetric fog"},{FL214_REFLECTION_QUALITY,0,"screen-space reflections"},{FL214_MOTION_BLUR,0,"motion blur"}};
    for(auto& l:limits){float before=0,after=0;int result=clamp(l.option,l.cap,&before,&after);char line[200];
        if(result==0)sprintf_s(line,"[forge.kr214_performance] %s unavailable",l.name);
        else sprintf_s(line,"[forge.kr214_performance] %s %.1f -> %.1f (%s)",l.name,before,after,result==2?"applied":result==1?"kept existing lower value":"refused");
        api->log(line);
    }
    float limit=api->get_fps_limit();if(limit<=0||limit>60)api->set_fps_limit(60);
    mod->id="forge.kr214_performance";mod->version="1.0.0";return 1;
}
