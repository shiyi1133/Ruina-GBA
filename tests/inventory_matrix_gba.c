#include "game.h"
#include "assets.h"
#include "inventory_matrix_config.h"
volatile u32 inventory_matrix_result;
int main(void){
    int i;video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();
    depth=0;engine_clock_paused=1;scene_image=-1;set_map(3,5,5);depth=0;
    for(i=1;i<=MAX_PICTURE;i++)game.pictures[i].image=-1;
    for(i=1;i<=MAX_ITEM;i++)game.items[i]=99;
    game.selected=0;world_redraw();if(inventory_rgb)scene_image=IMG_TITLE;current_face=IMG_HERO0;
    audio_music_quality(0);audio_music((Music){inventory_music_id,90,100,50},0);audio_pause_music(1);audio_music_position(inventory_music_peak);audio_pause_music(0);for(i=0;i<16;i++)audio_service();
    debug_state[14]=1;while(!(wait_frame()&KEY_A)){}
    inventory_matrix_result=inventory_select(inventory_mode);debug_state[14]=2;for(;;)wait_frame();
}
