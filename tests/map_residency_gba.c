#include "game.h"
#include "assets.h"
static int stage;
static void show(int x,int y){
 game.pan_locked=1;game.camera_lock_x=x-40;game.camera_lock_y=y-40;parallel_revision++;
#ifdef RESIDENCY_REFERENCE_FULL
 world_render_invalidate();
#endif
 world_redraw();debug_state[14]=++stage;while(!(wait_frame()&KEY_A)){}
}
static void hide_pictures(void){int i;for(i=1;i<=MAX_PICTURE;i++)game.pictures[i].image=-1;}
static PictureState image_state(int image,int x,int y,int flags){PictureState p;memset(&p,0,sizeof(p));p.image=image;p.x=p.target_x=x;p.y=p.target_y=y;p.zoom=p.target_zoom=100;p.flags=flags;p.red=p.green=p.blue=p.saturation=100;return p;}
int main(void){
 PictureState hud;
 video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();audio_restore();depth=0;engine_clock_paused=1;scene_image=-1;game.selected=0;hud=game.pictures[20];
 hide_pictures();show(0,0);show(16,0);show(0,0);
 set_map(33,0,0);hide_pictures();show(0,0);show(16,8);show(0,0);
 /* Cross both independent VRAM ring periods, then revisit earlier pixels. */
 show(256,256);show(384,512);show(0,0);show(256,256);show(0,0);
 /* Erase an anchored picture while its old pixels are off screen but still
  * resident in the spare rows. Returning must not resurrect its old copy. */
 game.pictures[4]=image_state(hud.image,images[hud.image].width/2,images[hud.image].height/2,3);show(0,0);show(0,24);
 game.pictures[4].image=-1;show(0,24);show(0,0);
 /* First two small pictures use OBJ. The third changes from baked artwork
  * into OBJ when the first is removed, then moves away from its old pixels. */
 hide_pictures();game.pictures[1]=hud;game.pictures[1].x=40;game.pictures[1].y=40;game.pictures[2]=hud;game.pictures[2].x=130;game.pictures[2].y=80;game.pictures[3]=hud;game.pictures[3].x=220;game.pictures[3].y=140;show(0,0);
 game.pictures[1].image=-1;show(0,0);game.pictures[3].x+=50;show(0,0);game.pictures[1]=hud;show(0,0);
 /* Nonuniform screen-fixed artwork must remain fixed as the map scrolls. */
 hide_pictures();game.pictures[4]=image_state(IMG_HERO0,140,100,0);show(0,0);show(16,8);show(0,0);
 hide_pictures();tile_substitute(0,1,3);show(256,256);show(0,0);
 /* A fresh map scene must reclaim its OBJ palette/texture cache. */
 set_map(23,15,12);hide_pictures();show(0,0);
 debug_state[14]=999;for(;;)wait_frame();
}
