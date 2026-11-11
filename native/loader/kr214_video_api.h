#pragma once
#include "forgeloader_api.h"

// Optional KR214 export. Returns 0 when unavailable, 1 when the existing value
// was already lower, 2 when the requested cap was verified, 3 when refused.
enum FLVideoOption214 {
    FL214_SCREEN_PERCENTAGE, FL214_SHADOW_QUALITY, FL214_VOLUMETRIC_FOG,
    FL214_REFLECTION_QUALITY, FL214_MOTION_BLUR
};
typedef int (FL_CALL *FLVideoClamp214)(unsigned option,int cap,float* before,float* after);
