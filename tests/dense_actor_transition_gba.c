#include "game.h"
#include "assets.h"
extern void fixture_native_palette(int image);
#include "dense_actor_transition_config.h"
extern const u8 original_characters_start[];
extern volatile u32 audio_stream_debug[4];
typedef struct {u16 image;u8 index,color_count;u32 palette,tiles;} Record;
volatile u32 dense_transition_debug[4];
static int hud_image;
static void actors(const Record*r,int count,int stage){int k;video_map_objects_begin();for(k=0;k<23;k++){int i=(stage*23+k)%count;video_map_actor(r[i].image,r[i].index,2,8+(k%8)*28,16+(k/8)*48);}video_map_hud(hud_image,0,144);video_map_hud(hud_image,176,144);}
int main(void){
 const u32*h=(const u32*)original_characters_start;const Record*r=(const Record*)(original_characters_start+h[2]);unsigned stage;int k;
 video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();hud_image=game.pictures[20].image;depth=0;engine_clock_paused=1;audio_music((Music){0,100,100,50},0);fixture_native_palette(-1);clear(14);video_map_upload(0,0,240,160,0,0);
 audio_music_quality(0);audio_music((Music){dense_music_id,90,100,50},0);audio_pause_music(1);audio_music_position(dense_music_seek);audio_pause_music(0);
 for(k=0;k<8;k++)audio_service();dense_transition_debug[1]=audio_stream_debug[0];
 for(stage=0;stage<7;stage++){
  dense_transition_debug[2]=1;for(k=0;k<4;k++)audio_effect(k);
  actors(r,h[1],stage);if(video_map_objects_retry())actors(r,h[1],stage);video_map_present(0,0,15);
  dense_transition_debug[2]=0;dense_transition_debug[0]=stage+1;while(!(wait_frame()&KEY_A)){}
 }
 dense_transition_debug[0]=999;for(;;)wait_frame();
}
