/* Export original MIDI events with the supplied SoundFont's preset and MIDI
 * controller resolution. No rendered PCM or replacement arrangements.
 * TinySoundFont / TinyMidiLoader keep their MIT notices in research/reference. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#define TSF_IMPLEMENTATION
#include "../research/reference/tsf.h"
#define TML_IMPLEMENTATION
#include "../research/reference/tml.h"
static double pitch(const struct tsf_channel*c){return c->pitchWheel==8192?c->tuning:(c->pitchWheel/16383.0*c->pitchRange*2-c->pitchRange+c->tuning);}
int main(int argc,char**argv){
 if(argc!=3)return 2;
 tsf*f=tsf_load_filename(argv[1]);tml_message*first=tml_load_filename(argv[2]),*m;
 if(!f||!first)return 3;
 tsf_set_output(f,TSF_STEREO_INTERLEAVED,16384,-6);
 tsf_channel_init(f,15);tsf_channel_set_bank_preset(f,9,128,0);
 unsigned end=0,loop=0;int sep=0;
 printf("{\"events\":[");
 for(m=first;m;m=m->next){
  unsigned at=(unsigned)((unsigned long long)m->time*16384/1000);
  struct tsf_channel*c=&f->channels->channels[m->channel];
  end=at;
  if(m->type==TML_NOTE_ON&&m->velocity){printf("%s[%u,1,%u,%u,%u,%u]",sep?",":"",at,m->channel,m->key,(unsigned char)m->velocity,c->presetIndex);sep=1;}
  else if(m->type==TML_NOTE_OFF||(m->type==TML_NOTE_ON&&!m->velocity)){printf("%s[%u,2,%u,%u]",sep?",":"",at,m->channel,m->key);sep=1;}
  else if(m->type==TML_PROGRAM_CHANGE)tsf_channel_set_presetnumber(f,m->channel,(unsigned char)m->program,m->channel==9);
  else if(m->type==TML_PITCH_BEND||m->type==TML_CONTROL_CHANGE){
   double oldgain=c->gainDB,oldpan=c->panOffset,oldpitch=pitch(c);unsigned oldsustain=c->sustain;
   if(m->type==TML_PITCH_BEND)tsf_channel_set_pitchwheel(f,m->channel,m->pitch_bend);
   else tsf_channel_midi_control(f,m->channel,(unsigned char)m->control,(unsigned char)m->control_value);
   if(c->gainDB!=oldgain){printf("%s[%u,3,%u,%u]",sep?",":"",at,m->channel,(unsigned)llround(pow(10,c->gainDB/20.0)*65536));sep=1;}
   if(pitch(c)!=oldpitch){printf("%s[%u,4,%u,%u]",sep?",":"",at,m->channel,(unsigned)llround(pow(2,pitch(c)/12.0)*1048576));sep=1;}
   if(c->panOffset!=oldpan){printf("%s[%u,5,%u,%d]",sep?",":"",at,m->channel,(int)llround(c->panOffset*32768));sep=1;}
   if(c->sustain!=oldsustain){printf("%s[%u,6,%u,%u]",sep?",":"",at,m->channel,c->sustain);sep=1;}
   if(m->type==TML_CONTROL_CHANGE){
    if(m->control==120||m->control==123){printf("%s[%u,%u,%u,0]",sep?",":"",at,m->control==120?7:8,m->channel);sep=1;}
    if(m->control==111)loop=at;
   }
  }
 }
 printf("],\"frames\":%u,\"loop\":%u}\n",end,loop);
 tsf_close(f);tml_free(first);return 0;
}
