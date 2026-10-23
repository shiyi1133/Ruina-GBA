#include "game.h"
#include "balanced.h"
void animation_fixture_setup(void);
void animation_fixture_cache_change(int stage);
static void hold(int stage,int phase){debug_state[18]=stage;debug_state[20]=phase;while(!(wait_frame()&KEY_A)){}while(wait_frame()&KEY_A){}}
int main(void){int stage;
 video_init();audio_init();init_game();depth=0;engine_clock_paused=1;animation_fixture_setup();draw_background();flip();
 for(stage=1;stage<=11;stage++){
  animation_fixture_cache_change(stage);video_clip(0,0,240,160);draw_battle();balanced_animation_background_store();flip();hold(stage,1);
  box(0,0,240,160,6);
  if(!balanced_animation_background_restore(0,0,240,160)){fault(9036);break;}
  flip();hold(stage,2);
  if(!balanced_battle_cache_store()){fault(9037);break;}
  box(96,24,144,72,6);balanced_battle_cache_restore(96,24,144,72);flip();hold(stage,3);
 }
 debug_state[18]=99;for(;;)wait_frame();
}
