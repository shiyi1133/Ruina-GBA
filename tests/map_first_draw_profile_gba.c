#include "game.h"
#include "assets.h"
int main(void){
    video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();
    audio_restore();depth=0;engine_clock_paused=1;scene_image=-1;
    debug_state[14]=1;while(!(wait_frame()&KEY_A)){}
    world_redraw();debug_state[14]=2;for(;;)wait_frame();
}
