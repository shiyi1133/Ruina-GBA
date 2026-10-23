#include "game.h"
#include "assets.h"
#include "shop_stack_config.h"
static u8 program[128];
const u32 shop_state_layout[5]={__builtin_offsetof(Game,items),__builtin_offsetof(Game,gold),__builtin_offsetof(Game,item_usage),sizeof(Game),sizeof(game.item_usage[0])};
static unsigned number(unsigned n,unsigned at){unsigned shift=0;while((n>>(shift+7))&&shift<28)shift+=7;for(;;){program[at++]=(n>>shift&127)|(shift?128:0);if(!shift)break;shift-=7;}return at;}
int main(void){
    unsigned at=0;int id;video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();
    depth=0;engine_clock_paused=1;scene_image=-1;set_map(3,5,5);depth=0;
    for(id=1;id<=MAX_PICTURE;id++)game.pictures[id].image=-1;
    for(id=1;id<=MAX_ITEM;id++)game.items[id]=99;
    game.gold=shop_initial_gold;game.selected=0;world_redraw();
    audio_music_quality(0);audio_music((Music){shop_music_id,90,100,50},0);audio_pause_music(1);audio_music_position(shop_music_peak);audio_pause_music(0);
    for(id=0;id<16;id++)audio_service();
    at=number(RM2K_OpenShop,at);at=number(0,at);at=number(0,at);at=number(6,at);
    at=number(0,at);at=number(0,at);at=number(0,at);at=number(0,at);at=number(1,at);at=number(2,at);
    at=number(0,at);at=number(0,at);at=number(0,at);at=number(0,at);
    stack[0]=(Frame){{{program,at},0,0},0,0,0,game.map};depth=1;if(shop_face_enabled)current_face=IMG_HERO0;
    debug_state[14]=1;while(!(wait_frame()&KEY_A)){}
    run_events();debug_state[14]=2;for(;;)wait_frame();
}
