/* Original map-tree inheritance, distinct from a map's tile/event data. */
#include "engine.h"
extern const u8 original_lcf_start[],original_lcf_end[];
LcfSpan map_info(int id){
 LcfSpan file={0,0},header,root;
 if(lcf_resource((LcfSpan){original_lcf_start,original_lcf_end-original_lcf_start},"RPG_RT.lmt",&file)!=1||!lcf_root(file,&header,&root)){fault(9068);return file;}
 return entry(root,id);
}
void map_music(int id){
 int count=0;LcfSpan info=map_info(id);
 while(info.data&&val(info,11,0)==0&&count++<RM2K_MAP_COUNT){int parent=val(info,2,0);if(parent==id)return;id=parent;info=map_info(id);}
 if(info.data&&val(info,11,0)==2){LcfSpan music=field(info,12);int p[4]={val(music,2,0),val(music,3,100),val(music,4,100),val(music,5,50)};audio_command(RM2K_PlayBGM,field(music,1),p);}
}
