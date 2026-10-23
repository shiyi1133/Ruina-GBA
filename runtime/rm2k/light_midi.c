/* Deliberately simplified timbres for the user's GBA performance policy.
 * Source note/controller times are retained at 16384 samples per second.
 * Gameplay uses a coarse mono wavetable and pairs adjacent output samples;
 * the music room uses a finer 128-point table, compiled amplitude steps and stereo controllers.
 * This does not claim original SoundFont timbre or original PCM fidelity. */
#ifdef RUINA_LIGHT_MUSIC
#include "native_midi.h"
#ifdef __arm__
#define LIGHT_HOT __attribute__((section(".iwram"),long_call))
#define LIGHT_FAST __attribute__((section(".iwram_bss")))
#else
#define LIGHT_HOT
#define LIGHT_FAST
#endif
#ifndef RUINA_LIGHT_VOICES
#define RUINA_LIGHT_VOICES 160
#endif
#define LIGHT_VOICES RUINA_LIGHT_VOICES
typedef struct {u32 phase,step,serial;int level;u16 release;u8 program,channel,key,velocity,held,pad;} LightVoice;
typedef struct {u32 gain,pitch;int pan,sustain;} LightChannel;
typedef struct {u32 cursor,event,next,serial,count;LightChannel channels[16];LightVoice voices[LIGHT_VOICES];} LightState;
static LightState state LIGHT_FAST;
static LightState loop_state;
static const signed char*drum_pcm;
static const short*scaled_waves;
static int bank_ready;
static const u32*drums,*pitch_table;
static const u8*score;
static u32 score_bytes,total_frames,loop_frame;
static int playing,loop_ready,quality;
volatile u32 native_midi_debug[8];

