#include "game.h"
#include "assets.h"
static void hold(int n){debug_state[14]=n;while(!(wait_frame()&KEY_A)){} }
int main(void){
 int i,npc;
 video_init();audio_init();init_game();depth=0;scene_image=IMG_TITLE;
 audio_music((Music){0,100,100,50},0);
 clear(11);portrait(IMG_HERO0,8,20);flip();hold(1);
 clear(11);for(i=0;i<4;i++)portrait(IMG_HERO0+i,7+i*59,1);flip();hold(2);
 npc=face_image(field(actor_data[6],15),val(actor_data[6],16,0));debug_state[13]=npc;
 clear(11);portrait(npc,8,20);flip();hold(3);
 clear(11);flip();hold(4);
 current_face=npc;debug_state[14]=5;describe("原始头像与对白共同显示。头像不再缩小到三十六像素，也不再与背景共用十六色减色。");
 for(;;)wait_frame();
}
