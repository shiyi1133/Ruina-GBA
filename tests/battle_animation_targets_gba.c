#include "game.h"
#include "balanced.h"
void animation_fixture_setup(void);
void animation_fixture_skill(int id,int target);
int main(void){int i;static const int cases[][2]={{27,1},{201,4},{170,4},{309,0}};
 video_init();audio_init();init_game();depth=0;audio_music((Music){0,100,100,50},0);
 for(i=0;i<4;i++){
  animation_fixture_setup();draw_background();flip();debug_state[18]=i+1;
  animation_fixture_skill(cases[i][0],cases[i][1]);debug_state[18]=0x100+i;
  while(!(wait_frame()&KEY_A)){}
 }
 debug_state[18]=0x600d;for(;;)wait_frame();
}
