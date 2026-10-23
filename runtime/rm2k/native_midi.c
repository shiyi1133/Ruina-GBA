/* Fixed-point ROM-sample MIDI synthesis for ARM7. Envelope, pitch, gain,
 * sustain, exclusive groups and note-off ordering follow TinySoundFont 0.9,
 * MIT, Copyright (C) 2017-2025 Bernhard Schelling. The upstream source and
 * license are preserved in research/reference/tsf.h. No floating point or
 * dynamic allocation is used by this runtime.
 */
#ifndef RUINA_LIGHT_MUSIC
#include "native_midi.h"
#ifndef NATIVE_VOICE_LIMIT
#define NATIVE_VOICE_LIMIT 160
#endif
#define VOICE_LIMIT NATIVE_VOICE_LIMIT
#define ONE (1<<24)
#ifdef __arm__
#define HOT __attribute__((section(".iwram"),long_call))
#define FAST __attribute__((section(".iwram_bss")))
#else
#define HOT
#define FAST
#endif
enum {DELAY=1,ATTACK,HOLD,DECAY,SUSTAIN,RELEASE,DONE};
typedef struct {int level,remaining,slope;u32 stage,slope_block;} Envelope;
typedef struct {
 const NativeTone*t;u32 pos,fraction,serial;Envelope amp,mod;
 int lfo_level,lfo_delta,lfo_delay;
 u8 channel,key,velocity,held;
 u32 base_step,base_left,base_right;
} SynthVoice;
typedef struct {u32 gain,pitch;int pan,sustain;} Channel;
typedef struct {u32 cursor,event,serial,count;Channel channels[16];SynthVoice voices[VOICE_LIMIT];} SynthState;
static SynthState synth FAST;
static short sample_cache[2048] FAST;
static u16 loop_cache_offsets[512];
static SynthState loop_state;
static const NativeSoundFont*font;
static const NativeTone*tones;
static const short*samples;
static const u32*pitches,*volumes,*pans;
static const u8*lists,*events;
static u32 event_bytes,total_frames,loop_frame,loop_event;
static int loop_ready,playing;
volatile u32 native_midi_debug[8];
static const u32*paired_loop(const NativeTone*t){
 u32 at=t->pad>0?((const u32*)((const u8*)font+font->loop_pairs))[t->pad-1]:0;
 return at?(const u32*)((const u8*)font+at):0;
}
static inline u32 multiply(u32 a,u32 b,int shift){return (u32)(((unsigned long long)a*b)>>shift);}
static inline int minimum(int a,int b){return a<b?a:b;}
static u32 power(u32 base,unsigned n){u32 result=1U<<30;while(n){if(n&1)result=multiply(result,base,30);n>>=1;if(n)base=multiply(base,base,30);}return result;}
static void env_next(Envelope*e,const NativeEnvelope*p,int amp,int velocity){
 for(;;){e->stage++;
  switch(e->stage){
  case DELAY:e->remaining=p->delay;e->level=e->slope=0;break;
  case ATTACK:e->remaining=amp?p->attack:(u32)((unsigned long long)p->attack*(145-velocity)/144);e->level=0;e->slope=e->remaining?ONE/e->remaining:0;break;
  case HOLD:e->remaining=p->hold;e->level=ONE;e->slope=0;break;
  case DECAY:e->remaining=p->decay_length;e->level=ONE;e->slope=amp?(int)p->decay_coeff:(p->decay?-ONE/(int)p->decay:0);break;
  case SUSTAIN:e->remaining=0x7fffffff;e->level=p->sustain;e->slope=0;return;
  case RELEASE:e->remaining=p->release;e->slope=amp?(int)p->release_coeff:(e->remaining?-e->level/e->remaining:0);break;
  default:e->stage=DONE;e->remaining=0x7fffffff;e->level=e->slope=0;return;
  }
  if(e->remaining>0){if(amp&&(e->stage==DECAY||e->stage==RELEASE))e->slope_block=power(e->slope,NATIVE_MIDI_BLOCK);return;}
 }
}
static inline void env_tick(Envelope*e,const NativeEnvelope*p,int amp,int velocity,unsigned n){
 if(e->slope){if(amp&&(e->stage==DECAY||e->stage==RELEASE))e->level=multiply(e->level,n==NATIVE_MIDI_BLOCK?e->slope_block:power(e->slope,n),30);else e->level+=e->slope*(int)n;}
 if((e->remaining-=(int)n)<=0)env_next(e,p,amp,velocity);
}
static void release_voice(SynthVoice*v,int quick){
 v->amp.stage=v->mod.stage=SUSTAIN;
 if(quick){v->amp.stage=v->mod.stage=RELEASE;v->amp.remaining=v->mod.remaining=163;v->amp.slope=1014654001;v->amp.slope_block=power(v->amp.slope,NATIVE_MIDI_BLOCK);v->mod.slope=-v->mod.level/163;}
 else {env_next(&v->amp,&v->t->amp,1,v->velocity);env_next(&v->mod,&v->t->mod,0,v->velocity);}
}
static void voice_channel(SynthVoice*v){
 const NativeTone*t=v->t;Channel*c=synth.channels+v->channel;int pi=2048+((t->pan+c->pan)>>3);
 u32 gain=multiply(t->gain,c->gain,16);gain=(u32)((unsigned long long)gain*v->velocity/127);
 if(pi<0)pi=0;if(pi>4096)pi=4096;
 v->base_step=multiply(t->step,c->pitch,20);v->base_left=multiply(gain,pans[4096-pi],16);v->base_right=multiply(gain,pans[pi],16);
}
static void off(int channel,int key){
 unsigned i,serial=0xffffffffU;
 for(i=0;i<synth.count;i++){SynthVoice*v=synth.voices+i;if(v->channel==channel&&v->key==key&&v->amp.stage<RELEASE&&!v->held&&v->serial<serial)serial=v->serial;}
 for(i=0;i<synth.count;i++){SynthVoice*v=synth.voices+i;if(v->channel==channel&&v->key==key&&v->serial==serial&&v->amp.stage<RELEASE&&!v->held){if(synth.channels[channel].sustain)v->held=1;else release_voice(v,0);}}
}
static void on(u32 command,u32 list){
 unsigned ch=(command>>4)&15,key=(command>>8)&127,velocity=(command>>16)&127,i,j,n;
 const u16*ids=(const u16*)(lists+list);u32 serial=synth.serial++;
 n=*ids++;
 for(i=0;i<n;i++){
  const NativeTone*t=tones+ids[i];SynthVoice*v;
  if(t->group)for(j=0;j<synth.count;j++)if(synth.voices[j].t->preset==t->preset&&synth.voices[j].t->group==t->group)release_voice(synth.voices+j,1);
  if(synth.count>=VOICE_LIMIT){native_midi_debug[3]++;continue;}
  v=synth.voices+synth.count++;v->t=t;v->pos=t->offset;v->fraction=0;v->serial=serial;
  v->amp=(Envelope){0,0,0,0,0};v->mod=(Envelope){0,0,0,0,0};
  env_next(&v->amp,&t->amp,1,velocity);env_next(&v->mod,&t->mod,0,velocity);
  v->lfo_level=0;v->lfo_delta=t->lfo_delta;v->lfo_delay=t->lfo_delay;
  v->channel=ch;v->key=key;v->velocity=velocity;v->held=0;
  voice_channel(v);
 }
 native_midi_debug[2]=synth.count;if(synth.count>native_midi_debug[1])native_midi_debug[1]=synth.count;
}
static void event(void){
 const u32*data=(const u32*)(events+synth.event);u32 cmd=data[1],kind=cmd&15,ch=(cmd>>4)&15,value=kind==1||(kind>=3&&kind<=5)?data[2]:0;Channel*c=synth.channels+ch;unsigned i;
 synth.event+=kind==1||(kind>=3&&kind<=5)?12:8;
 switch(kind){
 case 1:on(cmd,value);break;
 case 2:off(ch,(cmd>>8)&127);break;
 case 3:c->gain=value;break;
 case 4:c->pitch=value;break;
 case 5:c->pan=(int)value;break;
 case 6:c->sustain=cmd>>8;if(!c->sustain)for(i=0;i<synth.count;i++){SynthVoice*v=synth.voices+i;if(v->channel==ch&&v->held&&v->amp.stage<RELEASE)release_voice(v,0);}break;
 case 7:case 8:for(i=0;i<synth.count;i++){SynthVoice*v=synth.voices+i;if(v->channel==ch&&(v->amp.stage<RELEASE||kind==7))release_voice(v,kind==7);}break;
 }
 if(kind>=3&&kind<=5)for(i=0;i<synth.count;i++)if(synth.voices[i].channel==ch)voice_channel(synth.voices+i);
 native_midi_debug[0]++;
}
static void copy_state(SynthState*to,const SynthState*from){
 unsigned i,n=(unsigned)((const u8*)(from->voices+from->count)-(const u8*)from)/4;u32*d=(u32*)to;const u32*s=(const u32*)from;for(i=0;i<n;i++)d[i]=s[i];
}
void native_midi_init(const void*bank){const u8*b=bank;font=bank;tones=(const NativeTone*)(b+font->tones);samples=(const short*)(b+font->samples);lists=b+font->lists;pitches=(const u32*)(b+font->pitches);volumes=(const u32*)(b+font->volumes);pans=(const u32*)(b+font->pans);playing=0;}
void native_midi_stop(void){playing=0;synth.count=0;}
void native_midi_start(const void*sequence){
 const u32*h=sequence;unsigned i;const u32*cache=(const u32*)((const u8*)sequence+h[4]);events=(const u8*)(cache+h[5]*4);event_bytes=h[0];total_frames=h[1];loop_frame=h[2];loop_event=h[3];
 for(i=0;i<512;i++)loop_cache_offsets[i]=0;
 for(i=0;i<h[5];i++){const u32*c=cache+i*4;unsigned j;if(c[0]>=512||c[2]+c[3]>2048)continue;loop_cache_offsets[c[0]]=c[2]+1;for(j=0;j<c[3];j++)sample_cache[c[2]+j]=samples[c[1]+j];}
 synth.cursor=synth.event=synth.serial=synth.count=0;
 for(i=0;i<16;i++)synth.channels[i]=(Channel){65536,1048576,0,0};
 for(i=0;i<8;i++)native_midi_debug[i]=0;
 loop_ready=0;playing=total_frames>0;
}
u32 native_midi_position(void){return synth.cursor;}
/* Separate the sample loop from controller/envelope code so ARM7 can keep
 * phase, gains and loop bounds in registers for the complete block. */
