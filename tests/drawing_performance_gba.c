#include "game.h"
#include "assets.h"
/* Baseline backend predates these two APIs; the current backend supplies
 * strong definitions. This scene has no portrait. */
unsigned __attribute__((weak)) video_ticks(void){return *(volatile u16*)0x04000108;}
void __attribute__((weak)) portrait(int id,int x,int y){picture(id,x,y,0,0,36,36,0);}
void __attribute__((weak)) event_position_index_reset(void){}
/* Load a genuine ordinary save. The test then repeatedly draws that exact
 * state; original picture placement and art are not replaced by a test chart. */
int main(void){
 video_init();audio_init();init_game();
 if(!load_game()){debug_state[1]=1;for(;;)wait_frame();}
 audio_restore();depth=0;scene_image=-1;
 for(;;){event_set_direction(10001,(debug_state[14]&1)?4:6);world_redraw();debug_state[14]++;wait_frame();}
}
