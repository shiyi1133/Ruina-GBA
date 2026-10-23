#include "game.h"
#include "assets.h"
extern void fixture_native_palette(int image);
#include "panorama_matrix_config.h"
volatile u32 panorama_render_timing[3];
int main(void){unsigned i;video_init();audio_init();init_game();depth=0;engine_clock_paused=1;audio_music((Music){0,100,100,50},0);
 for(i=0;i<sizeof(panorama_matrix)/sizeof(*panorama_matrix);i++){const unsigned*r=panorama_matrix[i];fixture_native_palette(r[0]);video_clip(0,0,240,160);clear(14);panorama_render_timing[0]=video_ticks();picture_region_scaled(r[0],0,0,r[1],r[2],240,160,240,160,0,0,0);panorama_render_timing[1]=(video_ticks()-panorama_render_timing[0])&65535;video_map_upload(0,0,240,160,r[1],r[2]);video_map_objects_begin();video_map_present(r[1],r[2],15);debug_state[14]=i+1;while(!(wait_frame()&KEY_A)){} }
 debug_state[14]=9999;for(;;)wait_frame();}
