#include "game.h"
#include "assets.h"
extern void fixture_native_palette(int image);
static void show_map(int stage){
 unsigned i;int n=0;
 video_clip(0,0,240,160);clear(14);video_map_upload(0,0,240,160,0,0);video_map_objects_begin();
 for(i=0;i<resource_image_count;i++)if(resource_images[i].kind==3){video_map_actor(resource_images[i].image,0,2,n%3*72,n/3*48);n++;}
 video_map_hud(game.pictures[25].image,60,130);video_map_hud(game.pictures[20].image,128,130);
 video_map_present(0,0,0);debug_state[14]=stage;while(!(wait_frame()&KEY_A)){}
}
int main(void){
 video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();depth=0;engine_clock_paused=1;
 show_map(1);
 clear(11);portrait(IMG_HERO0,8,20);flip();debug_state[14]=2;while(!(wait_frame()&KEY_A)){}
 show_map(3);for(;;)wait_frame();
}
