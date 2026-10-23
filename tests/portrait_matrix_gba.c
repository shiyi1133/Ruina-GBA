#include "game.h"
#include "assets.h"
#include "portrait_matrix_config.h"
extern const u8 original_portraits_start[],portrait_combinations_start[];
extern volatile u32 audio_stream_debug[4];
typedef struct {u16 image,sheet;u32 tiles;} Record;
static unsigned stage;
static void show(unsigned mask){if(portrait_stress){int k;for(k=0;k<4;k++)audio_effect(k);}flip();debug_state[13]=mask;debug_state[14]=++stage;while(!(wait_frame()&KEY_A)){} }
int main(void){
 const u32*h=(const u32*)original_portraits_start,*m=(const u32*)portrait_combinations_start;const Record*r=(const Record*)(original_portraits_start+h[2]);const u16*index=(const u16*)(portrait_combinations_start+m[4]);unsigned i,mask,mixed_count=0;
 video_init();audio_init();init_game();depth=0;engine_clock_paused=1;audio_music((Music){0,100,100,50},0);video_scene_palette(-1);
 if(portrait_stress){int k;audio_music_quality(0);audio_music((Music){portrait_music_id,90,100,50},0);audio_pause_music(1);audio_music_position(portrait_music_seek);audio_pause_music(0);for(k=0;k<4;k++)game.system_sounds[k]=(Music){portrait_effects[k],80,200,k*30};for(k=0;k<8;k++)audio_service();audio_stream_debug[3]=audio_stream_debug[0];}
 for(i=0;i<h[1]&&(!portrait_quick||i<4);i++){clear(11);portrait(r[i].image,8,24);video_map_cursor(5,112,1);show(1U<<r[i].sheet);}
 for(mask=0;mask<m[3];mask++)if(index[mask]&&(!portrait_quick||mixed_count++<40)){
  unsigned sheets[4],count=0,k,s;for(s=0;s<m[2];s++)if(mask&(1U<<s))sheets[count++]=s;
  clear(11);for(k=0;k<4;k++){s=sheets[k%count];i=s*16+((mask+k*7)&15);portrait(r[i].image,8+k*58,24);}video_map_cursor(5,112,1);show(mask);
 }
 debug_state[14]=9999;for(;;)wait_frame();
}
