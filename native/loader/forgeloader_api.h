#pragma once
#include <stdint.h>
#ifdef _WIN32
#define FL_CALL __cdecl
#define FL_EXPORT __declspec(dllexport)
#else
#define FL_CALL
#define FL_EXPORT
#endif
#define FORGELOADER_ABI_VERSION 1

// Strings are UTF-8, owned by the caller and consumed before the call returns.
// Every callback runs on the game thread. No C++ objects cross DLL boundaries.
typedef struct FLHostV1 {
    uint32_t size;
    uint32_t abi_version;
    void (FL_CALL *log)(const char* message);
    int (FL_CALL *set_window_title)(const char* title);
    int (FL_CALL *set_fps_limit)(float fps);
    float (FL_CALL *get_fps_limit)(void);
} FLHostV1;

typedef struct FLModV1 {
    uint32_t size;
    uint32_t abi_version;
    const char* id;
    const char* version;
    void (FL_CALL *on_tick)(double seconds);
    void (FL_CALL *on_lobby_tick)(double seconds);
} FLModV1;

// Export this symbol from a native mod. Return nonzero only after successful init.
typedef int (FL_CALL *FLStartModV1)(const FLHostV1* host, FLModV1* result);
