#include "balanced.h"
#include "engine.h"
/* Original picture centers, coordinate operands, ordered slots and durations.
 * The backend reduces raster detail and uses uniform palette alpha.
 * Rotation/wave flags retain their static artwork. Position and zoom retain
 * their original interactive timing; opacity and screen-tone animations snap
 * to their endpoints and redraw behind black, per the GBA visual policy. */
static int operand_value(int mode,int n){return mode?variable(n):n;}
void pictures_show(LcfSpan name,const int*p){PictureState old,*s;int image=resource_image(0,name);if(p[0]<1||p[0]>MAX_PICTURE){fault(9030);return;}s=game.pictures+p[0];old=*s;memset(s,0,sizeof(*s));s->image=image;s->x=s->target_x=operand_value(p[1],p[2]);s->y=s->target_y=operand_value(p[1],p[3]);s->zoom=s->target_zoom=clamp(p[5],0,2000);s->transparency=s->target_transparency=clamp(p[6],0,100);s->flags=(p[4]?1:0)|(p[7]?2:0);s->map_x=map_display_x();s->map_y=map_display_y();s->red=p[8];s->green=p[9];s->blue=p[10];s->saturation=p[11];s->effect=p[12];s->power=p[13];{unsigned i;for(i=0;i<sizeof(*s);i++)if(((const u8*)&old)[i]!=((const u8*)s)[i]){parallel_revision++;break;}}if(image<0&&name.size)fault(9031);}
int pictures_move(const int*p){
 PictureState*s;int opacity_cut,frames=p[14]>0?p[14]*6:0;
 if(p[0]<1||p[0]>MAX_PICTURE){fault(9030);return 0;}
 s=game.pictures+p[0];if(s->image<0)return 0;
 s->target_x=operand_value(p[1],p[2]);s->target_y=operand_value(p[1],p[3]);
 s->target_zoom=clamp(p[5],0,2000);s->target_transparency=clamp(p[6],0,100);
 opacity_cut=frames&&s->transparency!=s->target_transparency;
 s->transparency=s->target_transparency;
 s->red=p[8];s->green=p[9];s->blue=p[10];s->saturation=p[11];s->effect=p[12];s->power=p[13];
 /* Alpha-only transitions have no residual animation wait. Real picture
  * movement/zoom can drive interfaces, so retain those durations. */
 if(s->x==s->target_x&&s->y==s->target_y&&s->zoom==s->target_zoom)frames=0;
 s->remaining=frames;if(!frames){s->x=s->target_x;s->y=s->target_y;s->zoom=s->target_zoom;}
 parallel_revision++;
 if(opacity_cut)presentation_black_redraw();
 return p[15]?frames:0;
}
void pictures_tick(void){int i;if(game.tone_remaining){/* Resume old saves at the endpoint, never restart a removed fade. */for(i=0;i<4;i++)game.screen_tone[i]=game.tone_target[i];game.tone_remaining=0;parallel_revision++;}if(game.pan_x!=game.pan_target_x||game.pan_y!=game.pan_target_y){int step=2<<game.pan_speed,dx=game.pan_target_x-game.pan_x,dy=game.pan_target_y-game.pan_y;game.pan_x+=clamp(dx,-step,step);game.pan_y+=clamp(dy,-step,step);parallel_revision++;}for(i=1;i<=MAX_PICTURE;i++){PictureState*s=game.pictures+i;int n=s->remaining;if(s->image<0||!n)continue;s->x=(s->x*(n-1)+s->target_x)/n;s->y=(s->y*(n-1)+s->target_y)/n;s->zoom=(s->zoom*(n-1)+s->target_zoom)/n;s->transparency=s->target_transparency;s->remaining--;parallel_revision++;}}
void legacy_pictures_draw(void){int i;for(i=1;i<=MAX_PICTURE;i++){PictureState*s=game.pictures+i;int w,h,x,y;u8 tone[4];if(s->image<0||!s->zoom||s->transparency>=100||(world_cached_background()&&world_picture_is_hud(i)))continue;w=images[s->image].width*s->zoom/100;h=images[s->image].height*s->zoom/100;x=s->x-w/2;y=s->y-h/2;if(s->flags&1){x-=(world_native_map()?world_view_x():map_display_x())-s->map_x;y-=(world_native_map()?world_view_y():map_display_y())-s->map_y;}tone[0]=s->red;tone[1]=s->green;tone[2]=s->blue;tone[3]=s->saturation;if(world_native_map()&&(s->flags&1))picture_region_scaled(s->image,x,y,0,0,images[s->image].width,images[s->image].height,w,h,s->flags&2,s->transparency,tone);else picture_region_scaled(s->image,x*3/4,y*2/3,0,0,images[s->image].width,images[s->image].height,w*3/4,h*2/3,s->flags&2,s->transparency,tone);}presentation_weather();}
void render_screen_command(int code,LcfSpan name,const int*p){int i;if(code==RM2K_ChangePBG){game.panorama=name.size?resource_image(1,name):-2;if(name.size&&game.panorama<0)fault(9032);}
 else if(code==RM2K_TintScreen){int changed=0;game.tone_remaining=0;for(i=0;i<4;i++){int target=clamp(p[i],0,200);if(game.screen_tone[i]!=target)changed=1;game.screen_tone[i]=game.tone_target[i]=target;}parallel_revision++;if(changed)presentation_black_redraw();return;}
 else if(code==RM2K_PlayerVisibility){game.player_hidden=p[0]==0;game.reserved&=~2;}
 else if(code==RM2K_PanScreen){if(p[0]<2){if(p[0]==0){game.camera_lock_x=map_display_x()-game.pan_x/16;game.camera_lock_y=map_display_y()-game.pan_y/16;}game.pan_locked=p[0]==0;}else {int d=p[1],amount=p[2]*256;game.pan_speed=clamp(p[3],1,6);if(p[0]==3)game.pan_target_x=game.pan_target_y=0;else {game.pan_target_x+=d==1?amount:d==3?-amount:0;game.pan_target_y+=d==2?amount:d==0?-amount:0;}}}
 parallel_revision++;
}

