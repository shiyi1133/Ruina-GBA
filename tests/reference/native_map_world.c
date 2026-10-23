#include "engine.h"
#include "autotile_tables.h"
/* Walking, original touch/action triggers and optional reachable-point routing.
 * Navigation follows the same collision grid; it never teleports the party. */
typedef struct {u32 stamp;short x,y;} DrawStamp;
/* BFS is finished before drawing. Reuse its temporary arrays for the previous
 * rendered state; route() refreshes the snapshots before returning. */
static union {u16 parent[MAX_MAP_CELLS];DrawStamp previous[MAX_EVENT];} event_scratch;
static union {u8 grid[MAX_MAP_CELLS];PictureState previous[MAX_PICTURE+1];} picture_scratch;
static u16*const parent=event_scratch.parent;
static u8*const grid=picture_scratch.grid;
static u16 points[MAX_EVENT],queue[MAX_MAP_CELLS];
static u8 point_access[MAX_EVENT/8];
static void scan_access(void);
static int render_valid,render_camera_x,render_camera_y;
static int draw_left,draw_top,draw_right=240,draw_bottom=160;
static unsigned render_revision,render_root;
static void render_resnapshot(void);
static int base_only,view_focus,view_manual,view_x,view_y;
static int native_coord(int n,int vertical){return world_native_map()?n:vertical?n*2/3:n*3/4;}
int world_native_map(void){return game.map>=3&&!battle_active&&!source_menu_active()&&game.map!=16&&game.map!=17;}
int world_cached_background(void){return base_only;}
int world_picture_is_hud(int slot){
 int i,count=0;if(!world_native_map())return 0;
 for(i=1;i<=slot;i++){PictureState*p=game.pictures+i;
  if(p->image>=0&&!(p->flags&1)&&p->zoom==100&&!p->transparency&&images[p->image].width<=64&&images[p->image].height<=32&&p->red==100&&p->green==100&&p->blue==100&&p->saturation==100)count++;
  else if(i==slot)return 0;
 }return count<=2;
}
int world_view_x(void){int maximum=val(map_data(game.map),2,20)*16-240,x=game.pan_locked?game.camera_lock_x+40:view_manual?view_x:(view_focus?event_coordinate(view_focus,0)*16+8:game.x*16+8)-120;return clamp(x+game.pan_x/16,0,maximum>0?maximum:0)&~7;}
int world_view_y(void){int maximum=val(map_data(game.map),3,15)*16-160,y=game.pan_locked?game.camera_lock_y+40:view_manual?view_y:(view_focus?event_coordinate(view_focus,1)*16+8:game.y*16+8)-80;return clamp(y+game.pan_y/16,0,maximum>0?maximum:0)&~7;}

