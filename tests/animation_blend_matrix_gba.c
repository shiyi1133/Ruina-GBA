/* All original opacity percentages, tint, clipping and shared-row invalidation. */
#include "game.h"
#include "balanced.h"
#include "animation_blend_matrix.h"
int main(void){
 unsigned stage,i;static const u8 tone[4]={80,110,90,50};
 video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
 audio_music((Music){0,100,100,50},0);
 for(stage=0;stage<3;stage++){
  video_clip(0,0,240,160);video_scene_palette(-1);clear(11);
  if(stage<2)for(i=0;i<100;i++)balanced_animation_cell(&blend_source,i%10*24,i/10*16,24,16,i,stage?tone:0);
  else{
   balanced_animation_cell(&blend_source,-5,-3,49,37,37,tone);
   /* This scaled illustration borrows the same row as the alpha lookup.
    * Clear it after the call so the independent expected screen stays simple. */
   picture_region_scaled(1,239,159,0,0,images[1].width,images[1].height,1,1,0,0,0);
   box(239,159,1,1,11);
   balanced_animation_cell(&blend_source,60,30,99,75,37,tone);
   balanced_animation_cell(&blend_source,210,140,49,37,50,0);
  }
  flip();debug_state[14]=stage+1;while(!(wait_frame()&KEY_A)){}
 }
 debug_state[14]=0x600d;for(;;)wait_frame();
}
