#include "game.h"
void animation_fixture_setup(void);
int main(void){
 video_init();audio_init();init_game();depth=0;animation_fixture_setup();
 audio_music((Music){1,90,100,50},0);draw_background();flip();
 debug_state[18]=1;while(!(wait_frame()&KEY_A)){}
 animation_targets(112);animation_battle(191);
 debug_state[18]=2;for(;;)wait_frame();
}
