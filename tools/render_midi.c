/* Offline renderer using the supplied game's own SoundFont and original MIDI.
 * TinySoundFont / TinyMidiLoader retain their upstream notices in reference/.
 * No notes, programs, drums, tempo events or song endings are rewritten.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#define TSF_IMPLEMENTATION
#include "../research/reference/tsf.h"
#define TML_IMPLEMENTATION
#include "../research/reference/tml.h"
int main(int argc,char**argv){
 if(argc<3)return 2;tml_message*first=tml_load_filename(argv[2]),*m,*end=NULL;unsigned loop_ms=0,events=0;
 if(!first)return 3;for(m=first;m;m=m->next){end=m;events++;if(m->type==TML_CONTROL_CHANGE&&m->control==111)loop_ms=m->time;}
 if(argc<4){printf("{\"milliseconds\":%u,\"loop_ms\":%u,\"events\":%u}\n",end->time,loop_ms,events);tml_free(first);return 0;}
 tsf*f=tsf_load_filename(argv[1]);if(!f)return 4;const unsigned rate=16384;tsf_set_output(f,TSF_STEREO_INTERLEAVED,rate,-6.0f);tsf_channel_set_bank_preset(f,9,128,0);
 FILE*out=fopen(argv[3],"wb");if(!out)return 5;unsigned cursor=0,limit=(unsigned)((uint64_t)end->time*rate/1000);short samples[512*2];m=first;
 while(cursor<limit){
  while(m&&(uint64_t)m->time*rate/1000<=cursor){
   switch(m->type){case TML_NOTE_ON:tsf_channel_note_on(f,m->channel,m->key,(unsigned char)m->velocity/127.0f);break;case TML_NOTE_OFF:tsf_channel_note_off(f,m->channel,m->key);break;case TML_PROGRAM_CHANGE:tsf_channel_set_presetnumber(f,m->channel,(unsigned char)m->program,m->channel==9);break;case TML_CONTROL_CHANGE:tsf_channel_midi_control(f,m->channel,(unsigned char)m->control,(unsigned char)m->control_value);break;case TML_PITCH_BEND:tsf_channel_set_pitchwheel(f,m->channel,m->pitch_bend);break;}
   m=m->next;
  }
  unsigned n=512;if(n>limit-cursor)n=limit-cursor;if(m){unsigned at=(unsigned)((uint64_t)m->time*rate/1000);if(at-cursor<n)n=at-cursor;}
  if(!n)continue;tsf_render_short(f,samples,n,0);fwrite(samples,4,n,out);cursor+=n;
 }
 fclose(out);tsf_close(f);tml_free(first);return 0;
}
