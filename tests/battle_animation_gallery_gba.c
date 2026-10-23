/* Controlled cartridge; links unchanged production animations/video/audio. */
#include "game.h"
#include "assets.h"
#include "balanced.h"
#include "battle_animation_cases.h"
extern volatile u32 animation_render_trace[16];
static void hold(unsigned stage){debug_state[14]=stage;while(!(wait_frame()&KEY_A)){} }
int main(void){unsigned i;video_init();audio_init();init_game();depth=0;engine_clock_paused=1;audio_music((Music){0,100,100,50},0);battle_active=1;
 draw_background();balanced_animation_background_store();flip();hold(1);
 for(i=0;i<sizeof(animation_cases)/sizeof(animation_cases[0]);i++){
  const int*p=animation_cases[i];game.animations[0]=(EventAnimation){p[0],p[1]*2,1,0};animations_tick();hold(i+2);
  game.animations[0].remaining=0;animations_tick();hold(0x10000+i);
 }
 debug_state[14]=0x600d;for(;;)wait_frame();
}
