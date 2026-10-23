/* Deterministic FIFO register observations, not a GBA timing acceptance test. */
#include "engine.h"
#include <stdio.h>
#define RM2K_GBA_HW_H
static volatile u16 host16[1024];
static volatile u32 host32[256];
static u32 last_address,output_hash,output_words;
static void flush_word(void){if(last_address==0x040000a0||last_address==0x040000a4){output_hash=(output_hash^host32[(last_address&1023)/4])*16777619U;output_words++;}last_address=0;}
static volatile u16*reg16(u32 a){return host16+((a&2047)/2);}
static volatile u32*reg32(u32 a){flush_word();last_address=a;return host32+((a&1023)/4);}
#define REG16(a) (*reg16(a))
#define REG32(a) (*reg32(a))
#include AUDIO_SOURCE
__asm__(".section .rodata\n.balign 4\n.global original_audio_start\noriginal_audio_start:\n.incbin \"build/audio.bin\"\n.balign 4\n.global native_soundfont_start\nnative_soundfont_start:\n.incbin \"build/native_music/native_soundfont.bin\"\n.previous\n");
Game game;int battle_active;volatile unsigned input_latched,input_sampled;
int clamp(int n,int lo,int hi){return n<lo?lo:n>hi?hi:n;}
void irq_dispatch(void){}
int main(void){
 const int pitches[4]={50,100,150,200};int id,q,p,effects[4],ef=0,cases=0;unsigned i;
 audio_init();for(id=1;id<=count()&&ef<4;id++)if(track(id)->kind==1)effects[ef++]=id;
 puts("[");
 for(id=1;id<=count();id++)for(q=0;q<(track(id)->kind==2?2:1);q++)for(p=0;p<4;p++){
  Music music={id,90,pitches[p],p==0?0:p==3?100:50};audio_reset();audio_music_quality(q);if(track(id)->kind==1)sound(music);else audio_music(music,0);flush_word();output_hash=2166136261U;output_words=0;
  for(i=0;i<1024;i++){
   if(i==16){int j;for(j=0;j<ef;j++)sound((Music){effects[j],20+j*20,pitches[(p+j)&3],j*30});}
   if(i==512&&track(id)->kind!=1){music.volume=35;music.pan=25;audio_music(music,0);}
   if(i==700&&track(id)->kind!=1)audio_pause_music(1);
   if(i==800&&track(id)->kind!=1)audio_pause_music(0);
   audio_service();REG16(0x04000202)=(i%17)?16:17;audio_irq();flush_word();
  }
  printf("%s{\"track\":%d,\"quality\":%d,\"pitch\":%d,\"FIFO_hash\":%u,\"FIFO_words\":%u,\"position\":%u,\"loops\":%u,\"underruns\":%u}",cases++?",\n":"",id,q,pitches[p],output_hash,output_words,audio_debug[3],audio_debug[4],audio_stream_debug[0]);
 }
 puts("\n]");return 0;
}
