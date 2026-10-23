#include "gba_hw.h"
#include "rm2k_commands.h"
#include "engine.h"
#include "audio.h"
#include "native_midi.h"
/* Stereo Direct Sound, fed in 16-sample groups by cascaded timer IRQ.
 * Offline IMA storage preserves complete source songs and their CC111 loops.
 * No PSG substitute or invented melody is used. See audio_manifest.json.
 */
typedef struct {u32 hash,kind,offset,frames,loop;short lp,rp;u8 li,ri;u16 pad;} Track;
typedef struct {const Track*t;u32 pos,fraction,step;int lp,rp,li,ri,left,right;} Voice;
extern const u8 original_audio_start[];
extern const u8 native_soundfont_start[];
extern int midi_clock_ticks(int id,u32 sample);
extern void irq_dispatch(void);
extern volatile unsigned input_latched,input_sampled;
volatile u32 video_frame_counter;
static Voice voices[5] __attribute__((section(".iwram_bss")));
#ifndef RUINA_PCM_WAV
static int deltas[89][16];
static u8 indices[89][16];
#endif
static const u8*stream_data;
static u32 fade_total,fade_elapsed;static int fade_out;
static int music_paused,music_quality;
/* Synthesis runs on the main CPU path. The timer interrupt only consumes a
 * bounded PCM queue, so a large chord cannot delay the hardware FIFO refill. */
