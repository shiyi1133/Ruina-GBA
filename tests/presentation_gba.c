#include "game.h"
#include "assets.h"
/* Isolated cartridge: only the fixture selects the scenes. Production event,
 * video, timing, picture and black-cut functions are linked unchanged. */
static void hold(int stage){debug_state[14]=stage;while(!(wait_frame()&KEY_A)){} }
static void transition(int code,int type,int stage){
    debug_state[14]=stage;
    {int p[6]={type};debug_state[13]=presentation_command(code,p);}
}
int main(void){
    int p[6]={31,0,0,31,10,1},n;
    video_init();audio_init();init_game();depth=0;
    audio_music((Music){0,100,100,50},0);
    game.party_count=1;game.party[0]=1;set_map(23,15,12);scene_image=IMG_TITLE;
    world_redraw();hold(1);
    transition(RM2K_EraseScreen,18,2);hold(3);
    draw_scene();box(8,100,224,50,11);rect(8,100,224,50,6);
    draw_text(16,111,"Dialogue remains readable",1,210);flip();hold(4);
    set_map(3,15,12);scene_image=IMG_FOREST;
    transition(RM2K_ShowScreen,8,5);hold(6);
    n=presentation_command(RM2K_FlashScreen,p);debug_state[14]=7;
    while(n--){debug_state[13]=n;wait_frame();}hold(8);
    p[0]=1;p[1]=2;presentation_command(RM2K_WeatherEffects,p);
    world_redraw();hold(9);
    transition(RM2K_EraseScreen,19,10);
    presentation_reset();clear(11);draw_text(8,20,"Title/reset stays visible",1,225);flip();
    hold(11);for(;;)wait_frame();
}
