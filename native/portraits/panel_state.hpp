#pragma once
#include <cstdint>
namespace krphoto {
// ESlateVisibility in the matched UE4 build: Visible, Collapsed, Hidden,
// HitTestInvisible, SelfHitTestInvisible. The last two still draw the widget.
inline bool settings_visible(uint8_t visibility){return visibility==0||visibility==3||visibility==4;}
inline bool panel_visible(uint64_t now,uint64_t lastTick,bool settingsOpen,
                          bool windowVisible,bool foregroundOwned,bool choosingFile){
    return lastTick!=0&&now>=lastTick&&now-lastTick<1500&&settingsOpen&&
           windowVisible&&foregroundOwned&&!choosingFile;
}
}
