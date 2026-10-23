#include "engine.h"
/* Retain original animation length and timed SFX. Raster battle effects use
 * the reduced GBA presentation. Pinned Player battle_animation.cpp is the
 * reference: one animation frame spans two game updates. */
static int frames(LcfSpan animation){LcfReader r={field(animation,12),0,0};ru32 n;return lcf_number(&r,&n)?n*2:0;}
int animation_start(int id){int i,duration;LcfSpan a=entry(db[19],id);if(!a.data)return 0;duration=frames(a);for(i=0;i<4;i++)if(!game.animations[i].remaining)break;if(i==4)i=0;game.animations[i]=(EventAnimation){id,0,duration,0};if(duration)presentation_cue(3,6);return duration;}
void animations_tick(void){int i;for(i=0;i<4;i++){EventAnimation*a=game.animations+i;if(!a->remaining)continue;if(!(a->frame&1)){LcfSpan timings=field(entry(db[19],a->id),6);LcfReader r={timings,0,0};ru32 n,j,key;if(timings.data&&lcf_number(&r,&n))for(j=0;j<n;j++){LcfSpan t,s;int p[3];if(!lcf_next_entry(&r,&key,&t)){fault(9033);break;}if(val(t,1,0)!=a->frame/2+1)continue;s=field(t,2);p[0]=val(s,3,100);p[1]=val(s,4,100);p[2]=val(s,5,50);audio_command(RM2K_PlaySound,field(s,1),p);}}a->frame++;a->remaining--;}}
void animation_battle(int id){int n;if(battle_active){draw_battle();flip();}n=animation_start(id);while(n--&&!halt_code)wait_frame();}
