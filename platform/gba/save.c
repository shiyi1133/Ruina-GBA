#include "engine.h"
#include "storage_codec.h"
#include "balanced.h"
/* v5 packs exact state into ordinary 32 KiB SRAM. v2/v3/v4 stay readable.
 * Failed compression leaves existing SRAM untouched. Checksums detect damage. */
#define SAVE_MAGIC 0x41554952U
static u8 *save_buffer;
#define SAVE_WORKSPACE_SIZE 32768
volatile u32 save_trace[8];
static u32 get32(const u8*p){return p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void put32(u8*p,u32 n){p[0]=n;p[1]=n>>8;p[2]=n>>16;p[3]=n>>24;}
static u32 checksum(const u8*p,unsigned n){u32 h=2166136261U;while(n--){if(!(n&511))audio_service();h^=*p++;h*=16777619U;}return h;}
static int save_impl(int checkpoint){
 volatile u8*sram=(volatile u8*)0x0e000000;unsigned i,saved_depth=vm_background?0:depth,base=28+saved_depth*20,packed,length;
 if(battle_active||saved_depth>32||(!checkpoint&&(depth||!game.save_enabled)))return 0;
 save_buffer=balanced_save_workspace();game.saves++;memset(save_buffer,0,SAVE_WORKSPACE_SIZE);put32(save_buffer,SAVE_MAGIC);put32(save_buffer+4,5);put32(save_buffer+12,RM2K_SAVE_SOURCE);put32(save_buffer+20,sizeof(Game));put32(save_buffer+24,saved_depth);
 for(i=0;i<saved_depth;i++){Frame*f=stack+i;u8*p=save_buffer+28+i*20;put32(p,f->common_id);put32(p+4,f->event_id);put32(p+8,f->page_id);put32(p+12,f->source_map);put32(p+16,f->reader.pos);}
 packed=pack_state_serviced((const u8*)&game,sizeof(Game),save_buffer+base,SAVE_WORKSPACE_SIZE-base,audio_service);
 if(!packed){game.saves--;return 0;}
 length=base+packed;put32(save_buffer+8,length-20);put32(save_buffer+16,checksum(save_buffer+20,length-20));
 save_trace[0]++;save_trace[1]=checksum((const u8*)&game,sizeof(Game));save_trace[7]=vm_background!=0;
 for(i=0;i<4;i++)sram[i]=0;
 for(i=4;i<length;i++){if(!(i&255))audio_service();sram[i]=save_buffer[i];}
 for(i=0;i<4;i++)sram[i]=save_buffer[i];
 for(i=0;i<length;i++){if(!(i&255))audio_service();if(sram[i]!=save_buffer[i]){game.saves--;return 0;}}
 return 1;
}
int save_game(void){return save_impl(0);}
int save_checkpoint(void){return save_impl(1);}
int load_game(void){
 save_buffer=balanced_save_workspace();const volatile u8*sram=(const volatile u8*)0x0e000000;unsigned i,version,size,saved_depth,frame_at;
 for(i=0;i<SAVE_WORKSPACE_SIZE;i++){if(!(i&255))audio_service();save_buffer[i]=sram[i];}
 if(get32(save_buffer)!=SAVE_MAGIC||get32(save_buffer+12)!=RM2K_SAVE_SOURCE)return 0;
 version=get32(save_buffer+4);size=get32(save_buffer+8);
 if(version==5){unsigned bytes=size,base;size=get32(save_buffer+20);saved_depth=get32(save_buffer+24);frame_at=28;base=frame_at+saved_depth*20;
  if(bytes>32748||bytes<8||saved_depth>32||base>bytes+20||size!=sizeof(Game)||checksum(save_buffer+20,bytes)!=get32(save_buffer+16))return 0;
  memset(&game,0,sizeof(game));extended_state_defaults();if(!unpack_state_serviced(save_buffer+base,bytes+20-base,(u8*)&game,size,audio_service))return 0;
 }else{
  if((version==2||version==3)?size!=31184:version!=4||size!=32068)return 0;
  if(20+size+4+32*20>SAVE_WORKSPACE_SIZE)return 0;
  saved_depth=get32(save_buffer+20+size);frame_at=24+size;
  if(saved_depth>32||checksum(save_buffer+20,size+4+32*20)!=get32(save_buffer+16))return 0;
  memset(&game,0,sizeof(game));extended_state_defaults();memcpy(&game,save_buffer+20,size);
  if(version<4)for(i=0;i<144;i++)game.upper_substitutions[i]=i;
 }
 if(game.party_count<1||game.party_count>4||game.map<1||game.map>=RM2K_MAP_COUNT)return 0;
 for(i=0;i<(unsigned)game.party_count;i++)if(game.party[i]<1||game.party[i]>MAX_ACTOR)return 0;
 depth=halt_code=engine_clock_paused=0;parallel_reset();presentation_reset();event_position_index_reset();scene_image=current_face=-1;
 if(version==2){u8 old[128];memcpy(old,game.erased_events,sizeof(old));memset(game.erased_events,0,sizeof(game.erased_events));for(i=1;i<128;i++)if(old[i])erase_event(i);if(!saved_depth)game.menu_enabled=1;}
 save_trace[2]=checksum((const u8*)&game,sizeof(Game));save_trace[3]=version;save_trace[4]=sizeof(Game);save_trace[5]=size;save_trace[6]=saved_depth;
 for(i=0;i<saved_depth;i++){const u8*p=save_buffer+frame_at+i*20;unsigned common=get32(p),event=get32(p+4),page=get32(p+8),map=get32(p+12),position=get32(p+16);LcfSpan cmd;
  if(common){if(common>MAX_COMMON)return 0;cmd=field(common_data[common],22);}else {LcfSpan e,pg;if(map<1||map>=RM2K_MAP_COUNT)return 0;e=entry(field(map_data(map),81),event);pg=entry(field(e,5),page);if(!pg.data)return 0;cmd=field(pg,52);}
  if(!cmd.data||position>cmd.size)return 0;stack[depth++]=(Frame){{cmd,position,0},event,page,common,map};
 }
 return 1;
}
