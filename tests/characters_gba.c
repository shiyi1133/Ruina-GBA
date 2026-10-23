#include "game.h"
#include "assets.h"
extern void fixture_native_palette(int image);
extern const u8 original_characters_start[];
typedef struct {u16 image;u8 index,color_count;u32 palette,tiles;} Record;
int main(void){
 const u32*h=(const u32*)original_characters_start;const Record*r=(const Record*)(original_characters_start+h[2]);unsigned i;int j;static const int directions[4]={8,6,2,4};
 video_init();audio_init();init_game();depth=0;engine_clock_paused=1;audio_music((Music){0,100,100,50},0);
 for(i=0;i<h[1];i++){
  video_scene_palette(-1);clear(14);flip();fixture_native_palette(-1);clear(14);video_map_upload(0,0,240,160,0,0);video_map_objects_begin();
  for(j=0;j<4;j++)video_map_actor(r[i].image,r[i].index,directions[j],30+j*45,50);
  video_map_present(0,0,15);debug_state[14]=i+1;debug_state[13]=r[i].image;
  while(!(wait_frame()&KEY_A)){}
 }
 debug_state[14]=999;for(;;)wait_frame();
}
