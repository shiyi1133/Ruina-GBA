#include "game.h"
#include "assets.h"
#include "../experiments/quality_preview/quality.h"
extern int quality_original_choices(LcfSpan,int);
volatile u32 quality_menu_test[4];
int main(void){int mode;static const char text[]="选项一/选项二/选项三/选项四/选项五/选项六/选项七/选项八";
    video_init();audio_init();presentation_reset();engine_clock_paused=1;game.map=0;scene_image=IMG_TITLE;quality_fit=1;
    for(mode=0;mode<2;mode++){int result;quality_menu_test[0]=mode;quality_menu_test[1]=1;
        result=mode?quality_original_choices((LcfSpan){(const u8*)text,sizeof(text)-1},1):choices((LcfSpan){(const u8*)text,sizeof(text)-1},1);
        quality_menu_test[2+mode]=result;quality_menu_test[1]=2;
    }
    quality_menu_test[1]=3;for(;;)wait_frame();
}
