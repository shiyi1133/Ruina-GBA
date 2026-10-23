/* Offline metadata export from the provided SoundFont. TinySoundFont is MIT;
 * its source and notice stay in research/reference/tsf.h. The GBA does not load
 * or expand SF2 in RAM: it reads the resulting immutable sample/voice tables. */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#define TSF_IMPLEMENTATION
#include "../research/reference/tsf.h"
static void envelope(const struct tsf_envelope*e){printf("{\"delay\":%.9g,\"attack\":%.9g,\"hold\":%.9g,\"decay\":%.9g,\"sustain\":%.9g,\"release\":%.9g,\"key_hold\":%.9g,\"key_decay\":%.9g}",e->delay,e->attack,e->hold,e->decay,e->sustain,e->release,e->keynumToHold,e->keynumToDecay);}
int main(int argc,char**argv){int p,i,id=0;if(argc!=2)return 2;tsf*f=tsf_load_filename(argv[1]);if(!f)return 3;
 printf("{\"presets\":[");for(p=0;p<f->presetNum;p++){struct tsf_preset*s=f->presets+p;printf("%s{\"index\":%d,\"bank\":%u,\"program\":%u,\"regions\":[",p?",":"",p,s->bank,s->preset);
 for(i=0;i<s->regionNum;i++,id++){struct tsf_region*r=s->regions+i;
  printf("%s{\"id\":%d,\"low_key\":%u,\"high_key\":%u,\"low_vel\":%u,\"high_vel\":%u,\"group\":%u,\"loop_mode\":%d,\"offset\":%u,\"end\":%u,\"loop_start\":%u,\"loop_end\":%u,\"sample_rate\":%u,\"transpose\":%d,\"tune\":%d,\"keycenter\":%d,\"keytrack\":%d,\"attenuation\":%.9g,\"pan\":%.9g,\"filter_fc\":%d,\"filter_q\":%d,\"mod_lfo_pitch\":%d,\"vib_lfo_pitch\":%d,\"mod_env_pitch\":%d,\"mod_lfo_filter\":%d,\"mod_env_filter\":%d,\"mod_lfo_volume\":%.9g,\"mod_lfo_delay\":%.9g,\"mod_lfo_frequency\":%d,\"vib_lfo_delay\":%.9g,\"vib_lfo_frequency\":%d,\"amp\":",i?",":"",id,r->lokey,r->hikey,r->lovel,r->hivel,r->group,r->loop_mode,r->offset,r->end,r->loop_start,r->loop_end,r->sample_rate,r->transpose,r->tune,r->pitch_keycenter,r->pitch_keytrack,r->attenuation,r->pan,r->initialFilterFc,r->initialFilterQ,r->modLfoToPitch,r->vibLfoToPitch,r->modEnvToPitch,r->modLfoToFilterFc,r->modEnvToFilterFc,(double)r->modLfoToVolume,r->delayModLFO,r->freqModLFO,r->delayVibLFO,r->freqVibLFO);
  envelope(&r->ampenv);printf(",\"mod\":");envelope(&r->modenv);printf("}");
 }printf("]}");}printf("]}\n");tsf_close(f);return 0;}
