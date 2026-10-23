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
static unsigned animation_clock[4];
static int animation_clock_known[4],animation_last_draw[4],animation_last_sound[4],animation_wait_slot;
static int animation_full_frames;
volatile u32 animation_timing_debug[8];/* id, omitted transitions, drawings,
 * original timing events, duration ticks, start clock, last clock, mode */
volatile u32 animation_sound_order[32];
volatile u32 animation_presented_trace[4];/* seqlock, id, source frame, hardware clock */
void animation_playback_mode(int full_frames){animation_full_frames=full_frames!=0;}
int animation_playback_full(void){return animation_full_frames;}
/* Four concurrent animations share immutable records. Do not rescan the
 * entire original database for the same record at every sound/draw pass. */
static LcfSpan record_database,record_values[4];
static u16 record_ids[4];
static unsigned record_next;
static LcfSpan animation_data(int id){unsigned i;
 if(record_database.data!=db[19].data||record_database.size!=db[19].size){record_database=db[19];memset(record_ids,0,sizeof(record_ids));memset(record_values,0,sizeof(record_values));record_next=0;}
 if(id>0)for(i=0;i<4;i++)if(record_ids[i]==id)return record_values[i];
 i=record_next++&3;record_ids[i]=id;record_values[i]=entry(db[19],id);return record_values[i];
}
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
typedef struct {int r,g,b,power;} AnimationFlash;
static int selected_flash(EventAnimation*a,LcfSpan data,int wanted,AnimationFlash*out){LcfReader r={field(data,6),0,0};LcfSpan selected={0,0};ru32 n,j,key;int latest=-1,delta,power;if(!lcf_number(&r,&n))return 0;
 for(j=0;j<n;j++){LcfSpan t;int when;if(!lcf_next_entry(&r,&key,&t))break;when=(val(t,1,0)-1)*2;if(val(t,3,0)==wanted&&when<=a->frame&&when>=latest){selected=t;latest=when;}}
 if(!selected.data)return 0;delta=a->frame-latest;if(delta>10)return 0;power=clamp((7-(delta+1)/2)*val(selected,7,31)/6,0,31);if(!power)return 0;
 *out=(AnimationFlash){val(selected,4,31),val(selected,5,31),val(selected,6,31),power};return 1;
}
static void flash(EventAnimation*a,LcfSpan data,int*b,int wanted){AnimationFlash f;int k;if(!selected_flash(a,data,wanted,&f))return;
 if(wanted==2){balanced_animation_flash(0,0,240,160,f.r,f.g,f.b,f.power);bounds(b,0,0,240,160);}
 else for(k=0;k<14;k++)if(a->reserved&(1U<<k)){int x,y,w,h;if(battle_animation_position(k,1,&x,&y,&w,&h)){
  balanced_animation_target_flash(battle_animation_image(k),x-w/2,y-h/2,w,h,f.r,f.g,f.b,f.power);bounds(b,x-w/2,y-h/2,w,h);
 }}
}
static int opaque_cells(EventAnimation*a,LcfSpan data){LcfSpan f=entry(field(data,12),a->frame/2+1);LcfReader r={field(f,1),0,0};ru32 n,j,key;
 if(!lcf_number(&r,&n))return 1;
 for(j=0;j<n;j++){LcfSpan c;int opacity;if(!lcf_next_entry(&r,&key,&c))return 0;if(!val(c,1,1))continue;opacity=clamp(val(c,10,0),0,100);if(opacity&&opacity<100)return 0;}
 return 1;
}
static void draw_animation(EventAnimation*a,int*b){LcfSpan data=animation_data(a->id),f=entry(field(data,12),a->frame/2+1);LcfReader r={field(f,1),0,0};ru32 n,j,key;const AnimationSheetAsset*s=sheet(a->id);int scope=val(data,9,0),pos=val(data,10,1);
 flash(a,data,b,1);
 if(scope){int baked[4];if(animation_baked_draw(a->id,a->frame/2,baked)){bounds(b,baked[0],baked[1],baked[2],baked[3]);animation_render_trace[0]=a->id;animation_render_trace[1]=a->frame/2;animation_render_trace[4]=a->reserved;return;}}
 if(!s||!lcf_number(&r,&n))return;
 for(j=0;j<n;j++){LcfSpan c;const AnimationCellAsset*asset;int zoom,xx,yy,w,h,k,opacity;u8 tone[4];if(!lcf_next_entry(&r,&key,&c))break;if(!val(c,1,1))continue;asset=cell_asset(s,val(c,2,0));if(!asset)continue;
  opacity=clamp(val(c,10,0),0,100);if(opacity>=100)continue;zoom=clamp(val(c,5,100),0,2000);w=asset->image.width*zoom*3/400;h=asset->image.height*zoom*2/300;if(!w||!h)continue;
  xx=(val(c,3,0)*100+asset->x*zoom)*3/400;yy=(val(c,4,0)*100+asset->y*zoom)*2/300;
  for(k=0;k<4;k++)tone[k]=clamp(val(c,6+k,100),0,200);
  for(k=0;k<14;k++){int x=120,y=53,tw,th;
   if(!scope&&a->reserved){if(!(a->reserved&(1U<<k))||!battle_animation_position(k,pos,&x,&y,&tw,&th))continue;}
   balanced_animation_cell(&asset->image,x+xx,y+yy,w,h,opacity,tone);bounds(b,x+xx,y+yy,w,h);animation_render_trace[3]++;
   if(scope||!a->reserved)break;
  }
 }
 animation_render_trace[0]=a->id;animation_render_trace[1]=a->frame/2;animation_render_trace[4]=a->reserved;
}
int animation_start(int id){int i,duration;LcfSpan a=animation_data(id);if(!a.data){pending_targets=0;return 0;}duration=frames(a);for(i=0;i<4;i++)if(!game.animations[i].remaining)break;if(i==4)i=0;
 if(battle_active){int j,active=0;for(j=0;j<4;j++)active|=game.animations[j].remaining;if(!active){restore();balanced_menu_invalidate();draw_battle();balanced_animation_background_store();flip();}}
 game.animations[i]=(EventAnimation){id,0,duration,battle_active?pending_targets:0};animation_clock[i]=video_clock();animation_clock_known[i]=1;animation_last_draw[i]=animation_last_sound[i]=-1;animation_wait_slot=i;
 memset((void*)animation_timing_debug,0,sizeof(animation_timing_debug));animation_timing_debug[0]=id;animation_timing_debug[4]=duration;animation_timing_debug[5]=animation_clock[i];animation_timing_debug[7]=animation_full_frames;
 memset((void*)animation_sound_order,0,sizeof(animation_sound_order));
 pending_targets=0;if(duration&&!battle_active)presentation_cue(3,6);return duration;
}
static void animation_sounds(EventAnimation*a,int first,int last){
 LcfSpan timings=field(animation_data(a->id),6);int after=first;
 if(last<=first)return;
 /* Find successive due frame numbers, preserving chronological order even
  * if an imported timing array happens to be stored out of order. */
 for(;;){LcfReader r={timings,0,0};ru32 n,j,key;int next=last+1;if(!lcf_number(&r,&n))return;
  for(j=0;j<n;j++){LcfSpan t;int when;if(!lcf_next_entry(&r,&key,&t)){fault(9033);return;}when=val(t,1,0)-1;if(when>after&&when<next)next=when;}
  if(next>last)return;r=(LcfReader){timings,0,0};if(!lcf_number(&r,&n))return;
  for(j=0;j<n;j++){LcfSpan t,s;int p[3];if(!lcf_next_entry(&r,&key,&t)){fault(9033);return;}if(val(t,1,0)-1!=next)continue;s=field(t,2);p[0]=val(s,3,100);p[1]=val(s,4,100);p[2]=val(s,5,50);audio_command(RM2K_PlaySound,field(s,1),p);if(animation_timing_debug[3]<32)animation_sound_order[animation_timing_debug[3]]=(next<<16)|(key&65535);animation_timing_debug[3]++;}
  after=next;
 }
}
void animations_tick(void){int i,redraw=0,active=0,b[4]={0};unsigned start=video_ticks();
 for(i=0;i<4;i++){EventAnimation*a=game.animations+i;int paced=battle_active&&!animation_full_frames&&!engine_clock_paused;if(!a->remaining){animation_clock_known[i]=0;continue;}
  if(paced){unsigned now=video_clock(),duration=a->frame+a->remaining,elapsed;int frame;
   if(!animation_clock_known[i]){animation_clock_known[i]=1;animation_clock[i]=now-a->frame;animation_last_draw[i]=animation_last_sound[i]=a->frame/2-1;}
   elapsed=now-animation_clock[i];frame=elapsed/2;if(frame>=(int)(duration/2))frame=(duration-1)/2;
   animation_sounds(a,animation_last_sound[i],frame);animation_last_sound[i]=frame;animation_timing_debug[6]=now;
   if(elapsed>=duration&&animation_last_draw[i]>=frame){a->remaining=0;animation_clock_known[i]=0;continue;}
   a->frame=frame*2;a->remaining=duration-a->frame;
   if(frame!=animation_last_draw[i]){if(frame>animation_last_draw[i]+1)animation_timing_debug[1]+=frame-animation_last_draw[i]-1;animation_last_draw[i]=frame;redraw=1;}
  }else if(!(a->frame&1)){redraw=1;animation_sounds(a,a->frame/2-1,a->frame/2);}
  active=1;
 }
 if(battle_active&&(redraw||(!active&&previous[2]))){int opaque=-1,fused=0,count=0,last=-1;AnimationFlash f;
  /* A fully opaque screen flash hides the complete underlay and every cell.
   * Keep the original sound and frame sequence, but omit invisible drawing. */
  for(i=0;i<4;i++)if(game.animations[i].remaining){last=i;count++;if(selected_flash(game.animations+i,animation_data(game.animations[i].id),2,&f)&&f.power==31)opaque=i;}
  {u32 mask[3];if(count==1&&animation_baked_mask(game.animations[last].id,game.animations[last].frame/2,mask))balanced_animation_mask(mask);else balanced_animation_mask(0);}
  if(opaque<0&&count==1){EventAnimation*a=game.animations+last;LcfSpan data=animation_data(a->id);
   if(selected_flash(a,data,2,&f)&&opaque_cells(a,data)){
    balanced_animation_palette_flash(f.r,f.g,f.b,f.power);
    if(!balanced_animation_background_restore(0,0,240,160)){video_clip(0,0,240,160);draw_battle();balanced_animation_flash(0,0,240,160,f.r,f.g,f.b,f.power);}
    memset(previous,0,sizeof(previous));bounds(b,0,0,240,160);fused=1;
   }
  }
  if(opaque<0&&!fused)restore();animation_render_trace[12]=(u16)(video_ticks()-start);
  for(i=0;i<4;i++)if(game.animations[i].remaining){EventAnimation*a=game.animations+i;if(opaque<0)draw_animation(a,b);else{animation_render_trace[0]=a->id;animation_render_trace[1]=a->frame/2;animation_render_trace[4]=a->reserved;}}
  if(fused)balanced_animation_palette_reset();animation_render_trace[13]=(u16)(video_ticks()-start);if(!fused)for(i=opaque<0?0:opaque;i<4;i++)if(game.animations[i].remaining)flash(game.animations+i,animation_data(game.animations[i].id),b,2);memcpy(previous,b,sizeof(b));flip();if(active){animation_render_trace[2]++;animation_timing_debug[2]++;animation_presented_trace[0]++;animation_presented_trace[1]=animation_render_trace[0];animation_presented_trace[2]=animation_render_trace[1];animation_presented_trace[3]=video_clock();animation_presented_trace[0]++;}
  balanced_animation_mask(0);for(i=0;i<4;i++)animation_render_trace[5+i]=b[i];animation_render_trace[9]=(u16)(video_ticks()-start);if(animation_render_trace[9]>animation_render_trace[10])animation_render_trace[10]=animation_render_trace[9];
 }
 if(!battle_active)memset(previous,0,sizeof(previous));animation_render_trace[11]=active;
 for(i=0;i<4;i++){EventAnimation*a=game.animations+i;if(a->remaining){a->frame++;a->remaining--;}}
}
void animation_battle(int id){int n=animation_start(id),slot=animation_wait_slot;if(n)while(game.animations[slot].remaining&&game.animations[slot].id==id&&!halt_code)wait_frame();if(battle_active&&previous[2]){restore();flip();}}
