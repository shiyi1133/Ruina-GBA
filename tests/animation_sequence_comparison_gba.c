#include "game.h"
#include "animation_sequences.h"
void animation_fixture_setup(void);
static void hold(u32 stage){debug_state[14]=stage;while(!(wait_frame()&KEY_A)){} }
int main(void){unsigned i,frame;
 video_init();audio_init();init_game();depth=0;animation_fixture_setup();engine_clock_paused=1;audio_music((Music){1,90,100,50},0);draw_background();flip();
 for(i=0;i<sizeof(animation_sequences)/sizeof(animation_sequences[0]);i++){
  int id=animation_sequences[i][0],n=animation_sequences[i][1];animation_targets(112);animation_start(id);
  for(frame=0;frame<(unsigned)n;frame++){
   game.animations[0]=(EventAnimation){id,frame*2,1,112};animations_tick();hold(0x10000000+(i<<12)+frame);
  }
  game.animations[0].remaining=0;animations_tick();hold(0x20000000+i);
 }
 debug_state[14]=0x600d;for(;;)wait_frame();
}