static short native_queue[1024][2] __attribute__((section(".iwram_bss")));
static volatile unsigned native_read,native_write;
volatile u32 audio_stream_debug[4];
volatile u32 audio_debug[8];
#ifndef RUINA_PCM_WAV
static const int steps[89]={7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767};
#endif
static int count(void){return ((const u32*)original_audio_start)[1];}
static const Track*track(int id){return id>0&&id<=count()?(const Track*)(original_audio_start+8)+(id-1):0;}
static const u8*data(void){return original_audio_start+8+count()*sizeof(Track);}
static int lookup(LcfSpan name,int kind){u32 h=2166136261U;unsigned i;int j;if(!name.size||name.data[0]=='(')return 0;for(i=0;i<name.size;i++){h^=name.data[i];h*=16777619U;}for(j=1;j<=count();j++){const Track*t=track(j);if(t->hash==h&&(t->kind==(unsigned)kind||(!kind&&t->kind==2)))return j;}audio_debug[6]=h;audio_debug[7]++;return 0;}
static void gains(Voice*v,Music m){int volume=clamp(m.volume,0,100),pan=clamp(m.pan,0,100);v->left=volume*256/100*(pan>50?100-pan:50)/50;v->right=volume*256/100*(pan<50?pan:50)/50;v->step=(u32)clamp(m.pitch,50,200)*65536/100;}
static void start(Voice*v,Music m){memset(v,0,sizeof(*v));v->t=track(m.id);gains(v,m);if(v==voices){native_read=native_write=0;if(v->t&&v->t->kind==2)native_midi_start(stream_data+v->t->offset);else native_midi_stop();}}
void audio_service(void){
 unsigned block;const Track*t=voices[0].t;if(!t||t->kind!=2||music_paused)return;
 for(block=0;block<8&&native_write-native_read<=1024-NATIVE_MIDI_BLOCK;block++){
  /* Writes are block-aligned and cannot cross the 1024-frame ring end.
   * Publish only after synthesis completes; the IRQ never reads this block
   * while it is being rendered. No intermediate stereo stack copy is needed. */
  unsigned w=native_write;native_midi_render(native_queue[w&1023],NATIVE_MIDI_BLOCK);
  __asm__ volatile("":::"memory");native_write=w+NATIVE_MIDI_BLOCK;audio_stream_debug[1]++;
 }
 audio_stream_debug[2]=native_write-native_read;
}
void audio_music(Music m,int fadein){int ime=REG16(0x04000208);REG16(0x04000208)=0;music_paused=0;if(voices[0].t==track(m.id)&&m.id){gains(voices,m);}else {start(voices,m);audio_debug[4]=0;}game.music=m;fade_total=fadein>0?(u32)fadein*1024/1000:0;fade_elapsed=0;fade_out=0;audio_debug[1]=m.id;REG16(0x04000208)=ime;}
int audio_music_count(void){int i,n=0;for(i=1;i<=count();i++)if(track(i)->kind!=1)n++;return n;}
int audio_music_id(int index){int i;for(i=1;i<=count();i++)if(track(i)->kind!=1&&index--==0)return i;return 0;}
unsigned audio_music_frames(int id){const Track*t=track(id);return t?t->frames:0;}
void audio_pause_music(int paused){music_paused=paused!=0;}
int audio_music_paused(void){return music_paused;}
void audio_music_quality(int appreciation){music_quality=appreciation!=0;native_midi_quality(music_quality);}
int audio_current_quality(void){return music_quality;}
void audio_music_position(unsigned position){
 Voice*v=voices;const Track*t=v->t;if(!t)return;if(position>=t->frames)position=t->frames-1;
 if(t->kind==2){int ime,paused=music_paused;ime=REG16(0x04000208);REG16(0x04000208)=0;music_paused=1;native_read=native_write=0;REG16(0x04000208)=ime;
  native_midi_start(stream_data+t->offset);native_midi_seek(position);
  ime=REG16(0x04000208);REG16(0x04000208)=0;v->pos=position;audio_debug[3]=position;music_paused=paused;REG16(0x04000208)=ime;}
}
static void sound(Music m){int ime=REG16(0x04000208),i;REG16(0x04000208)=0;for(i=1;i<5;i++)if(!voices[i].t)break;if(i==5){i=1;audio_debug[5]++;}start(voices+i,m);audio_debug[2]=m.id;REG16(0x04000208)=ime;}
void audio_system(int which){if(which>=0&&which<8)audio_music(game.system_music[which],0);}
void audio_effect(int which){if(which>=0&&which<MAX_SYSTEM_SOUND&&game.system_sounds[which].id)sound(game.system_sounds[which]);}
void audio_default_sounds(void){int i;for(i=0;i<MAX_SYSTEM_SOUND;i++){LcfSpan s=field(db[22],41+i);game.system_sounds[i]=(Music){lookup(field(s,1),1),val(s,3,100),val(s,4,100),val(s,5,50)};}game.sound_defaults_set=1;}
void audio_command(int code,LcfSpan name,const int*p){Music m;
 switch(code){
 case RM2K_PlayBGM:m=(Music){lookup(name,0),p[1],p[2],p[3]};audio_music(m,p[0]);break;
 case RM2K_FadeOutBGM:{int ime=REG16(0x04000208);REG16(0x04000208)=0;fade_total=(u32)clamp(p[0],0,60000)*1024/1000;fade_elapsed=0;fade_out=1;if(!fade_total)voices[0].t=0;REG16(0x04000208)=ime;break;}
 case RM2K_MemorizeBGM:game.memorized_music=game.music;break;
 case RM2K_PlayMemorizedBGM:audio_music(game.memorized_music,0);break;
 case RM2K_PlaySound:m=(Music){lookup(name,1),p[0],p[1],p[2]};sound(m);break;
 case RM2K_ChangeSystemBGM:if(p[0]>=0&&p[0]<8)game.system_music[p[0]]=(Music){lookup(name,0),p[2],p[3],p[4]};break;
 case RM2K_ChangeSystemSFX:if(p[0]>=0&&p[0]<MAX_SYSTEM_SOUND)game.system_sounds[p[0]]=(Music){lookup(name,1),p[1],p[2],p[3]};break;
 }
}
void audio_reset(void){int i;REG16(0x04000208)=0;memset(voices,0,sizeof(voices));native_midi_stop();native_midi_quality(0);music_quality=music_paused=0;native_read=native_write=0;fade_total=fade_elapsed=fade_out=0;memset((void*)audio_debug,0,sizeof(audio_debug));memset((void*)audio_stream_debug,0,sizeof(audio_stream_debug));for(i=0;i<8;i++)game.system_music[i]=(Music){0,100,100,50};game.music=game.memorized_music=(Music){0,100,100,50};REG16(0x04000208)=1;}
void audio_restore(void){if(!game.sound_defaults_set)audio_default_sounds();audio_music(game.music,0);}
int audio_midi_ticks(void){return voices[0].t?midi_clock_ticks(game.music.id,voices[0].pos):0;}
int audio_played_once(void){return audio_debug[4]>0;}
static inline __attribute__((always_inline)) int limit(int n){return n<-32768?-32768:n>32767?32767:n;}
static inline __attribute__((always_inline)) void sample(Voice*v){const Track*t=v->t;const u8*src;if(v->pos>=t->frames){if(v==voices&&t->loop<t->frames){v->pos=t->loop;v->lp=t->lp;v->rp=t->rp;v->li=t->li;v->ri=t->ri;audio_debug[4]++;}else {v->t=0;v->lp=v->rp=0;return;}}
 if(t->kind==2){unsigned at=native_read;if(at==native_write){v->lp=v->rp=0;audio_stream_debug[0]++;return;}v->lp=native_queue[at&1023][0];v->rp=native_queue[at&1023][1];native_read=at+1;v->pos++;return;}
 src=stream_data+t->offset;
 if(t->pad){const signed char*pcm=(const signed char*)src;unsigned at=v->pos++;if(t->pad==1)v->lp=v->rp=(int)pcm[at]*256;else{v->lp=(int)pcm[at*2]*256;v->rp=(int)pcm[at*2+1]*256;}return;}
#ifndef RUINA_PCM_WAV
 {unsigned c=src[v->pos++],lc=c>>4,rc=c&15;v->lp=limit(v->lp+deltas[v->li][lc]);v->rp=limit(v->rp+deltas[v->ri][rc]);v->li=indices[v->li][lc];v->ri=indices[v->ri][rc];}
#else
 v->pos++;v->lp=v->rp=0;
#endif
}
void __attribute__((section(".iwram"),long_call)) audio_irq(void){unsigned pending=REG16(0x04000202),word,i,j,mix_count=0;Voice*mix[5];int mix_gain[5],fg=256;REG16(0x04000202)=pending;REG16(0x03007ff8)|=pending;if(pending&1)video_frame_counter++;if(!(pending&16))return;
 {unsigned keys=(~REG16(0x04000130))&1023;input_latched|=keys&~input_sampled;input_sampled=keys;}
 audio_debug[0]++;if(fade_total){if(fade_elapsed<fade_total)fade_elapsed++;fg=(fade_out?fade_total-fade_elapsed:fade_elapsed)*256/fade_total;if(fade_elapsed==fade_total){if(fade_out)voices[0].t=0;fade_total=0;}}
 if(!music_paused&&voices[0].t&&voices[0].t->kind==2&&voices[0].step==65536&&!voices[0].fraction&&!voices[1].t&&!voices[2].t&&!voices[3].t&&!voices[4].t){
  Voice*v=voices;unsigned at=native_read,available=native_write-at;int lg=v->left*fg>>8,rg=v->right*fg>>8;
#ifdef RUINA_LIGHT_MUSIC
  if(!music_quality&&lg==rg){
   for(word=0;word<4;word++){u32 packed=0;for(i=0;i<4;i++){int sample=0;
    if(available){sample=native_queue[at&1023][0];at++;available--;v->pos++;if(v->pos>=v->t->frames){v->pos=v->t->loop;audio_debug[4]++;}}else audio_stream_debug[0]++;
    /* Gains and fade are clamped to 0..256, so a signed-16 input cannot
     * overflow its original range. Both channels are identical in this mode. */
    sample=(sample*lg>>8)>>8;packed|=(u32)(u8)sample<<(i*8);
   }REG32(0x040000a0)=packed;REG32(0x040000a4)=packed;}
   native_read=at;audio_debug[3]=v->pos;return;
  }
#endif
  for(word=0;word<4;word++){u32 left=0,right=0;for(i=0;i<4;i++){
   int l=0,r=0;if(available){l=native_queue[at&1023][0];r=native_queue[at&1023][1];at++;available--;v->pos++;if(v->pos>=v->t->frames){v->pos=v->t->loop;audio_debug[4]++;}}
   else audio_stream_debug[0]++;
   l=(l*lg>>8)>>8;r=(r*rg>>8)>>8;left|=(u32)(u8)l<<(i*8);right|=(u32)(u8)r<<(i*8);
  }REG32(0x040000a0)=left;REG32(0x040000a4)=right;}
  native_read=at;audio_debug[3]=v->pos;return;
 }
 /* The active set is fixed for this interrupt. Keep its original order and
  * arithmetic, but avoid checking four empty effect slots for every sample. */
 for(j=0;j<5;j++)if(voices[j].t&&(j||!music_paused)){mix[mix_count]=voices+j;mix_gain[mix_count++]=j?256:fg;}
 for(word=0;word<4;word++){u32 left=0,right=0;for(i=0;i<4;i++){int l=0,r=0;for(j=0;j<mix_count;j++){Voice*v=mix[j];int gain=mix_gain[j];if(!v->t)continue;v->fraction+=v->step;while(v->fraction>=65536&&v->t){v->fraction-=65536;sample(v);}l+=((v->lp*v->left)>>8)*gain>>8;r+=((v->rp*v->right)>>8)*gain>>8;}
   l=limit(l)>>8;r=limit(r)>>8;left|=(u32)(u8)l<<(i*8);right|=(u32)(u8)r<<(i*8);}
  REG32(0x040000a0)=left;REG32(0x040000a4)=right;}
 audio_debug[3]=voices[0].pos;
}
void audio_init(void){int i;REG16(0x04000208)=0;
 stream_data=data();native_midi_init(native_soundfont_start);
 /* Free-running hardware time supplies fresh new-game seeds. */
 REG16(0x0400010a)=0;REG16(0x04000108)=0;REG16(0x0400010a)=0x83;
#ifndef RUINA_PCM_WAV
 {int j;static const int adjust[8]={-1,-1,-1,-1,2,4,6,8};for(i=0;i<89;i++)for(j=0;j<16;j++){int step=steps[i],d=step/8;if(j&1)d+=step/4;if(j&2)d+=step/2;if(j&4)d+=step;deltas[i][j]=(j&8)?-d:d;indices[i][j]=clamp(i+adjust[j&7],0,88);}}
#endif
 REG32(0x03007ffc)=(u32)irq_dispatch;REG16(0x04000084)=0x80;REG16(0x04000082)=0x9a0c;for(i=0;i<8;i++){REG32(0x040000a0)=0;REG32(0x040000a4)=0;}REG16(0x04000102)=0;REG16(0x04000106)=0;REG16(0x04000100)=65536-1024;REG16(0x04000104)=65536-16;REG16(0x04000202)=0xffff;REG16(0x04000004)|=8;REG16(0x04000200)=17;REG16(0x04000106)=0xc4;REG16(0x04000102)=0x80;REG16(0x04000208)=1;
}