int render_screen_wait(int code,const int*p){if(code==RM2K_TintScreen)return 0;if(code==RM2K_PanScreen&&p[0]>=2&&p[4]){int dx=game.pan_target_x-game.pan_x,dy=game.pan_target_y-game.pan_y,step=2<<game.pan_speed;if(dx<0)dx=-dx;if(dy<0)dy=-dy;if(dy>dx)dx=dy;return (dx+step-1)/step;}return 0;}

void pictures_draw(void){int i;
    if(!balanced_rgb_mode()){legacy_pictures_draw();return;}
    for(i=1;i<=MAX_PICTURE;i++){
        PictureState*s=game.pictures+i;int w,h,x,y;u8 tone[4];
        if(s->image<0||!s->zoom||s->transparency>=100)continue;
        w=images[s->image].width*s->zoom/100;h=images[s->image].height*s->zoom/100;x=s->x-w/2;y=s->y-h/2;
        if(s->flags&1){x-=(world_native_map()?world_view_x():map_display_x())-s->map_x;y-=(world_native_map()?world_view_y():map_display_y())-s->map_y;}
        tone[0]=s->red;tone[1]=s->green;tone[2]=s->blue;tone[3]=s->saturation;
        if(!(world_native_map()&&(s->flags&1))){if(game.map==RUINA_START_MAP)x-=40;else{x=13+x*2/3;y=y*2/3;w=w*2/3;h=h*2/3;}}
        picture_region_scaled(s->image,x,y,0,0,images[s->image].width,images[s->image].height,w,h,s->flags&2,s->transparency,tone);
    }presentation_weather();
}