static u32 number(void){
 u32 value=0;unsigned shift;
 for(shift=0;shift<35&&state.event<score_bytes;shift+=7){u32 b=score[state.event++];value|=(b&127)<<shift;if(!(b&128))return value;}
 playing=0;native_midi_debug[3]++;return 0;
}
static void next_time(void){if(state.event<score_bytes)state.next+=number();else state.next=0xffffffffU;}
static void state_copy(LightState*to,const LightState*from){unsigned n=(unsigned)((const u8*)(from->voices+from->count)-(const u8*)from)/4;u32*d=(u32*)to;const u32*s=(const u32*)from;while(n--)*d++=*s++;}
static void release(LightVoice*v){v->held=0;v->release=1;}
static void note_off(int channel,int key){
 unsigned i;u32 oldest=0xffffffffU;
 for(i=0;i<state.count;i++){LightVoice*v=state.voices+i;if(v->channel==channel&&v->key==key&&!v->held&&!v->release&&v->serial<oldest)oldest=v->serial;}
 for(i=0;i<state.count;i++){LightVoice*v=state.voices+i;if(v->channel==channel&&v->key==key&&v->serial==oldest&&!v->release){if(state.channels[channel].sustain)v->held=1;else release(v);}}
}
static void set_step(LightVoice*v){u32 base=v->program&128?32768:pitch_table[v->key];v->step=(u32)(((unsigned long long)base*state.channels[v->channel].pitch)>>20);}
static void execute_event(void){
 unsigned tag,kind,ch,i;if(state.event>=score_bytes){state.next=0xffffffffU;return;}
 tag=score[state.event++];kind=tag&15;ch=tag>>4;
 if(kind==1){
  unsigned key,velocity,program;LightVoice*v;
  if(state.event+3>score_bytes){playing=0;native_midi_debug[3]++;return;}
  key=score[state.event++];velocity=score[state.event++];program=score[state.event++];
  if(state.count==LIGHT_VOICES){native_midi_debug[3]++;next_time();return;}
  v=state.voices+state.count++;v->phase=0;v->serial=state.serial++;v->level=65536;v->release=0;
  v->program=program;v->channel=ch;v->key=key;v->velocity=velocity;v->held=v->pad=0;set_step(v);
  if(state.count>native_midi_debug[1])native_midi_debug[1]=state.count;
 }else if(kind==2){if(state.event<score_bytes)note_off(ch,score[state.event++]);}
 else if(kind==3)state.channels[ch].gain=number();
 else if(kind==4){state.channels[ch].pitch=number();for(i=0;i<state.count;i++)if(state.voices[i].channel==ch)set_step(state.voices+i);}
 else if(kind==5){u32 n=number();state.channels[ch].pan=clamp((int)((n>>1)^-(n&1)),-32768,32768);}
 else if(kind==6){
  if(state.event<score_bytes)state.channels[ch].sustain=score[state.event++];
  if(!state.channels[ch].sustain)for(i=0;i<state.count;i++)if(state.voices[i].channel==ch&&state.voices[i].held)release(state.voices+i);
 }else if(kind==7||kind==8){for(i=0;i<state.count;i++)if(state.voices[i].channel==ch)release(state.voices+i);}
 else {playing=0;native_midi_debug[3]++;return;}
 native_midi_debug[0]++;next_time();
}
static void LIGHT_HOT segment(short*out,unsigned n){
 int left[NATIVE_MIDI_BLOCK/2],right[NATIVE_MIDI_BLOCK/2],center[NATIVE_MIDI_BLOCK/2];unsigned i=0,j,stride=2,count;
 /* Dense low/mid-register passages use a lower presentation sample rate.
  * High notes keep the finer rate, and every original event clock remains. */
 if(state.count>64){stride=4;for(i=0;i<state.count;i++)if(state.voices[i].step>=2048000U){stride=2;break;}}
 i=0;count=(n+stride-1)/stride;if(stride==4)native_midi_debug[7]+=n;
 if(out)for(j=0;j<count;j++){left[j]=0;if(quality)right[j]=center[j]=0;}
 while(i<state.count){
  LightVoice*v=state.voices+i;LightChannel*c=state.channels+v->channel;
  u32 phase=v->phase,step=v->step,phase_step=step*stride,end_phase=phase+step*n;int gain=(int)((v->velocity*c->gain)>>8),gone=0;
  gain=gain*(v->level>>8)>>8;
  if(out&&gain){
   if(v->program&128){
    const signed char*pcm=drum_pcm+drums[v->key*2];u32 end=drums[v->key*2+1];
    int pan=quality?c->pan:0,lg,rg;
    if(!pan)lg=rg=gain>>1;else{lg=((u32)gain*(u32)(32768-pan))>>16;rg=((u32)gain*(u32)(32768+pan))>>16;}
    for(j=0;j<count;j++){u32 at=phase>>16;if(at>=end){gone=1;break;}
     if(!quality)left[j]+=pcm[at]*gain>>10;
     else if(lg==rg)center[j]+=pcm[at]*lg>>9;
     else{left[j]+=pcm[at]*lg>>9;right[j]+=pcm[at]*rg>>9;}
     phase+=phase_step;
    }
   }else{
    /* Amplitude is resolved once per voice/block. The inner loop contains
     * only phase, a ready-scaled ROM sample, and an accumulator addition. */
    const short*base=scaled_waves+v->program*65*128;
    if(!quality){unsigned level=(unsigned)(gain+512)>>10;if(level>64)level=64;
     if(level){const short*wave=base+level*128;for(j=0;j<count;j++){left[j]+=wave[(phase>>17)&124];phase+=phase_step;}}
     else phase+=step*n;
    }else{int pan=c->pan;unsigned lg,rg;
     if(!pan)lg=rg=(unsigned)(gain+512)>>10;
     else{lg=((((u32)gain*(u32)(32768-pan))>>16)+256)>>9;rg=((((u32)gain*(u32)(32768+pan))>>16)+256)>>9;}
     const short*lw,*rw;if(lg>64)lg=64;if(rg>64)rg=64;lw=base+lg*128;rw=base+rg*128;
     if(lg==rg){if(lg)for(j=0;j<count;j++){center[j]+=lw[(phase>>17)&127];phase+=phase_step;}else phase+=step*n;}
     else if(!lg)for(j=0;j<count;j++){right[j]+=rw[(phase>>17)&127];phase+=phase_step;}
     else if(!rg)for(j=0;j<count;j++){left[j]+=lw[(phase>>17)&127];phase+=phase_step;}
     else for(j=0;j<count;j++){unsigned at=(phase>>17)&127;left[j]+=lw[at];right[j]+=rw[at];phase+=phase_step;}
    }
   }
  }else{phase+=step*n;if((v->program&128)&&(phase>>16)>=drums[v->key*2+1])gone=1;}
  v->phase=end_phase;
  if(v->release){int shift=quality?3:2;v->level-=(v->level*(int)n)>>(shift+6);if(v->level<64)gone=1;}
  /* Upward rounding lets a pedal-held pluck actually reach silence. */
  else if(!(v->program&128)&&(v->program<16||(v->program>=24&&v->program<40)||(v->program>=104&&v->program<120))){v->level-=(v->level*(int)n+32767)>>15;if(v->level<16)gone=1;}
  if(gone){state.count--;if(i<state.count)state.voices[i]=state.voices[state.count];}else i++;
 }
 if(out)for(j=0;j<count;j++){
  int l=left[j],r;unsigned k,copies=n-j*stride;if(copies>stride)copies=stride;
  if(quality){l+=center[j];r=right[j]+center[j];}else r=l;
  if(l< -32768){l=-32768;native_midi_debug[4]+=copies;}if(l>32767){l=32767;native_midi_debug[4]+=copies;}
  if(r< -32768){r=-32768;native_midi_debug[4]+=copies;}if(r>32767){r=32767;native_midi_debug[4]+=copies;}
  for(k=0;k<copies;k++){*out++=l;*out++=r;}
 }
 native_midi_debug[2]=state.count;
}
void native_midi_quality(int appreciation){quality=appreciation!=0;}
void native_midi_init(const void*bank){const u8*b=bank;const u32*h=bank;playing=0;bank_ready=h[0]==0x3146534c&&h[1]==2;scaled_waves=bank_ready?(const short*)(b+h[2]):0;drums=(const u32*)(b+h[4]);drum_pcm=(const signed char*)(b+h[5]);pitch_table=(const u32*)(b+h[6]);}
void native_midi_stop(void){playing=0;state.count=0;}
void native_midi_start(const void*sequence){
 const u32*h=sequence;unsigned i;score=(const u8*)sequence+32;score_bytes=h[4];total_frames=h[2];loop_frame=h[3];
 state.cursor=state.event=state.next=state.serial=state.count=0;
 for(i=0;i<16;i++)state.channels[i]=(LightChannel){65536,1048576,0,0};
 for(i=0;i<8;i++)native_midi_debug[i]=0;loop_ready=0;playing=bank_ready&&h[0]==0x314d534c&&total_frames>0;
 if(playing)next_time();else native_midi_debug[3]++;
}
u32 native_midi_position(void){return state.cursor;}
void LIGHT_HOT native_midi_render(short*out,unsigned frames){
 while(frames&&playing){
  unsigned n=frames<NATIVE_MIDI_BLOCK?frames:NATIVE_MIDI_BLOCK;u32 boundary;
  if(!loop_ready&&state.cursor==loop_frame){state_copy(&loop_state,&state);loop_ready=1;}
  if(state.cursor>=total_frames){if(loop_ready&&loop_frame<total_frames){state_copy(&state,&loop_state);native_midi_debug[5]++;}else{playing=0;break;}}
  while(playing&&state.next<=state.cursor)execute_event();
  boundary=total_frames;if(state.next<boundary)boundary=state.next;
  if(!loop_ready&&loop_frame>state.cursor&&loop_frame<boundary)boundary=loop_frame;
  if(boundary-state.cursor<n)n=boundary-state.cursor;if(!n)continue;
  segment(out,n);state.cursor+=n;frames-=n;if(out)out+=n*2;
 }
 if(out)while(frames--){*out++=0;*out++=0;}native_midi_debug[6]=state.cursor;
}
void native_midi_seek(u32 sample){if(sample>total_frames)sample=total_frames;while(playing&&state.cursor<sample){unsigned n=sample-state.cursor;if(n>NATIVE_MIDI_BLOCK)n=NATIVE_MIDI_BLOCK;native_midi_render(0,n);}}
#endif