static void HOT __attribute__((noinline)) mix_wave(SynthVoice*v,unsigned n,u32 step,u32 gl,u32 gr,int*left,int*right){
 const NativeTone*t=v->t;u32 pos=v->pos,fraction=v->fraction,end=t->end,start=t->loop_start,stop=t->loop_end;unsigned j;
 u32 cached=t->pad>0?loop_cache_offsets[t->pad-1]:0;
 if(cached&&pos>=start&&step/65536<stop-start+1){
  const short*base=sample_cache+cached-1;
  u32 phase=((pos-start)<<16)|fraction,length=(stop-start+1)<<16;
  for(j=0;j<n;j++){
   const short*p=base+(phase>>16);int a=p[0],delta=p[1]-a;
   int s=(int)(((u32)a<<16)+(u32)delta*(phase&65535))>>16;
   left[j]+=(s*(int)gl)>>14;right[j]+=(s*(int)gr)>>14;
   phase+=step;if(phase>=length)phase-=length;
  }
  pos=start+(phase>>16);fraction=phase&65535;
 }else if(start<stop&&pos>=start&&step/65536<stop-start+1&&paired_loop(t)){
  const u32*base=paired_loop(t);u32 phase=((pos-start)<<16)|fraction,length=(stop-start+1)<<16;
  for(j=0;j<n;j++){
   u32 packed=base[phase>>16];int delta=(int)packed>>16;
   int s=(int)((packed<<16)+(u32)delta*(phase&65535))>>16;
   left[j]+=(s*(int)gl)>>14;right[j]+=(s*(int)gr)>>14;
   phase+=step;if(phase>=length)phase-=length;
  }
  pos=start+(phase>>16);fraction=phase&65535;
 }else if(step==65536&&!fraction&&start>=stop){
  unsigned count=n;if(pos+count>end)count=end-pos;
  for(j=0;j<count;j++){int s=samples[pos++];left[j]+=(s*(int)gl)>>14;right[j]+=(s*(int)gr)>>14;}
 }else if(start<stop){for(j=0;j<n&&pos<end;j++){
  const short*p=samples+pos;int s=p[0],delta=p[1]-s;
  /* The convex weighted sum fits signed 32 bits. Unsigned modular arithmetic
   * also keeps the intermediate difference product defined at full scale. */
  s=(int)(((u32)s<<16)+(u32)delta*fraction)>>16;left[j]+=(s*(int)gl)>>14;right[j]+=(s*(int)gr)>>14;
  fraction+=step;pos+=fraction>>16;fraction&=65535;if(pos>stop)pos-=stop-start+1;
 }}else{for(j=0;j<n&&pos<end;j++){
  int s=samples[pos],delta=samples[pos+1]-s;s=(int)(((u32)s<<16)+(u32)delta*fraction)>>16;
  left[j]+=(s*(int)gl)>>14;right[j]+=(s*(int)gr)>>14;fraction+=step;pos+=fraction>>16;fraction&=65535;
 }}
 v->pos=pos;v->fraction=fraction;
}
static void HOT __attribute__((noinline)) mix_center(SynthVoice*v,unsigned n,u32 step,u32 gain,int*center){
 const NativeTone*t=v->t;u32 pos=v->pos,fraction=v->fraction,end=t->end,start=t->loop_start,stop=t->loop_end;unsigned j;
 u32 cached=t->pad>0?loop_cache_offsets[t->pad-1]:0;
 if(cached&&pos>=start&&step/65536<stop-start+1){
  const short*base=sample_cache+cached-1;u32 phase=((pos-start)<<16)|fraction,length=(stop-start+1)<<16;
  for(j=0;j<n;j++){
   const short*p=base+(phase>>16);int a=p[0],delta=p[1]-a;
   int s=(int)(((u32)a<<16)+(u32)delta*(phase&65535))>>16;center[j]+=(s*(int)gain)>>14;
   phase+=step;if(phase>=length)phase-=length;
  }
  pos=start+(phase>>16);fraction=phase&65535;
 }else if(start<stop&&pos>=start&&step/65536<stop-start+1&&paired_loop(t)){
  const u32*base=paired_loop(t);u32 phase=((pos-start)<<16)|fraction,length=(stop-start+1)<<16;
  for(j=0;j<n;j++){
   u32 packed=base[phase>>16];int delta=(int)packed>>16;
   int s=(int)((packed<<16)+(u32)delta*(phase&65535))>>16;
   center[j]+=(s*(int)gain)>>14;phase+=step;if(phase>=length)phase-=length;
  }
  pos=start+(phase>>16);fraction=phase&65535;
 }else if(start<stop&&step/65536<stop-start+1){
  u32 length=stop-start+1;
  for(j=0;j<n;j++){
   const short*p=samples+pos;int a=p[0],delta=p[1]-a;
   int s=(int)(((u32)a<<16)+(u32)delta*fraction)>>16;center[j]+=(s*(int)gain)>>14;
   fraction+=step;pos+=fraction>>16;fraction&=65535;if(pos>stop)pos-=length;
  }
 }else if(step==65536&&!fraction){
  unsigned count=n;if(pos+count>end)count=end-pos;for(j=0;j<count;j++)center[j]+=(samples[pos++]*(int)gain)>>14;
 }else{
  for(j=0;j<n&&pos<end;j++){
   int a=samples[pos],delta=samples[pos+1]-a,s=(int)(((u32)a<<16)+(u32)delta*fraction)>>16;
   center[j]+=(s*(int)gain)>>14;fraction+=step;pos+=fraction>>16;fraction&=65535;
  }
 }
 v->pos=pos;v->fraction=fraction;
}
static void render_segment(short*out,unsigned n){
 int left[NATIVE_MIDI_BLOCK],right[NATIVE_MIDI_BLOCK],center[NATIVE_MIDI_BLOCK];unsigned i=0,j;
 if(out){volatile int*l=left,*r=right,*c=center;for(j=0;j<n;j++){l[j]=0;r[j]=0;c[j]=0;}}
 while(i<synth.count){
  SynthVoice*v=synth.voices+i;const NativeTone*t=v->t;
  u32 step=v->base_step,level=v->amp.level<0?0:v->amp.level,gl,gr;
  int cents=(int)(((long long)v->lfo_level*t->lfo_pitch+(long long)v->mod.level*t->env_pitch)>>24);
  if(cents){if(cents< -2400)cents=-2400;if(cents>2400)cents=2400;step=multiply(step,pitches[cents+2400],20);}
  if(t->lfo_volume){int db=(int)(((long long)v->lfo_level*t->lfo_volume*10)>>24);if(db< -200)db=-200;if(db>200)db=200;level=multiply(level,volumes[db+200],16);}
  gl=multiply(v->base_left,level,26);gr=multiply(v->base_right,level,26);
  env_tick(&v->amp,&t->amp,1,v->velocity,n);if(t->env_pitch)env_tick(&v->mod,&t->mod,0,v->velocity,n);
  if(t->lfo_pitch||t->lfo_volume){if(v->lfo_delay>(int)n)v->lfo_delay-=n;else{v->lfo_level+=v->lfo_delta*(int)n;if(v->lfo_level>ONE){v->lfo_level=2*ONE-v->lfo_level;v->lfo_delta=-v->lfo_delta;}else if(v->lfo_level< -ONE){v->lfo_level=-2*ONE-v->lfo_level;v->lfo_delta=-v->lfo_delta;}}}
  if(out&&(gl||gr)){
   if(gl==gr)mix_center(v,n,step,gl,center);else mix_wave(v,n,step,gl,gr,left,right);
  }else{
   unsigned long long position=(unsigned long long)v->fraction+(unsigned long long)step*n;
   v->pos+=position>>16;v->fraction=position&65535;
   if(t->loop_start<t->loop_end&&v->pos>t->loop_end)v->pos=t->loop_start+(v->pos-t->loop_start)%(t->loop_end-t->loop_start+1);
  }
  /* Once a fixed-point release is exactly zero it cannot become audible again.
   * Retiring that silent tail removes no samples, notes or controller changes. */
  if(v->pos>=t->end||v->amp.stage==DONE||(!v->amp.level&&(v->amp.stage==RELEASE||(v->held&&v->amp.stage>=DECAY&&v->amp.stage<=SUSTAIN&&!t->amp.sustain)))){synth.count--;if(i<synth.count)synth.voices[i]=synth.voices[synth.count];}else i++;
 }
 if(out)for(j=0;j<n;j++){int l=left[j]+center[j],r=right[j]+center[j];if(l< -32768){l=-32768;native_midi_debug[4]++;}else if(l>32767){l=32767;native_midi_debug[4]++;}if(r< -32768){r=-32768;native_midi_debug[4]++;}else if(r>32767){r=32767;native_midi_debug[4]++;}out[2*j]=l;out[2*j+1]=r;}
 native_midi_debug[2]=synth.count;
}
void HOT native_midi_render(short*out,unsigned frames){
 while(frames&&playing){
  unsigned n=minimum(frames,NATIVE_MIDI_BLOCK);u32 boundary;
  if(!loop_ready&&synth.cursor==loop_frame){copy_state(&loop_state,&synth);loop_ready=1;}
  if(synth.cursor>=total_frames){
   if(loop_frame<total_frames&&loop_ready){copy_state(&synth,&loop_state);synth.event=loop_event;native_midi_debug[5]++;}
   else {playing=0;break;}
  }
  while(synth.event<event_bytes&&((const u32*)(events+synth.event))[0]<=synth.cursor)event();
  boundary=total_frames;if(synth.event<event_bytes&&((const u32*)(events+synth.event))[0]<boundary)boundary=((const u32*)(events+synth.event))[0];
  if(!loop_ready&&loop_frame>synth.cursor&&loop_frame<boundary)boundary=loop_frame;
  if(boundary-synth.cursor<n)n=boundary-synth.cursor;
  if(!n)continue;
  render_segment(out,n);synth.cursor+=n;frames-=n;if(out)out+=n*2;
 }
 if(out)while(frames--){*out++=0;*out++=0;}
 native_midi_debug[6]=synth.cursor;
}
void native_midi_seek(u32 source_sample){
 /* Replay control/envelope evolution only; waveform interpolation is omitted.
  * Cold loading is bounded to the saved position of this one original song. */
 if(source_sample>total_frames)source_sample=total_frames;
 while(playing&&synth.cursor<source_sample){unsigned n=source_sample-synth.cursor;if(n>NATIVE_MIDI_BLOCK)n=NATIVE_MIDI_BLOCK;native_midi_render(0,n);}
}
void native_midi_quality(int appreciation){(void)appreciation;}
#endif
