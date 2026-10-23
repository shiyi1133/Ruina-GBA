#include "game.h"
#include "assets.h"
extern int balanced_original_choices(LcfSpan,int);
volatile u32 balanced_menu_test[5];
int main(void){
    int context,mode;static const char text[]="明亮的古老石阶/破损而潮湿的走廊/寂静森林中的小屋/远处传来的钟声/被藤蔓遮住的石门/墙上古老的文字/点燃墙边的火把/回到熟悉的街道";
    video_init();audio_init();init_game();depth=0;engine_clock_paused=1;presentation_reset();
    for(context=0;context<3;context++){
        battle_active=0;
        if(context==0){game.map=0;scene_image=IMG_TITLE;}
        else{set_map(23,15,12);scene_image=-1;depth=0;world_redraw();if(context==2)battle_active=1;}
        for(mode=0;mode<2;mode++){
            int result;balanced_menu_test[0]=context;balanced_menu_test[1]=mode;balanced_menu_test[2]=1;
            result=mode?balanced_original_choices((LcfSpan){(const u8*)text,sizeof(text)-1},1):choices((LcfSpan){(const u8*)text,sizeof(text)-1},1);
            balanced_menu_test[3+mode]=result;balanced_menu_test[2]=2;
        }
    }
    balanced_menu_test[2]=3;for(;;)wait_frame();
}
