#include "../../../../native/loader/forgeloader_api.h"
static const FLHostV1* host;
static void tick(double){static bool once=false;if(!once){once=true;host->log("[forge.native_hello] native tick executed");}}
extern "C" __declspec(dllexport) int __cdecl ForgeMod_Load(const FLHostV1* api,FLModV1* mod){
    if(!api||api->size!=sizeof(FLHostV1)||api->abi_version!=FORGELOADER_ABI_VERSION||!mod||mod->size!=sizeof(FLModV1))return 0;
    host=api;mod->id="forge.native_hello";mod->version="1.0.0";mod->on_tick=tick;host->log("[forge.native_hello] native module started");return 1;
}
