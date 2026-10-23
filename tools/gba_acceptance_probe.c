/* Read-only GBA acceptance driver: genuine keys, screenshots, ordinary saves,
 * memory observations and captured emulated audio. No state or memory editing.
 * mGBA is independently installed; this harness does not change its core.
 */
#include <mgba/flags.h>
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba/core/log.h>
#include <mgba/core/timing.h>
#include <mgba-util/audio-buffer.h>
#include <mgba-util/vfs.h>
#include <mgba/internal/arm/arm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static void quiet(struct mLogger*l,int c,enum mLogLevel level,const char*fmt,va_list a){(void)l;(void)c;if(level==mLOG_FATAL||level==mLOG_ERROR){vfprintf(stderr,fmt,a);fputc('\n',stderr);}}
static void put32(FILE*f,unsigned n){for(int i=0;i<4;i++)fputc((n>>(8*i))&255,f);}
static void wavheader(FILE*f,unsigned bytes,unsigned rate){rewind(f);fwrite("RIFF",1,4,f);put32(f,bytes+36);fwrite("WAVEfmt ",1,8,f);put32(f,16);fwrite("\1\0\2\0",1,4,f);put32(f,rate);put32(f,rate*4);fwrite("\4\0\20\0data",1,8,f);put32(f,bytes);}
static void audio(struct mCore*c,FILE*f,unsigned*bytes){int16_t samples[4096*2];struct mAudioBuffer*b=c->getAudioBuffer(c);size_t n=mAudioBufferRead(b,samples,4096);if(f){fwrite(samples,4,n,f);*bytes+=n*4;}}
int main(int argc,char**argv){if(argc<2)return 2;struct mLogger log={.log=quiet};mLogSetDefaultLogger(&log);struct mCore*c=mCoreFind(argv[1]);if(!c||!c->init(c))return 3;mCoreInitConfig(c,"ruina-gba-acceptance");mCoreConfigSetDefaultIntValue(&c->config,"volume",256);mCoreLoadConfig(c);c->setAudioBufferSize(c,4096);mColor*p=calloc(256*256,sizeof(mColor));c->setVideoBuffer(c,p,256);if(!mCoreLoadFile(c,argv[1]))return 4;if(argc>2&&!mCoreLoadSaveFile(c,argv[2],true))return 5;c->reset(c);setvbuf(stdout,NULL,_IOLBF,0);puts("READY");char line[4096],op[32],path[3072];FILE*record=NULL;unsigned bytes=0;
 while(fgets(line,sizeof(line),stdin)){unsigned n=0,k=0,a=0;if(sscanf(line,"%31s",op)!=1)continue;
 if(!strcmp(op,"frames")){sscanf(line,"%*s %u %x",&n,&k);c->setKeys(c,k);for(unsigned i=0;i<n;i++){c->runFrame(c);audio(c,record,&bytes);}c->setKeys(c,0);printf("FRAME %u\n",c->frameCounter(c));}
 else if(!strcmp(op,"read")){sscanf(line,"%*s %x %x",&a,&n);for(unsigned i=0;i<n;i++)printf("%02X",c->busRead8(c,a+i));puts("");}
 else if(!strcmp(op,"timing")){printf("TIMING %d %d %u %llu\n",c->frequency(c),c->frameCycles(c),c->frameCounter(c),(unsigned long long)mTimingGlobalTime(c->timing));}
 /* Hash the actual completed LCD output, including hardware brightness,
  * instead of treating the VRAM framebuffer as the displayed image. */
 else if(!strcmp(op,"lcdhash")){uint64_t h=1469598103934665603ULL;unsigned black=0;for(unsigned y=0;y<160;y++)for(unsigned x=0;x<240;x++){mColor color=p[y*256+x];if(!(color&0x00ffffffU))black++;for(unsigned b=0;b<sizeof(color);b++){h^=(color>>(b*8))&255;h*=1099511628211ULL;}}printf("LCD %016llx %u\n",(unsigned long long)h,black);}
 /* Single-step the unchanged core and observe its PC. No registers, memory,
  * emulator speed settings or ROM bytes are changed by this profiler. */
 else if(!strcmp(op,"profile")||!strcmp(op,"profile_keys")||!strcmp(op,"profile_cycles")){int bycycles=!strcmp(op,"profile_cycles");path[0]=0;if(strcmp(op,"profile")){sscanf(line,"%*s %u %x %3071[^\n]",&n,&k,path);c->setKeys(c,k);}else sscanf(line,"%*s %u %3071[^\n]",&n,path);unsigned *counts=calloc(0x1000000,sizeof(unsigned)),*cycles=bycycles?calloc(0x1000000,sizeof(unsigned)):NULL;unsigned start=c->frameCounter(c),steps=0;struct ARMCore*cpu=c->cpu;
  while(c->frameCounter(c)-start<n){unsigned pc=(unsigned)cpu->gprs[15];uint64_t before=bycycles?mTimingGlobalTime(c->timing):0;if(pc<0x10000000)counts[pc>>4]++;c->step(c);if(bycycles&&pc<0x10000000)cycles[pc>>4]+=(unsigned)(mTimingGlobalTime(c->timing)-before);steps++;if(!(steps&4095))audio(c,record,&bytes);}
  c->setKeys(c,0);if(path[0]){FILE*f=fopen(path,"w");if(f){for(unsigned i=0;i<0x1000000;i++)if(counts[i]){if(bycycles)fprintf(f,"%08x %u %u\n",i<<4,counts[i],cycles[i]);else fprintf(f,"%08x %u\n",i<<4,counts[i]);}fclose(f);}}
  printf("PROFILE %u %u",n,steps);for(unsigned j=0;j<30;j++){unsigned best=0;for(unsigned i=0;i<0x1000000;i++)if(counts[i]>counts[best])best=i;if(!counts[best])break;printf(" %08x:%u",best<<4,counts[best]);counts[best]=0;}puts("");free(counts);free(cycles);}
 /* Observe both CPU stack pointers without sentinel writes or patched RAM. */
 else if(!strcmp(op,"stack")){sscanf(line,"%*s %u %x",&n,&k);c->setKeys(c,k);unsigned start=c->frameCounter(c),steps=0,minsp[32],minpc[32],observed[32]={0};struct ARMCore*cpu=c->cpu;for(unsigned i=0;i<32;i++)minsp[i]=0xffffffffU;
  while(c->frameCounter(c)-start<n){unsigned mode=(unsigned)cpu->privilegeMode&31,sp=(unsigned)cpu->gprs[13];observed[mode]++;if(sp<minsp[mode]){minsp[mode]=sp;minpc[mode]=(unsigned)cpu->gprs[15];}c->step(c);if(!(++steps&4095))audio(c,record,&bytes);}
  c->setKeys(c,0);printf("STACK %u",steps);for(unsigned i=0;i<32;i++)if(observed[i])printf(" %02x:%08x:%08x:%u",i,minsp[i],minpc[i],observed[i]);puts("");}
 else if(!strcmp(op,"shot")){if(sscanf(line,"%*s %3071[^\n]",path)!=1)continue;struct VFile*f=VFileOpen(path,O_CREAT|O_TRUNC|O_WRONLY);int ok=f&&mCoreTakeScreenshotVF(c,f);if(f)f->close(f);printf("SHOT %d\n",ok);}
 else if(!strcmp(op,"savecopy")){if(sscanf(line,"%*s %3071[^\n]",path)!=1)continue;void*b=NULL;size_t size=c->savedataClone(c,&b),written=0;int error=0;FILE*f=NULL;
  if(!size||!b)error=ENODATA;else{errno=0;f=fopen(path,"wb");if(!f)error=errno?errno:EIO;}
  if(f){errno=0;written=fwrite(b,1,size,f);if(written!=size)error=errno?errno:EIO;if(fclose(f)&&!error)error=errno?errno:EIO;}
  free(b);if(error)printf("SAVE_ERROR %d %zu/%zu\n",error,written,size);else printf("SAVE %zu\n",size);}
 else if(!strcmp(op,"record")){if(sscanf(line,"%*s %3071[^\n]",path)!=1)continue;if(record){wavheader(record,bytes,c->audioSampleRate(c));fclose(record);}record=fopen(path,"wb");bytes=0;if(record)wavheader(record,0,c->audioSampleRate(c));printf("RECORD %d\n",record!=NULL);}
 else if(!strcmp(op,"stop")){if(record){wavheader(record,bytes,c->audioSampleRate(c));fclose(record);record=NULL;}printf("AUDIO %u %u\n",bytes,c->audioSampleRate(c));}
 else if(!strcmp(op,"quit"))break;else puts("ERR COMMAND");
 }
 if(record){wavheader(record,bytes,c->audioSampleRate(c));fclose(record);}c->deinit(c);free(p);return 0;}