static void render_clip(int x,int y,int w,int h){draw_left=x;draw_top=y;draw_right=x+w;draw_bottom=y+h;video_clip(x,y,w,h);}
static int stamp_visible(const DrawStamp*s){int x=s->x-(world_native_map()?render_camera_x:0),y=s->y-(world_native_map()?render_camera_y:0);return s->stamp&&x<draw_right&&y<draw_bottom&&x+32>draw_left&&y+32>draw_top;}
void world_render_invalidate(void){render_valid=0;}
static int point_count,path_count,path_map,path_event,path_activate;
volatile u32 world_trace[8];
volatile u32 world_metrics[8];
static int pending_touch,pending_map;
unsigned world_presented_revision;
void world_reset(void){view_focus=view_manual=view_x=view_y=0;render_valid=0;pending_touch=path_event=path_count=0;path_map=game.map;world_presented_revision=~0U;}
void world_queue_touch(int event){pending_touch=event;pending_map=game.map;}
extern volatile unsigned input_sampled;
static int has_commands(LcfSpan p){LcfSpan code=field(p,52);LcfReader r={code,0,0};LcfCommand c;while(r.pos<code.size){if(!lcf_command(&r,&c))return 0;if(c.code&&c.code!=10&&c.code!=RM2K_Comment&&c.code!=RM2K_Comment_2)return 1;}return 0;}
static int scan_points(void){int id;point_count=0;for(id=1;id<MAX_EVENT;id++){int pid;LcfSpan p=event_page(id,0,&pid);if(p.data&&val(p,33,0)==0&&has_commands(p)&&(field(p,21).size||val(p,22,0)>0||game.event_sprite[id]!=65535))points[point_count++]=id;}if(!path_count)scan_access();return point_count;}
static void scan_access(void){
 /* The scene lives in VRAM. Borrow its idle CPU framebuffer for BFS without
  * destroying the dirty-render snapshots or adding a second map allocation. */
 u8*access_grid=video_map_scratch();u16*visited=(u16*)(access_grid+MAX_MAP_CELLS);
 LcfSpan m=map_data(game.map);int w=val(m,2,20),h=val(m,3,15),cells=w*h,head=0,tail=0,i,start=game.x+game.y*w,loop=val(m,11,0);
 static const int dx[4]={0,1,0,-1},dy[4]={-1,0,1,0},bit[4]={8,4,1,2},rev[4]={1,2,8,4};
 memset(point_access,0,sizeof(point_access));
 if(cells<1||cells>MAX_MAP_CELLS||start<0||start>=cells||!map_walk_grid(access_grid,MAX_MAP_CELLS))return;
 for(i=0;i<cells;i++)visited[i]=65535;visited[start]=start;queue[tail++]=start;
 while(head<tail){int cell=queue[head++],x=cell%w,y=cell/w,k;
  for(k=0;k<4;k++){int nx=x+dx[k],ny=y+dy[k],next;if(loop&2)nx=(nx+w)%w;if(loop&1)ny=(ny+h)%h;if(nx<0||nx>=w||ny<0||ny>=h)continue;next=nx+ny*w;
   if(visited[next]!=65535||(!(game.reserved&2)&&(!(access_grid[cell]&bit[k])||!(access_grid[next]&rev[k])||(access_grid[next]&128))))continue;
   visited[next]=cell;queue[tail++]=next;
  }
 }
 for(i=0;i<point_count;i++){int id=points[i],pid,x=event_coordinate(id,0),y=event_coordinate(id,1),reachable=0,k;LcfSpan p=event_page(id,0,&pid);
  if(x<0||x>=w||y<0||y>=h)continue;
  if(val(p,34,0)!=1)reachable=visited[x+y*w]!=65535;
  else for(k=0;k<4;k++){int nx=x+dx[k],ny=y+dy[k];if(loop&2)nx=(nx+w)%w;if(loop&1)ny=(ny+h)%h;if(nx>=0&&nx<w&&ny>=0&&ny<h&&visited[nx+ny*w]!=65535)reachable=1;}
  if(reachable)point_access[id>>3]|=1<<(id&7);
 }
}
static int at_event(int id,int x,int y,int trigger,int same){int pid;LcfSpan p;if(event_coordinate(id,0)!=x||event_coordinate(id,1)!=y)return 0;p=event_page(id,0,&pid);if(!p.data||val(p,33,0)!=trigger||(val(p,34,0)==1)!=same||!has_commands(p))return 0;if((trigger==1||trigger==2)&&game.last_touch_event==id&&game.last_touch_page==pid)return 0;game.last_touch_event=id;game.last_touch_page=pid;push_event(id,pid);return 1;}
int world_touch_event(int x,int y,int same){int id;for(id=1;id<MAX_EVENT;id++)if(at_event(id,x,y,1,same)||at_event(id,x,y,2,same))return 1;return 0;}
static int action_at(int x,int y,int same){int id;for(id=1;id<MAX_EVENT;id++)if(at_event(id,x,y,0,same))return 1;return 0;}
static int counter_at(int x,int y){LcfSpan map=map_data(game.map),tiles=field(map,72),pass=field(entry(db[20],val(map,1,1)),5);int w=val(map,2,20),h=val(map,3,15),n;if(x<0||x>=w||y<0||y>=h)return 0;n=(tiles.data[(x+y*w)*2]|tiles.data[(x+y*w)*2+1]<<8)-10000;if(n<0||n>=144)return 0;n=game.upper_substitutions[n];return n<(int)pass.size&&(pass.data[n]&64);}
static int action(void){int d=event_direction(10001),dx=d==6?1:d==4?-1:0,dy=d==2?1:d==8?-1:0,x=map_round_x(game.x+dx),y=map_round_y(game.y+dy);if(action_at(game.x,game.y,0)||action_at(x,y,1))return 1;if(counter_at(x,y))return action_at(map_round_x(x+dx),map_round_y(y+dy),1);return 0;}
static void face(int dx,int dy){if(!(game.reserved&1))event_set_direction(10001,dx>0?6:dx<0?4:dy>0?2:8);}
static int step(int dx,int dy){int x=map_round_x(game.x+dx),y=map_round_y(game.y+dy),speed=(game.reserved>>4)&7;face(dx,dy);if(!map_step_allowed(10001,game.x,game.y,game.x+dx,game.y+dy,game.reserved&2)){world_touch_event(x,y,1);return 0;}event_relocate(10001,x,y);game.player_step_wait=256>>(1+(speed?speed:4));world_touch_event(x,y,0);return 1;}
static int route(int event,int activate){
 LcfSpan map=map_data(game.map);int w=val(map,2,20),h=val(map,3,15),cells=w*h,same=0,pid,head=0,tail=0,goal=-1,start=game.x+game.y*w,tx=event_coordinate(event,0),ty=event_coordinate(event,1),i;LcfSpan page=event_page(event,0,&pid);
 path_count=0;if(!page.data||cells<1||cells>MAX_MAP_CELLS||start<0||start>=cells||tx<0||tx>=w||ty<0||ty>=h)return 0;same=val(page,34,0)==1;if(!map_walk_grid(grid,MAX_MAP_CELLS)){render_resnapshot();return 0;}
 for(i=0;i<cells;i++)parent[i]=65535;parent[start]=start;queue[tail++]=start;
 while(head<tail){int cell=queue[head++],x=cell%w,y=cell/w,k,distance=(x>tx?x-tx:tx-x)+(y>ty?y-ty:ty-y);static const int dx[4]={0,1,0,-1},dy[4]={-1,0,1,0},bit[4]={8,4,1,2},rev[4]={1,2,8,4};if((!same&&distance==0)||(same&&distance==1)){goal=cell;break;}
  for(k=0;k<4;k++){int nx=x+dx[k],ny=y+dy[k],next;if(val(map,11,0)&2)nx=(nx+w)%w;if(val(map,11,0)&1)ny=(ny+h)%h;if(nx<0||nx>=w||ny<0||ny>=h)continue;next=nx+ny*w;if(parent[next]!=65535)continue;if(!(game.reserved&2)&&(!(grid[cell]&bit[k])||!(grid[next]&rev[k])||(grid[next]&128)))continue;parent[next]=cell;queue[tail++]=next;}
 }
 if(goal<0){render_resnapshot();return 0;}while(goal!=start){queue[path_count++]=goal;goal=parent[goal];}path_map=game.map;path_event=event;path_activate=activate;render_resnapshot();return 1;
}
static int arrive(void){int x,y;if(!path_event)return 0;x=event_coordinate(path_event,0)-game.x;y=event_coordinate(path_event,1)-game.y;if(x||y)face(x,y);path_event=0;if(path_activate)return action();return 0;}
static int original_autorun(void){int id,pid;if(pending_touch){id=pending_touch;pending_touch=0;if(pending_map==game.map){LcfSpan p=event_page(id,0,&pid);if(p.data&&val(p,33,0)==2){push_event(id,pid);return 1;}}}for(id=1;id<=MAX_COMMON;id++){LcfSpan c=common_data[id];if(c.data&&val(c,11,5)==3&&(!val(c,12,0)||sw(val(c,13,1)))){push_common(id);return 1;}}for(id=1;id<MAX_EVENT;id++){LcfSpan p=event_page(id,0,&pid);if(p.data&&val(p,33,0)==3){push_event(id,pid);return 1;}}return world_touch_event(game.x,game.y,0);}
static void sprite(int image,int index,int direction,int x,int y){static const int dirs[4]={8,6,2,4};int k,frame=1,sx,sy;if(image<0)return;for(k=0;k<4&&dirs[k]!=direction;k++){}if(k==4)k=2;sx=(index%4*3+frame)*24;sy=(index/4*4+k)*32;picture_region_scaled(image,native_coord(x*16-render_camera_x-4,0),native_coord(y*16-render_camera_y-16,1),sx,sy,24,32,world_native_map()?24:18,world_native_map()?32:22,1,0,0);}
static void quad(int image,int sx,int sy,int x,int y,int w,int h){int part=chipset_quadrant(image,sx/8,sy/8);if(part>=0)picture_region_scaled(part,x,y,0,0,8,8,w,h,1,0,game.screen_tone);}
static void tile(int image,int id,int upper,int x,int y){int col,row,i,j;if(upper){if(id<48){col=18+id%6;row=8+id/6;}else{col=24+(id-48)%6;row=(id-48)/6;}}else{if(id<96){col=12+id%6;row=id/6;}else{col=18+(id-96)%6;row=(id-96)/6;}}for(j=0;j<2;j++)for(i=0;i<2;i++){int px=native_coord(x*16+i*8-render_camera_x,0),py=native_coord(y*16+j*8-render_camera_y,1),ph=native_coord(y*16+(j+1)*8-render_camera_y,1)-py;quad(image,col*16+i*8,row*16+j*8,px,py,world_native_map()?8:6,ph);}}
static void autotile(int image,int raw,int x,int y){int i,j,block,sub,b=0;if(raw>=4000&&raw<4600){block=(raw-4000)/50;sub=(raw-4000)%50;}else{block=raw/1000;b=(raw%1000)/50;sub=raw%50;if(block>2||b>=16||sub>=47)return;}
 for(j=0;j<2;j++)for(i=0;i<2;i++){int col,row,px=native_coord(x*16+i*8-render_camera_x,0),py=native_coord(y*16+j*8-render_camera_y,1),ph=native_coord(y*16+(j+1)*8-render_camera_y,1)-py;
  if(raw>=4000){int bx=block<4?(block%2)*3:6+(block%2)*3,by=block<4?8+block/2*4:(block-4)/2*4;col=bx+block_d[sub][j][i][0];row=by+block_d[sub][j][i][1];}
  else{int a=block_a[sub][j][i],t=(b>>(j*2+i))&1;if(a<0){if(block==2)t^=3;col=0;row=4+t;}else{col=block==1?3:0;row=a;}if(b&&sub){t=(b>>(j*2+i))&1;if(block==2)t*=2;if(t){col=0;row=4+t;}}}
  quad(image,col*16+i*8,row*16+j*8,px,py,world_native_map()?8:6,ph);
 }
}
static void tiles(int above){LcfSpan map=map_data(game.map),chip=entry(db[20],val(map,1,1)),lower=field(map,71),upper=field(map,72),up=field(chip,5);int image=resource_image(2,field(chip,2)),w=val(map,2,20),h=val(map,3,15),x,y,x0=render_camera_x/16,y0=render_camera_y/16,x1=x0+(world_native_map()?16:21),y1=y0+(world_native_map()?11:16);if(image<0)return;
 /* Invert the final 3/4 by 2/3 screen scale, with a one-tile margin for
  * integer rounding. Keep the same viewport bounds as the full renderer. */
 x0=clamp((render_camera_x+(world_native_map()?draw_left:draw_left*4/3))/16-1,x0,x1);y0=clamp((render_camera_y+(world_native_map()?draw_top:draw_top*3/2))/16-1,y0,y1);
 x1=clamp((render_camera_x+(world_native_map()?draw_right:draw_right*4/3))/16+2,x0,x1);y1=clamp((render_camera_y+(world_native_map()?draw_bottom:draw_bottom*3/2))/16+2,y0,y1);
 for(y=y0;y<h&&y<y1;y++)for(x=x0;x<w&&x<x1;x++){unsigned at=(x+y*w)*2;int raw,id;world_trace[1]=x;world_trace[2]=y;world_trace[3]=above;if(at+1>=lower.size||at+1>=upper.size)continue;raw=lower.data[at]|lower.data[at+1]<<8;if(!above){if(raw>=5000&&raw<5144)tile(image,game.tile_substitutions[raw-5000],0,x,y);else if(raw<3000||(raw>=4000&&raw<4600))autotile(image,raw,x,y);else if(raw>=3000&&raw<3150)tile(image,96+(raw-3000)/50,0,x,y);}id=(upper.data[at]|upper.data[at+1]<<8)-10000;if(id<0||id>=144)continue;id=game.upper_substitutions[id];if(id<(int)up.size&&!!(up.data[id]&16)==above)tile(image,id,1,x,y);}
}
static void draw(void){int id,layer;unsigned t=video_ticks();world_trace[0]=1;draw_background();world_metrics[1]=(video_ticks()-t)&65535;t=video_ticks();world_trace[0]=2;if(game.screen_hidden)return;
 tiles(0);world_metrics[2]=(video_ticks()-t)&65535;t=video_ticks();world_trace[0]=3;
 for(layer=0;layer<3;layer++){for(id=1;id<MAX_EVENT;id++){int pid,image,index;LcfSpan p;if(!stamp_visible(event_scratch.previous+id))continue;p=event_page(id,0,&pid);if(!p.data||val(p,34,0)!=layer)continue;image=game.event_sprite[id]!=65535?game.event_sprite[id]:resource_image(3,field(p,21));index=game.event_sprite[id]!=65535?game.event_sprite_index[id]:val(p,22,0);if(image>=0){if(!base_only)sprite(image,index,event_direction(id),event_coordinate(id,0),event_coordinate(id,1));}else if(!field(p,21).size&&index>0&&index<144){LcfSpan m=map_data(game.map);int atlas=resource_image(2,field(entry(db[20],val(m,1,1)),2));if(atlas>=0)tile(atlas,index,1,event_coordinate(id,0),event_coordinate(id,1));}}
  if(layer==1&&!base_only&&!game.player_hidden&&game.party_count){int a=game.party[0],image=game.player_sprite!=65535?game.player_sprite:game.actor_sprite[a]!=65535?game.actor_sprite[a]:resource_image(3,field(actor_data[a],3)),index=game.player_sprite!=65535?game.player_sprite_index:game.actor_sprite[a]!=65535?game.actor_sprite_index[a]:val(actor_data[a],4,0);sprite(image,index,event_direction(10001),game.x,game.y);rect(native_coord(game.x*16-render_camera_x,0),native_coord(game.y*16-render_camera_y,1),world_native_map()?16:12,world_native_map()?16:11,2);}if(layer==1)tiles(1);
 }
 world_metrics[3]=(video_ticks()-t)&65535;t=video_ticks();world_trace[0]=4;pictures_draw();world_metrics[4]=(video_ticks()-t)&65535;world_trace[0]=5;
 if(game.selected&&!world_native_map()){int x=(event_coordinate(game.selected,0)*16-render_camera_x)*3/4,y=(event_coordinate(game.selected,1)*16-render_camera_y)*2/3;video_map_cursor(x-1,y-1,1);}
 if(game.timer_visible[0]){int sec=timer_seconds(0);box(174,0,66,16,11);draw_num(178,2,sec/60,1);draw_text(202,2,":",1,6);draw_num(211,2,sec%60,1);}
}

