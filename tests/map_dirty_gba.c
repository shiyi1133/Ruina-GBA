#include "game.h"
#include "assets.h"
/* Controlled renderer states loaded from a genuine ordinary save. This is a
 * visual equivalence fixture, not natural event progression or a playthrough. */
static void show(int stage){
#ifdef REFERENCE_FULL
 world_render_invalidate();
#endif
 world_redraw();debug_state[14]=stage;
 while(!(wait_frame()&KEY_A)){}
}
int main(void){
 int p[16]={25,0,62,8,0,100,0,1,100,100,100,100};
 video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();audio_restore();depth=0;engine_clock_paused=1;scene_image=-1;
 show(1);event_set_direction(10001,6);show(2);
 if(map_step_allowed(10001,game.x,game.y,game.x,game.y-1,0))event_relocate(10001,game.x,game.y-1);show(3);
 game.selected=1;show(4);game.selected=7;show(5);
 game.pictures[30].transparency=game.pictures[30].target_transparency=80;show(6);
 pictures_move(p);show(7);render_picture_erase(25);show(8);
 draw_scene();box(20,20,200,80,11);draw_text(30,30,"Temporary menu overlay",1,180);flip();debug_state[14]=9;while(!(wait_frame()&KEY_A)){}
 show(10);tile_substitute(0,142,100);show(11);
 set_map(3,15,12);show(12);
 for(;;)wait_frame();
}
