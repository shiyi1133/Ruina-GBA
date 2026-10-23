#include "gba_hw.h"
/* Ruina-specific display and chapter boot adapter. No recipes or class rules. */
#include "game.h"
#include "assets.h"
#include "balanced.h"
int scene_image=-1,current_face=-1,avatar_mode,chapter_notice;
static int balanced_image_id(int id){static const short aliases[][2]={{5,506},{4,499},{160,497},{161,512},{162,491},{163,509},{164,514}};unsigned i;for(i=0;i<sizeof(aliases)/sizeof(aliases[0]);i++)if(aliases[i][0]==id)return aliases[i][1];return id;}

void render_picture_show(LcfSpan name,const int*p){pictures_show(name,p);scene_image=-1;if(p[0]==10&&game.map==RUINA_START_MAP)avatar_mode=1;}
void render_picture_erase(int slot){if(slot>0&&slot<=MAX_PICTURE){if(game.pictures[slot].image>=0)parallel_revision++;game.pictures[slot].image=-1;}if(slot==10)avatar_mode=0;}
int battle_background_image(void){return game.battle_backdrop>=0?game.battle_backdrop:IMG_BATTLE_BG;}
int choice_header_height(int count){return avatar_mode&&game.map==RUINA_START_MAP&&count==4?56:40;}
void render_choice_header(int count){int i;if(choice_header_height(count)==56)for(i=0;i<4;i++)portrait(IMG_HERO0+(sw(2)?0:8)+i,7+i*59,1);}
void init_game(void){
    int i;u32 seed=0x5275696eU^((u32)REG16(0x04000108)<<16)^REG16(0x04000006)^audio_debug[0];
    engine_init(seed);acceptance_boost_arm();current_face=-1;avatar_mode=0;scene_image=IMG_FOREST;
    audio_reset();audio_default_sounds();
    for(i=0;i<8;i++){LcfSpan music=field(db[22],32+i);int p[5]={i,val(music,2,0),val(music,3,100),val(music,4,100),val(music,5,50)};audio_command(RM2K_ChangeSystemBGM,field(music,1),p);}
    set_map(RUINA_START_MAP,0,0);scene_image=IMG_FOREST;push_event(RUINA_START_EVENT,1);
}
static int scene_palette_image(int background){
 int chosen=background,i;
 if(chosen<0&&game.map>0&&game.map<RM2K_MAP_COUNT){LcfSpan chip=entry(db[20],val(map_data(game.map),1,1));chosen=resource_image(2,field(chip,2));}
 /* A fully opaque illustration that covers the view owns the palette. This
  * prevents a title/story image being forced into an unrelated map palette.
  * Uniform fog masks leave the underlying scene's palette alone. */
 for(i=1;i<=MAX_PICTURE;i++){
  const PictureState*p=game.pictures+i;int w,h,x,y,native;
  if(p->image<0||!p->zoom||p->transparency||p->flags&2||images[p->image].encoding==7)continue;
  w=images[p->image].width*p->zoom/100;h=images[p->image].height*p->zoom/100;x=p->x-w/2;y=p->y-h/2;native=world_native_map()&&(p->flags&1);
  if(p->flags&1){x-=(world_native_map()?world_view_x():map_display_x())-p->map_x;y-=(world_native_map()?world_view_y():map_display_y())-p->map_y;}
  if(!native){x=x*3/4;y=y*2/3;w=w*3/4;h=h*2/3;}
  if(x<=0&&y<=0&&x+w>=240&&y+h>=160)chosen=p->image;
 }return chosen;
}
void draw_background(void){
    int id=game.panorama>=0?game.panorama:game.panorama==-2?-1:game.map>=0&&game.map<RM2K_MAP_COUNT?map_image_ids[game.map]:-1;
    if(battle_active){video_scene_palette(battle_background_image());draw_battle();return;}
    if(scene_image>=0)id=scene_image;
    video_scene_palette(scene_palette_image(id));
    if(game.screen_hidden){clear(14);return;}
    clear(balanced_rgb_mode()?14:0);if(id<0)return;
    if(!balanced_rgb_mode()){
        if(world_native_map()&&scene_image<0)picture_region_scaled(id,0,0,world_view_x(),world_view_y(),240,160,240,160,0,0,game.screen_tone);
        else picture_region_scaled(id,0,0,scene_image<0?map_display_x():0,scene_image<0?map_display_y():0,scene_image>=0?images[id].width:320,scene_image>=0?images[id].height:240,240,160,0,0,game.screen_tone);
    }else if(id==IMG_TITLE)picture(IMG_TITLE,0,0,0,0,240,160,0);
    else if(world_native_map()&&scene_image<0)picture_region_scaled(id,0,0,world_view_x(),world_view_y(),240,160,240,160,0,0,game.screen_tone);
    else{int native=game.map==RUINA_START_MAP,x,y=0,w,h;id=balanced_image_id(id);w=images[id].width;h=images[id].height;x=(320-w)/2;
        if(native)x-=40;else{x=13+x*2/3;w=w*2/3;h=h*2/3;}
        picture_region_scaled(id,x,y,0,0,images[id].width,images[id].height,w,h,0,0,game.screen_tone);
    }
}
void draw_scene(void){balanced_menu_invalidate();if(balanced_native_ui_begin())return;draw_background();if(!battle_active&&!game.screen_hidden)pictures_draw();}

static u32 stamp_value(u32 hash,int value){return(hash^(u32)value)*16777619U;}
u32 balanced_scene_stamp(void){
    int i;u32 h=2166136261U;
    if(battle_active)h=stamp_value(h,battle_render_stamp());
    int values[]={scene_image,game.map,game.panorama,game.screen_hidden,game.weather,(int)balanced_surface_epoch,game.map>0?world_view_x():0,game.map>0?world_view_y():0,avatar_mode,sw(2)};
    for(i=0;i<(int)(sizeof(values)/sizeof(values[0]));i++)h=stamp_value(h,values[i]);
    for(i=0;i<4;i++)h=stamp_value(h,game.screen_tone[i]);
    /* A timer, switch or variable revision does not imply changed pixels.
     * Hash only fields that this renderer actually projects into the scene. */
    for(i=1;i<=MAX_PICTURE;i++){PictureState*s=game.pictures+i;
        if(s->image<0||!s->zoom||s->transparency>=100)continue;
        h=stamp_value(h,i);h=stamp_value(h,s->image);h=stamp_value(h,s->x);h=stamp_value(h,s->y);h=stamp_value(h,s->zoom);h=stamp_value(h,s->transparency);h=stamp_value(h,s->flags);
        if(s->flags&1){h=stamp_value(h,s->map_x);h=stamp_value(h,s->map_y);}
        h=stamp_value(h,s->red);h=stamp_value(h,s->green);h=stamp_value(h,s->blue);h=stamp_value(h,s->saturation);
    }
    return h;
}
