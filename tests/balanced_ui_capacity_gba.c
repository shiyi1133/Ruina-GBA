#include "game.h"
#include "assets.h"
static void hold(int stage){flip();debug_state[14]=stage;while(!(wait_frame()&KEY_A)){} }
int main(void){
    int stage,i;video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
    set_map(23,15,12);depth=0;scene_image=-1;world_redraw();debug_state[15]=20;
    draw_scene();hold(1);
    for(stage=0;stage<3;stage++){
        int count=stage?260:30;draw_scene();box(0,0,240,160,11);
        for(i=0;i<count;i++){unsigned code=glyph_codes[500+i];char text[3]={code>>8,code,0};
            draw_text(i%20*12,i/20*12,text,(i+stage)%2?1:2,12);
        }
        if(stage==1)box(0,0,8,160,0);
        hold(stage+2);
    }
    debug_state[14]=0x600d;for(;;)wait_frame();
}
