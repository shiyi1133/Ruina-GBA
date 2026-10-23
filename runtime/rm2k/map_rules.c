/* RM2000 map queries and event positions, independent of node UI rendering.
 * Reference: pinned Player game_map.cpp and map_data.h, GPL-3.0-or-later. */
#include "engine.h"
void tile_substitute(int layer,int from,int to){if(layer<0||layer>1||from<0||from>=144||to<0||to>=144){fault(9300);return;}{int i,count=layer?144:162;u8*tiles=layer?game.upper_substitutions:game.tile_substitutions;for(i=0;i<count;i++)if(tiles[i]==from)tiles[i]=to;}parallel_revision++;}
void reset_tiles(void){int i;for(i=0;i<162;i++)game.tile_substitutions[i]=i;for(i=0;i<144;i++)game.upper_substitutions[i]=i;memset(game.erased_events,0,sizeof(game.erased_events));game.last_touch_event=game.last_touch_page=0;}
static int resolve_event(int id){return id==10005&&depth?stack[depth-1].event_id:id;}
static EventPosition*slot(int n){return n<MAX_MOVED_EVENT?game.moved_events+n:game.extra_positions+n-MAX_MOVED_EVENT;}
/* The save layout remains unchanged. Zero means unknown, one means original
 * map position, and slot+2 indexes a saved override. */
static u16 position_index[MAX_EVENT];
/* Original event coordinates are immutable map data. A moved-position record
 * still takes precedence; map transfers and SAV loads invalidate this cache. */
static short original_positions[MAX_EVENT][2];
static u8 original_position_valid[MAX_EVENT/8];
static int original_coordinate(int id,int axis){
 unsigned mask=1U<<(id&7);
 if(!(original_position_valid[id>>3]&mask)){
  LcfSpan e=map_event(id);int x=val(e,2,0),y=val(e,3,0);
  if(x< -32768||x>32767||y< -32768||y>32767)return axis?y:x;
  original_positions[id][0]=x;original_positions[id][1]=y;original_position_valid[id>>3]|=mask;
 }return original_positions[id][axis!=0];
}
void event_position_index_reset(void){int i;memset(original_position_valid,0,sizeof(original_position_valid));for(i=0;i<MAX_EVENT;i++)position_index[i]=1;for(i=0;i<MAX_EVENT;i++){EventPosition*p=slot(i);if(p->id>0&&p->id<MAX_EVENT&&position_index[p->id]==1)position_index[p->id]=i+2;}}
static EventPosition*position(int id,int create){
    int i,empty=-1;unsigned cached=position_index[id];
    if(cached>1){EventPosition*p=slot(cached-2);if(p->id==id)return p;position_index[id]=0;}
    if(cached==1&&!create)return 0;
    for(i=0;i<MAX_EVENT;i++){EventPosition*p=slot(i);if(p->id==id){position_index[id]=i+2;return p;}if(!p->id&&empty<0){empty=i;if(cached==1)break;}}
    position_index[id]=1;if(!create)return 0;if(empty<0){fault(9080);return 0;}
    {EventPosition*p=slot(empty);LcfSpan e=map_event(id);p->direction=event_direction(id);p->id=id;p->x=val(e,2,0);p->y=val(e,3,0);position_index[id]=empty+2;return p;}
}
int event_coordinate(int id,int axis){EventPosition*p;id=resolve_event(id);if(id==10001)return axis?game.y:game.x;if(id<=0||id>=MAX_EVENT)return 0;
 /* A cached immutable coordinate also proves that the original event exists.
  * Untouched events need no repeated LCF lookup or moved-slot helper call. */
 if(position_index[id]==1&&(original_position_valid[id>>3]&(1U<<(id&7))))return original_positions[id][axis!=0];
 if(!map_event(id).data)return 0;p=position(id,0);return p?(axis?p->y:p->x):original_coordinate(id,axis);}
