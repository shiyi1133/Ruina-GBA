#include "game.h"
#include "assets.h"
/* Controlled cache/reference comparison using genuine ordinary-save data. */
static void show(int stage){
#ifdef SCROLL_REFERENCE_FULL
 world_render_invalidate();
#endif
 world_redraw();debug_state[14]=stage;
 while(!(wait_frame()&KEY_A)){}
}
int main(void){
 video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();
 audio_restore();depth=0;engine_clock_paused=1;scene_image=-1;game.selected=0;
 show(1);
 event_relocate(10001,10,8);show(2);
 event_relocate(10001,9,8);show(3);
 event_relocate(10001,10,8);show(4);
 event_relocate(10001,10,9);show(5);
 event_relocate(10001,4,4);show(6);
 event_relocate(10001,18,14);show(7);
 event_relocate(10001,10,8);show(8);
 event_set_direction(10001,6);show(9);
 game.pictures[25].x=game.pictures[25].target_x=80;show(10);
 draw_scene();box(20,30,200,70,11);draw_text(30,40,"Menu owns VRAM temporarily",1,180);flip();
 debug_state[14]=11;while(!(wait_frame()&KEY_A)){}
 show(12);
 game.pictures[30].transparency=game.pictures[30].target_transparency=50;parallel_revision++;show(13);
 tile_substitute(0,142,100);show(14);
 set_map(3,15,12);show(15);
 for(;;)wait_frame();
}
