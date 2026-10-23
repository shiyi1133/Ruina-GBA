#include "game.h"
#include "assets.h"
extern void fixture_native_palette(int image);
int main(void){
 static const int cameras[3][2]={{0,0},{80,80},{8,16}};int i;
 video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
 for(i=0;i<3;i++){
  int x=cameras[i][0],y=cameras[i][1];
  fixture_native_palette(IMG_CAVE);video_clip(0,0,240,160);clear(14);
  picture_region_scaled(IMG_CAVE,0,0,x,y,240,160,240,160,0,0,0);
  video_map_upload(0,0,240,160,x,y);video_map_objects_begin();video_map_present(x,y,15);
  debug_state[14]=i+1;while(!(wait_frame()&KEY_A)){}
 }
 for(;;)wait_frame();
}