int event_direction(int id){EventPosition*p;id=resolve_event(id);if(id==10001)return game.direction?game.direction:2;if(id<=0||id>=MAX_EVENT)return 2;p=position(id,0);if(p)return p->direction;{int pid;LcfSpan pg=event_page(id,0,&pid);int dir=val(pg,23,2);return dir==0?8:dir==1?6:dir==2?2:4;}}
void event_relocate(int id,int x,int y){EventPosition*p;id=resolve_event(id);if(id==10001){if(game.x!=x||game.y!=y){parallel_revision++;game.last_touch_event=game.last_touch_page=0;}game.x=x;game.y=y;return;}if(id<=0||id>=MAX_EVENT||!map_event(id).data)return;p=position(id,1);if(p){if(p->x!=x||p->y!=y)parallel_revision++;p->x=x;p->y=y;}}
void event_set_direction(int id,int d){EventPosition*p;id=resolve_event(id);if(id==10001){if(game.direction!=d)parallel_revision++;game.direction=d;return;}if(id<=0||id>=MAX_EVENT||!map_event(id).data)return;p=position(id,1);if(p){if(p->direction!=d)parallel_revision++;p->direction=d;}}
int event_motion_flags(int id){EventPosition*p;id=resolve_event(id);if(id==10001)return game.reserved;p=id>0&&id<MAX_EVENT?position(id,0):0;return p?p->reserved:0;}
void event_set_motion_flags(int id,int flags){EventPosition*p;id=resolve_event(id);if(id==10001){if(game.reserved!=flags)parallel_revision++;game.reserved=flags;return;}if(id<=0||id>=MAX_EVENT||!map_event(id).data)return;p=position(id,1);if(p){if(p->reserved!=flags)parallel_revision++;p->reserved=flags;}}
int map_terrain(int x,int y){
    LcfSpan map=map_data(game.map),terrain=field(entry(db[20],val(map,1,1)),3),tiles=field(map,71);int width=val(map,2,20),height=val(map,3,15),loop=val(map,11,0),index=0;
    if(!terrain.size)return 1;
    if((loop&2)&&width>0)x=(x%width+width)%width;if((loop&1)&&height>0)y=(y%height+height)%height;
    if(x>=0&&x<width&&y>=0&&y<height){unsigned at=(x+y*width)*2;if(at+1>=tiles.size){fault(9081);return 1;}index=rm2k_chip_index(tiles.data[at]|tiles.data[at+1]<<8);if(index>=18&&index<162)index=18+game.tile_substitutions[index-18];}
    if(index<0||index*2+1>=(int)terrain.size){fault(9082);return 1;}return terrain.data[index*2]|terrain.data[index*2+1]<<8;
}
static int tile_pass(int x,int y,int bit){
    LcfSpan map=map_data(game.map),chip=entry(db[20],val(map,1,1)),lower=field(map,71),upper=field(map,72),lp=field(chip,4),up=field(chip,5);
    int w=val(map,2,20),h=val(map,3,15),at,li,ui,raw,flags,j,pid,event_tile=0;
    int count,k;const u16*ids=map_event_ids(&count);
    if(x<0||y<0||x>=w||y>=h)return 0;
    for(k=0;k<count;k++){int key=ids[k];LcfSpan p;if(event_coordinate(key,0)!=x||event_coordinate(key,1)!=y||(event_motion_flags(key)&2))continue;p=event_page(key,0,&pid);if(p.data&&val(p,34,0)==0&&!field(p,21).size&&game.event_sprite[key]==65535)event_tile=val(p,22,0);}
    if(event_tile>0&&event_tile<(int)up.size&&!(up.data[event_tile]&16))return (up.data[event_tile]&bit)!=0;
    at=(x+y*w)*2;if(at+1>=(int)upper.size||at+1>=(int)lower.size)return 0;
    ui=(upper.data[at]|upper.data[at+1]<<8)-10000;if(ui<0||ui>=144)return 0;ui=game.upper_substitutions[ui];flags=ui<(int)up.size?up.data[ui]:31;
    if(!(flags&bit))return 0;if(!(flags&16))return 1;
    raw=lower.data[at]|lower.data[at+1]<<8;li=rm2k_chip_index(raw);if(li>=18&&li<162)li=18+game.tile_substitutions[li-18];flags=li<(int)lp.size?lp.data[li]:15;
    if(raw>=4000&&raw<4600&&(flags&32)){j=(raw-4000)%50;if((j>=20&&j<=23)||(j>=33&&j<=37)||j==42||j==43||j==45||j==46)return 1;}
    return (flags&bit)!=0;
}
int map_round_x(int x){LcfSpan map=map_data(game.map);int width=val(map,2,20);return (val(map,11,0)&2)&&width>0?(x%width+width)%width:x;}
int map_round_y(int y){LcfSpan map=map_data(game.map);int height=val(map,3,15);return (val(map,11,0)&1)&&height>0?(y%height+height)%height:y;}
int map_display_x(void){if(game.map<1||game.map>=RM2K_MAP_COUNT)return 0;int limit=val(map_data(game.map),2,20)*16-320;if(limit<0)limit=0;return clamp((game.pan_locked?game.camera_lock_x:game.x*16-160)+game.pan_x/16,0,limit);}
int map_display_y(void){if(game.map<1||game.map>=RM2K_MAP_COUNT)return 0;int limit=val(map_data(game.map),3,15)*16-240;if(limit<0)limit=0;return clamp((game.pan_locked?game.camera_lock_y:game.y*16-120)+game.pan_y/16,0,limit);}
int map_walk_grid(u8*grid,unsigned capacity){
 LcfSpan map=map_data(game.map),chip=entry(db[20],val(map,1,1)),lower=field(map,71),upper=field(map,72),lp=field(chip,4),up=field(chip,5);int w=val(map,2,20),h=val(map,3,15),cells=w*h,i;
 if(cells<1||(unsigned)cells>capacity||lower.size<(unsigned)cells*2||upper.size<(unsigned)cells*2)return 0;
 for(i=0;i<cells;i++){int raw=lower.data[i*2]|lower.data[i*2+1]<<8,li=rm2k_chip_index(raw),ui=(upper.data[i*2]|upper.data[i*2+1]<<8)-10000,uf,lf;if(li>=18&&li<162)li=18+game.tile_substitutions[li-18];if(ui<0||ui>=144){grid[i]=0;continue;}ui=game.upper_substitutions[ui];uf=ui<(int)up.size?up.data[ui]:31;lf=li<(int)lp.size?lp.data[li]:15;
  if(raw>=4000&&raw<4600&&(lf&32)){int j=(raw-4000)%50;if((j>=20&&j<=23)||(j>=33&&j<=37)||j==42||j==43||j==45||j==46)lf|=15;}grid[i]=(uf&15)&(uf&16?lf:15);
 }
 {int j,count;const u16*ids=map_event_ids(&count);for(j=0;j<count;j++){int pid,x,y,layer,tile;LcfSpan p;i=ids[j];p=event_page(i,0,&pid);if(!p.data||(event_motion_flags(i)&2))continue;x=event_coordinate(i,0);y=event_coordinate(i,1);if(x<0||x>=w||y<0||y>=h)continue;layer=val(p,34,0);if(layer==1)grid[x+y*w]|=128;
  if(layer==0&&!field(p,21).size&&game.event_sprite[i]==65535){tile=val(p,22,0);if(tile>0&&tile<(int)up.size&&!(up.data[tile]&16))grid[x+y*w]=(grid[x+y*w]&128)|(up.data[tile]&15);}
 }
 }return cells;
}
int map_step_allowed(int id,int x,int y,int nx,int ny,int through){
    LcfSpan map=map_data(game.map);int count,i;const u16*ids=map_event_ids(&count);int w=val(map,2,20),h=val(map,3,15),dx=nx-x,dy=ny-y,bit,reverse,self_layer=1;
    nx=map_round_x(nx);ny=map_round_y(ny);if(nx<0||ny<0||nx>=w||ny>=h)return 0;if(through)return 1;
    if(dx&&dy){return (map_step_allowed(id,x,y,x+dx,y,0)&&map_step_allowed(id,nx,y,nx,y+dy,0))||(map_step_allowed(id,x,y,x,y+dy,0)&&map_step_allowed(id,x,ny,x+dx,ny,0));}
    bit=dx>0?4:dx<0?2:dy>0?1:8;reverse=dx>0?2:dx<0?4:dy>0?8:1;
    if(!tile_pass(x,y,bit)||!tile_pass(nx,ny,reverse))return 0;
    if(id!=10001){int pid;self_layer=val(event_page(id,0,&pid),34,0);}if(self_layer!=1)return 1;
    if(id!=10001&&game.x==nx&&game.y==ny&&!(event_motion_flags(10001)&2))return 0;
    for(i=0;i<count;i++){LcfSpan p;int key=ids[i],pid;if((int)key==id||event_coordinate(key,0)!=nx||event_coordinate(key,1)!=ny||(event_motion_flags(key)&2))continue;p=event_page(key,0,&pid);if(p.data&&val(p,34,0)==1)return 0;}
    return 1;
}
