#include "game.h"
#include "assets.h"
#include "music_full_score_config.h"
volatile u32 music_full_score_state[5];
int main(void){
    unsigned i;video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
    scene_image=IMG_TITLE;video_scene_palette(-1);
    for(i=0;i<sizeof(music_full_score_cases)/sizeof(music_full_score_cases[0]);i++){
        const unsigned*r=music_full_score_cases[i];unsigned last_second=~0U;int j;
        audio_music((Music){0,100,100,50},0);audio_music_quality(r[1]);audio_music((Music){r[0],90,100,50},0);
        for(j=0;j<8;j++)audio_service();
        clear(11);draw_text(8,8,"原曲简化音色：整曲运行检查",1,224);draw_num(8,28,r[0],2);draw_num(90,28,r[1],6);flip();
        music_full_score_state[0]=i+1;music_full_score_state[1]=r[1];music_full_score_state[2]=r[2];music_full_score_state[3]=r[3];debug_state[14]=i+1;
        for(;;){unsigned second=audio_debug[3]/16384,k;
            music_full_score_state[4]=audio_music_finished();
            if(second!=last_second){box(8,53,224,17,11);draw_num(8,55,second,1);draw_num(95,55,audio_debug[4],2);flip();last_second=second;}
            k=wait_frame();if(k&KEY_A)break;
        }
    }
    debug_state[14]=0x600d;for(;;)wait_frame();
}
