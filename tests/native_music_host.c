/* Production fixed-point player, exercised without emulated RAM writes. */
#include <stdio.h>
#include <stdlib.h>
#include "native_midi.h"
static void*load(const char*path){FILE*f=fopen(path,"rb");long n;void*p;if(!f)return 0;fseek(f,0,SEEK_END);n=ftell(f);rewind(f);p=malloc(n);if(fread(p,1,n,f)!=(unsigned long)n)exit(3);fclose(f);return p;}
int main(int argc,char**argv){
 if(argc<3)return 2;
 void*bank=load(argv[1]);void*seq=load(argv[2]);FILE*out=argc>4?fopen(argv[4],"wb"):0;short pcm[NATIVE_MIDI_BLOCK*2];u32 frames,done=0;
 if(!bank||!seq)return 4;
 frames=((u32*)seq)[1];
 if(argc>3&&atoi(argv[3])>0)frames=atoi(argv[3])*16384;
 native_midi_init(bank);native_midi_start(seq);
 while(done<frames){unsigned n=frames-done;if(n>NATIVE_MIDI_BLOCK)n=NATIVE_MIDI_BLOCK;native_midi_render(out?pcm:0,n);if(out)fwrite(pcm,4,n,out);done+=n;}
 if(out)fclose(out);
 printf("{\"frames\":%u,\"events\":%u,\"peak_voices\":%u,\"active_voices\":%u,\"dropped_voices\":%u,\"clipped_samples\":%u,\"loops\":%u,\"position\":%u}\n",done,native_midi_debug[0],native_midi_debug[1],native_midi_debug[2],native_midi_debug[3],native_midi_debug[4],native_midi_debug[5],native_midi_debug[6]);
 free(seq);free(bank);return 0;
}
