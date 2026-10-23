#include "game.h"
#include "assets.h"
extern void fixture_native_palette(int image);
extern const u8 original_characters_start[];
typedef struct {u16 image;u8 index,color_count;u32 palette,tiles;} Record;
static void actors(const Record*r,int count,int stage){int k;video_map_objects_begin();for(k=0;k<3;k++){int i=k==0?stage%count:k==1?(stage*17+35)%count:0;video_map_actor(r[i].image,r[i].index,(int[]){8,6,2,4}[(stage+k)%4],30+k*70,50);}}
int main(void){const u32*h=(const u32*)original_characters_start;const Record*r=(const Record*)(original_characters_start+h[2]);unsigned stage;video_init();audio_init();init_game();depth=0;engine_clock_paused=1;audio_music((Music){0,100,100,50},0);fixture_native_palette(-1);clear(11);video_map_upload(0,0,240,160,0,0);
 for(stage=0;stage<h[1]*2;stage++){actors(r,h[1],stage);if(video_map_objects_retry())actors(r,h[1],stage);video_map_present(0,0,0);debug_state[14]=stage+1;while(!(wait_frame()&KEY_A)){} }
 debug_state[14]=9999;for(;;)wait_frame();}
