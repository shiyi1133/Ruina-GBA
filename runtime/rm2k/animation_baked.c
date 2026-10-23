#include "balanced.h"
typedef struct {u32 key;const u8*rectangles;const u16*palette;u16 count,colors;u8 bounds[4];u32 coverage[3];} ScreenAnimationFrame;
#include "screen_animation_assets.h"
int animation_baked_mask(int id,int frame,u32*out){u32 key=((u32)id<<16)|frame;unsigned lo=0,hi=sizeof(screen_animation_frames)/sizeof(screen_animation_frames[0]),i;while(lo<hi){unsigned at=(lo+hi)/2;if(screen_animation_frames[at].key<key)lo=at+1;else hi=at;}if(lo>=sizeof(screen_animation_frames)/sizeof(screen_animation_frames[0])||screen_animation_frames[lo].key!=key)return 0;for(i=0;i<3;i++)out[i]=screen_animation_frames[lo].coverage[i];return 1;}
int animation_baked_draw(int id,int frame,int*out){
 u32 key=((u32)id<<16)|frame;unsigned lo=0,hi=sizeof(screen_animation_frames)/sizeof(screen_animation_frames[0]),i;
 while(lo<hi){unsigned at=(lo+hi)/2;if(screen_animation_frames[at].key<key)lo=at+1;else hi=at;}
 if(lo>=sizeof(screen_animation_frames)/sizeof(screen_animation_frames[0])||screen_animation_frames[lo].key!=key)return 0;
 {const ScreenAnimationFrame*f=screen_animation_frames+lo;balanced_animation_rectangles(f->rectangles,f->count,f->palette,f->colors,f->bounds);for(i=0;i<4;i++)out[i]=f->bounds[i];}return 1;
}
