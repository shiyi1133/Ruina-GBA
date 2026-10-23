#include "engine.h"
#include "balanced.h"
/* Original cell, scope, position, zoom, tone, opacity and timing data.
 * RM2000 plays one animation frame for two engine updates. Reference:
 * pinned EasyRPG Player battle_animation.cpp, GPL-3.0-or-later.
 * Transient rendering never changes Game or the ordinary SRAM layout. */
typedef struct {Image image;short x,y;} AnimationCellAsset;
typedef struct {u16 id;const short*cells;u16 count;} AnimationSheetAsset;
#include "battle_animation_assets.h"
static unsigned pending_targets;
static int previous[4];
volatile u32 animation_render_trace[16];/* id, frame, frames, cells, mask,
 * damage x/y/w/h, last/max hardware ticks, active; remaining reserved. */
void animation_targets(unsigned mask){pending_targets=mask;}
static int frames(LcfSpan animation){LcfReader r={field(animation,12),0,0};ru32 n;return lcf_number(&r,&n)?n*2:0;}
static const AnimationSheetAsset*sheet(int id){unsigned i;for(i=0;i<sizeof(animation_sheets)/sizeof(animation_sheets[0]);i++)if(animation_sheets[i].id==id)return animation_sheets+i;return 0;}
static const AnimationCellAsset*cell_asset(const AnimationSheetAsset*s,int id){unsigned i;if(!s)return 0;for(i=0;i<s->count;i++)if(s->cells[i*2]==id)return s->cells[i*2+1]>=0?animation_cells+s->cells[i*2+1]:0;return 0;}
static void bounds(int*b,int x,int y,int w,int h){int r=clamp(x+w,0,240),d=clamp(y+h,0,160);x=clamp(x,0,240);y=clamp(y,0,160);if(x>=r||y>=d)return;
 if(!b[2]){b[0]=x;b[1]=y;b[2]=r-x;b[3]=d-y;return;}
 if(r<b[0]+b[2])r=b[0]+b[2];if(d<b[1]+b[3])d=b[1]+b[3];if(x>b[0])x=b[0];if(y>b[1])y=b[1];b[0]=x;b[1]=y;b[2]=r-x;b[3]=d-y;
}
static void restore(void){if(previous[2]){if(!balanced_animation_background_restore(previous[0],previous[1],previous[2],previous[3])){video_clip(previous[0],previous[1],previous[2],previous[3]);draw_battle();video_clip(0,0,240,160);}memset(previous,0,sizeof(previous));}}
static void flash(EventAnimation*a,LcfSpan data,int*b,int wanted){LcfReader r={field(data,6),0,0};LcfSpan selected={0,0};ru32 n,j,key;int latest=-1,delta,power,k;if(!lcf_number(&r,&n))return;
 for(j=0;j<n;j++){LcfSpan t;int when;if(!lcf_next_entry(&r,&key,&t))break;when=(val(t,1,0)-1)*2;if(val(t,3,0)==wanted&&when<=a->frame&&when>=latest){selected=t;latest=when;}}
 if(!selected.data)return;delta=a->frame-latest;if(delta>10)return;power=clamp((7-(delta+1)/2)*val(selected,7,31)/6,0,31);
 if(wanted==2){balanced_animation_flash(0,0,240,160,val(selected,4,31),val(selected,5,31),val(selected,6,31),power);bounds(b,0,0,240,160);}
 else for(k=0;k<14;k++)if(a->reserved&(1U<<k)){int x,y,w,h;if(battle_animation_position(k,1,&x,&y,&w,&h)){
  balanced_animation_target_flash(battle_animation_image(k),x-w/2,y-h/2,w,h,val(selected,4,31),val(selected,5,31),val(selected,6,31),power);bounds(b,x-w/2,y-h/2,w,h);
 }}
}
static void draw_animation(EventAnimation*a,int*b){LcfSpan data=entry(db[19],a->id),f=entry(field(data,12),a->frame/2+1);LcfReader r={field(f,1),0,0};ru32 n,j,key;const AnimationSheetAsset*s=sheet(a->id);int scope=val(data,9,0),pos=val(data,10,1);
 flash(a,data,b,1);if(!s||!lcf_number(&r,&n))return;
 for(j=0;j<n;j++){LcfSpan c;const AnimationCellAsset*asset;int zoom,xx,yy,w,h,k;u8 tone[4];if(!lcf_next_entry(&r,&key,&c))break;if(!val(c,1,1))continue;asset=cell_asset(s,val(c,2,0));if(!asset)continue;
  zoom=clamp(val(c,5,100),0,2000);w=asset->image.width*zoom*3/400;h=asset->image.height*zoom*2/300;if(!w||!h)continue;
  xx=(val(c,3,0)*100+asset->x*zoom)*3/400;yy=(val(c,4,0)*100+asset->y*zoom)*2/300;
  for(k=0;k<4;k++)tone[k]=clamp(val(c,6+k,100),0,200);
  for(k=0;k<14;k++){int x=120,y=53,tw,th;
   if(!scope&&a->reserved){if(!(a->reserved&(1U<<k))||!battle_animation_position(k,pos,&x,&y,&tw,&th))continue;}
   balanced_animation_cell(&asset->image,x+xx,y+yy,w,h,clamp(val(c,10,0),0,100),tone);bounds(b,x+xx,y+yy,w,h);animation_render_trace[3]++;
   if(scope||!a->reserved)break;
  }
 }
 animation_render_trace[0]=a->id;animation_render_trace[1]=a->frame/2;animation_render_trace[4]=a->reserved;
}
int animation_start(int id){int i,duration;LcfSpan a=entry(db[19],id);if(!a.data){pending_targets=0;return 0;}duration=frames(a);for(i=0;i<4;i++)if(!game.animations[i].remaining)break;if(i==4)i=0;
 if(battle_active){int j,active=0;for(j=0;j<4;j++)active|=game.animations[j].remaining;if(!active){restore();balanced_menu_invalidate();draw_battle();balanced_animation_background_store();flip();}}
 game.animations[i]=(EventAnimation){id,0,duration,battle_active?pending_targets:0};pending_targets=0;if(duration&&!battle_active)presentation_cue(3,6);return duration;
}
void animations_tick(void){int i,redraw=0,active=0,b[4]={0};unsigned start=video_ticks();
 for(i=0;i<4;i++){EventAnimation*a=game.animations+i;if(!a->remaining)continue;active=1;if(!(a->frame&1)){
  LcfSpan timings=field(entry(db[19],a->id),6);LcfReader r={timings,0,0};ru32 n,j,key;redraw=1;
  if(timings.data&&lcf_number(&r,&n))for(j=0;j<n;j++){LcfSpan t,s;int p[3];if(!lcf_next_entry(&r,&key,&t)){fault(9033);break;}if(val(t,1,0)!=a->frame/2+1)continue;s=field(t,2);p[0]=val(s,3,100);p[1]=val(s,4,100);p[2]=val(s,5,50);audio_command(RM2K_PlaySound,field(s,1),p);}
 }}
 if(battle_active&&(redraw||(!active&&previous[2]))){restore();animation_render_trace[12]=(u16)(video_ticks()-start);for(i=0;i<4;i++)if(game.animations[i].remaining)draw_animation(game.animations+i,b);animation_render_trace[13]=(u16)(video_ticks()-start);for(i=0;i<4;i++)if(game.animations[i].remaining)flash(game.animations+i,entry(db[19],game.animations[i].id),b,2);memcpy(previous,b,sizeof(b));flip();animation_render_trace[2]++;
  for(i=0;i<4;i++)animation_render_trace[5+i]=b[i];animation_render_trace[9]=(u16)(video_ticks()-start);if(animation_render_trace[9]>animation_render_trace[10])animation_render_trace[10]=animation_render_trace[9];
 }
 if(!battle_active)memset(previous,0,sizeof(previous));animation_render_trace[11]=active;
 for(i=0;i<4;i++){EventAnimation*a=game.animations+i;if(a->remaining){a->frame++;a->remaining--;}}
}
void animation_battle(int id){int n;n=animation_start(id);while(n--&&!halt_code)wait_frame();if(battle_active&&previous[2]){restore();flip();}}
