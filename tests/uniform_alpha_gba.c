#include "game.h"
#include "assets.h"
/* Actual palette compositing over all 256 destination colors. */
static void show(int stage,int alpha,int image,const u8*tone){
 int i;clear(14);
 for(i=0;i<256;i++)box(i%16*15,i/16*10,15,10,i);
 if(alpha>=0)picture_region_scaled(image,0,0,0,0,images[image].width,images[image].height,240,160,1,alpha,tone);
 flip();debug_state[14]=stage;while(!(wait_frame()&KEY_A)){}
}
int main(void){
 static const u8 tone[4]={80,110,90,50};
 video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
 audio_music((Music){0,100,100,50},0);
 show(1,-1,446,0);show(2,70,446,0);show(3,25,446,0);
 show(4,0,446,0);show(5,100,446,0);show(6,70,IMG_FOREST,tone);
 for(;;)wait_frame();
}