typedef struct {short x1,y1,x2,y2;} DirtyRect;
static DirtyRect dirty[8];
static int dirty_count,dirty_full,last_timer=-1;
static DrawStamp last_player;
static void dirty_add(int x,int y,int w,int h){
 int i;DirtyRect r={(short)clamp(x,0,240),(short)clamp(y,0,160),(short)clamp(x+w,0,240),(short)clamp(y+h,0,160)};
 if(r.x1>=r.x2||r.y1>=r.y2)return;
 for(i=0;i<dirty_count;i++)if(r.x1<=dirty[i].x2&&r.x2>=dirty[i].x1&&r.y1<=dirty[i].y2&&r.y2>=dirty[i].y1){
  DirtyRect q=dirty[i];if(q.x1<r.x1)r.x1=q.x1;if(q.y1<r.y1)r.y1=q.y1;if(q.x2>r.x2)r.x2=q.x2;if(q.y2>r.y2)r.y2=q.y2;
  dirty[i]=dirty[--dirty_count];i=-1;
 }
 if(dirty_count==8){dirty_full=1;return;}dirty[dirty_count++]=r;
}
static u32 hash_bytes(u32 hash,const void*data,unsigned n){const u8*p=data;while(n--)hash=(hash^*p++)*16777619U;return hash;}
static unsigned root_stamp(void){
 u32 h=2166136261U;int values[7]={game.map,scene_image,game.panorama,render_camera_x,render_camera_y,game.screen_hidden,game.weather};
 if(world_native_map())values[3]=values[4]=0;h=hash_bytes(h,values,sizeof(values));h=hash_bytes(h,game.screen_tone,4);
 h=hash_bytes(h,game.tile_substitutions,sizeof(game.tile_substitutions));return hash_bytes(h,game.upper_substitutions,sizeof(game.upper_substitutions));
}
static void stamp_change(DrawStamp*old,DrawStamp current,int force,int w,int h){
 if(!force&&(!world_native_map()||((old->stamp|current.stamp)&0x80000000U))&&(old->stamp!=current.stamp||old->x!=current.x||old->y!=current.y)){
  if(old->stamp)dirty_add(old->x-(world_native_map()?render_camera_x:0),old->y-(world_native_map()?render_camera_y:0),w,h);
  if(current.stamp)dirty_add(current.x-(world_native_map()?render_camera_x:0),current.y-(world_native_map()?render_camera_y:0),w,h);
 }
 *old=current;
}
static void picture_dirty(const PictureState*p){
 int w,h,x,y;if(p->image<0||!p->zoom||p->transparency>=100)return;
 w=images[p->image].width*p->zoom/100;h=images[p->image].height*p->zoom/100;x=p->x-w/2;y=p->y-h/2;
 if(p->flags&1){x-=render_camera_x-p->map_x;y-=render_camera_y-p->map_y;}
 if(world_native_map()&&(p->flags&1))dirty_add(x,y,w,h);
 else dirty_add(x*3/4,y*2/3,w*3/4,h*2/3);
}
static int picture_changed(const PictureState*a,const PictureState*b){
 return a->image!=b->image||a->x!=b->x||a->y!=b->y||a->zoom!=b->zoom||a->transparency!=b->transparency||a->flags!=b->flags||a->map_x!=b->map_x||a->map_y!=b->map_y||a->red!=b->red||a->green!=b->green||a->blue!=b->blue||a->saturation!=b->saturation||a->effect!=b->effect||a->power!=b->power;
}
static void collect_changes(int force){
 int id,timer;DrawStamp current;
 dirty_count=dirty_full=0;
 for(id=1;id<MAX_EVENT;id++){
  int pid;LcfSpan p=event_page(id,0,&pid);current=(DrawStamp){0,0,0};
  if(p.data&&(field(p,21).size||val(p,22,0)>0||game.event_sprite[id]!=65535)){
   int values[4]={(int)(unsigned long)p.data,game.event_sprite[id],game.event_sprite_index[id],event_direction(id)};
   current.stamp=(hash_bytes(2166136261U,values,sizeof(values))&0x7fffffffU)|1;if(!field(p,21).size&&game.event_sprite[id]==65535)current.stamp|=0x80000000U;
   current.x=world_native_map()?event_coordinate(id,0)*16-4:(event_coordinate(id,0)*16-render_camera_x-4)*3/4-1;
   current.y=world_native_map()?event_coordinate(id,1)*16-16:(event_coordinate(id,1)*16-render_camera_y-16)*2/3-1;
  }
  stamp_change(event_scratch.previous+id,current,force,world_native_map()?32:21,world_native_map()?48:26);
 }
 current=(DrawStamp){0,0,0};
 if(game.party_count&&!game.player_hidden){
  int a=game.party[0],values[7]={a,game.player_sprite,game.player_sprite_index,game.actor_sprite[a],game.actor_sprite_index[a],event_direction(10001),game.player_hidden};
  current.stamp=hash_bytes(2166136261U,values,sizeof(values))|1;
  current.x=(game.x*16-render_camera_x-4)*3/4-1;current.y=(game.y*16-render_camera_y-16)*2/3-1;
 }
 stamp_change(&last_player,current,force||world_native_map(),21,26);
 for(id=1;id<=MAX_PICTURE;id++){
  PictureState*old=picture_scratch.previous+id,*p=game.pictures+id;
  if(!force&&picture_changed(old,p)&&!world_picture_is_hud(id)){picture_dirty(old);picture_dirty(p);}*old=*p;
 }
 timer=game.timer_visible[0]?timer_seconds(0):-1;
 if(!force&&timer!=last_timer)dirty_add(174,0,66,16);last_timer=timer;
}
static void render_resnapshot(void){
 if(render_valid&&render_revision==video_revision())collect_changes(1);else render_valid=0;
}
static void bitmap_world_redraw(void){
 unsigned t=video_ticks(),f,new_root;
 int i,full;
 render_camera_x=map_display_x();render_camera_y=map_display_y();new_root=root_stamp();
 full=!render_valid||render_revision!=video_revision()||new_root!=render_root;
 collect_changes(full);
 if(full||dirty_full){render_clip(0,0,240,160);draw();}
 else {
  world_metrics[0]++;
  if(!dirty_count){
   if(game.selected)video_map_cursor((event_coordinate(game.selected,0)*16-render_camera_x)*3/4-1,(event_coordinate(game.selected,1)*16-render_camera_y)*2/3-1,1);
   else video_map_cursor(0,0,0);
   video_overlays_present();world_presented_revision=parallel_revision;return;
  }
  for(i=0;i<dirty_count;i++){DirtyRect*r=dirty+i;render_clip(r->x1,r->y1,r->x2-r->x1,r->y2-r->y1);draw();}
 }
 render_clip(0,0,240,160);f=video_ticks();flip();
 world_metrics[6]=(video_ticks()-f)&65535;world_metrics[5]=(video_ticks()-t)&65535;world_metrics[7]++;
 render_valid=1;render_root=new_root;render_revision=video_revision();world_presented_revision=parallel_revision;
}
static void map_objects(void){
 int i;video_map_objects_begin();
 for(i=1;i<MAX_EVENT;i++){
  int pid,image,index;LcfSpan p;DrawStamp*st=event_scratch.previous+i;
  if(!stamp_visible(st))continue;p=event_page(i,0,&pid);if(!p.data)continue;
  image=game.event_sprite[i]!=65535?game.event_sprite[i]:resource_image(3,field(p,21));
  index=game.event_sprite[i]!=65535?game.event_sprite_index[i]:val(p,22,0);
  if(image>=0)video_map_actor(image,index,event_direction(i),event_coordinate(i,0)*16-render_camera_x-4,event_coordinate(i,1)*16-render_camera_y-16);
 }
 if(!game.player_hidden&&game.party_count){int a=game.party[0],image=game.player_sprite!=65535?game.player_sprite:game.actor_sprite[a]!=65535?game.actor_sprite[a]:resource_image(3,field(actor_data[a],3)),index=game.player_sprite!=65535?game.player_sprite_index:game.actor_sprite[a]!=65535?game.actor_sprite_index[a]:val(actor_data[a],4,0);
  video_map_actor(image,index,event_direction(10001),game.x*16-render_camera_x-4,game.y*16-render_camera_y-16);
 }
 for(i=0;i<point_count;i++){int id=points[i];video_map_point(event_coordinate(id,0)*16-render_camera_x+4,event_coordinate(id,1)*16-render_camera_y+4,id==game.selected,(point_access[id>>3]>>(id&7))&1);}
 video_map_player(game.x*16-render_camera_x+4,game.y*16-render_camera_y+4);
 for(i=1;i<=MAX_PICTURE;i++)if(world_picture_is_hud(i)){PictureState*p=game.pictures+i;video_map_hud(p->image,clamp(p->x*3/4-images[p->image].width/2,0,240-images[p->image].width),clamp(p->y*2/3-images[p->image].height/2,0,160-images[p->image].height));}
}
static void native_region(int x,int y,int w,int h){
 if(w<=0||h<=0)return;
 x=x/8*8;y=y/8*8;w=(w+7)/8*8;h=(h+7)/8*8;
 if(x+w>240)w=240-x;if(y+h>160)h=160-y;
 render_clip(x,y,w,h);base_only=1;draw();base_only=0;
 video_map_upload(x,y,w,h,render_camera_x,render_camera_y);
}
void world_redraw(void){
 static int old_x,old_y;
 unsigned t,new_root;int full,dx,dy,i,was_cut;
 if(!world_native_map()||game.screen_hidden){bitmap_world_redraw();return;}
 t=video_ticks();render_camera_x=world_view_x();render_camera_y=world_view_y();new_root=root_stamp();
 full=!render_valid||!video_map_active()||new_root!=render_root||render_revision!=video_revision();
 was_cut=presentation_busy();if(!video_map_active())video_brightness(-16);
 collect_changes(full);dx=render_camera_x-old_x;dy=render_camera_y-old_y;
 if(dx>=240||dx<=-240||dy>=160||dy<=-160)full=1;
 /* A large jump can reuse slots still visible in the old view. Hide that
  * rebuild until the new offsets are committed; ordinary 8/16-pixel scrolls
  * fit the spare ring rows/columns and never need a black cut. */
 if(full||dirty_full||dx>16||dx< -16||dy>32||dy< -32)video_brightness(-16);
 if(full||dirty_full){native_region(0,0,240,160);world_metrics[7]++;}
 else{
  if(dx>0)native_region(240-dx,0,dx,160);else if(dx<0)native_region(0,0,-dx,160);
  if(dy>0)native_region(0,160-dy,240,dy);else if(dy<0)native_region(0,0,240,-dy);
  for(i=0;i<dirty_count;i++){DirtyRect*r=dirty+i;int x=r->x1/8*8,y=r->y1/8*8;native_region(x,y,r->x2-x,r->y2-y);}
  world_metrics[0]++;
 }
 render_clip(0,0,240,160);map_objects();
 {int maxx=val(map_data(game.map),2,20)*16-240,maxy=val(map_data(game.map),3,15)*16-160;
  video_map_present(render_camera_x,render_camera_y,(render_camera_y>0?1:0)|(render_camera_x<maxx?2:0)|(render_camera_y<maxy?4:0)|(render_camera_x>0?8:0));}
 if(!was_cut)video_brightness(0);
 render_valid=1;render_root=new_root;render_revision=video_revision();old_x=render_camera_x;old_y=render_camera_y;
 world_presented_revision=parallel_revision;world_metrics[5]=(video_ticks()-t)&65535;
}
void world_screen(void){
 int map_start=game.map,dirty=1;if(original_autorun())return;if(source_menu_active()){source_menu_screen();return;}scan_points();if(!game.selected&&point_count)game.selected=points[0];if(path_map!=game.map){path_count=path_event=0;path_map=game.map;}
 debug_state[15]=4;world_trace[4]=path_count;
 for(;;){unsigned revision=parallel_revision,generation=ui_generation,k,held,direction_keys;world_trace[4]=path_count;world_trace[5]=path_event;debug_state[0]=0x4d415000;debug_state[9]=game.map;debug_state[10]=game.vars[41];debug_state[11]=game.selected;debug_state[12]=game.party_count;
  if(dirty){world_redraw();dirty=0;}k=wait_frame();held=input_sampled;direction_keys=held|k;
  if(game.map!=map_start)return;
  if(generation!=ui_generation){path_count=path_event=0;return;}
  if(game.player_step_wait)game.player_step_wait--;
  if(k&(KEY_START|KEY_B)){path_count=path_event=0;if(game.menu_enabled)system_menu();return;}
  if((direction_keys&KEY_R)&&(direction_keys&(KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT))){view_x=world_view_x();view_y=world_view_y();view_focus=0;view_manual=1;if(direction_keys&KEY_RIGHT)view_x+=16;if(direction_keys&KEY_LEFT)view_x-=16;if(direction_keys&KEY_DOWN)view_y+=16;if(direction_keys&KEY_UP)view_y-=16;dirty=1;continue;}
  if((k&(KEY_L|KEY_R))==(KEY_L|KEY_R)){if(game.selected&&!route(game.selected,0))describe("无法从当前位置到达这个调查点。");dirty=1;}
  else if((k&(KEY_L|KEY_R))&&point_count){int i;for(i=0;i<point_count;i++)if(points[i]==game.selected)break;if(i==point_count)i=0;else i=(i+point_count+((k&KEY_R)?1:-1))%point_count;game.selected=points[i];view_focus=game.selected;view_manual=0;dirty=1;}
  if(!game.player_step_wait&&(direction_keys&(KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT))){view_focus=view_manual=0;path_count=path_event=0;step(direction_keys&KEY_RIGHT?1:direction_keys&KEY_LEFT?-1:0,direction_keys&KEY_DOWN?1:direction_keys&KEY_UP?-1:0);dirty=1;}
  else if(!game.player_step_wait&&path_count){int w=val(map_data(game.map),2,20),next=queue[--path_count],dx=next%w-game.x,dy=next/w-game.y;if(dx>1)dx=-1;if(dx< -1)dx=1;if(dy>1)dy=-1;if(dy< -1)dy=1;if(!step(dx,dy)){path_count=path_event=0;}dirty=1;}
  if(k&KEY_A){view_focus=view_manual=0;if(game.selected&&game.map!=17&&game.map!=20){if(!route(game.selected,1))describe("无法从当前位置到达这个调查点。");dirty=1;}else action();}
  if(depth){path_count=path_event=0;debug_state[15]=0;return;}
  if(!path_count&&path_event&&!game.player_step_wait){arrive();dirty=1;if(depth){debug_state[15]=0;return;}}
  if(revision!=parallel_revision){dirty=1;if(original_autorun()){path_count=path_event=0;debug_state[15]=0;return;}scan_points();}
 }
}
