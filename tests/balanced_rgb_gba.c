#include "game.h"
#include "assets.h"
#include "balanced_rgb_cases.h"
int main(void){
    unsigned stage;int i;
    video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
    audio_music((Music){0,100,100,50},0);
    for(stage=0;stage<sizeof(rgb_cases)/sizeof(rgb_cases[0]);stage++){
        const int*p=rgb_cases[stage];u8 tone[4]={p[12],p[13],p[14],p[15]};
        video_clip(0,0,240,160);video_scene_palette(-1);clear(14);
        for(i=0;i<256;i++)box(i%16*15,i/16*10,15,10,i);
        video_clip(p[16],p[17],p[18],p[19]);
        picture_region_scaled(p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],p[9],p[10],p[11]?tone:0);
        video_clip(0,0,240,160);flip();debug_state[14]=stage+1;
        while(!(wait_frame()&KEY_A)){}
    }
    debug_state[14]=0x600d;for(;;)wait_frame();
}
