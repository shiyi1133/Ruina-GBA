#include "engine.h"
extern const u8 original_lcf_start[],original_lcf_end[];
Game game;
LcfSpan db[26],actor_data[MAX_ACTOR+1],item_data[MAX_ITEM+1],skill_data[MAX_SKILL+1],enemy_data[MAX_ENEMY+1],troop_data[MAX_TROOP+1];
LcfSpan common_data[MAX_COMMON+1];
static LcfSpan cached_map,map_events[MAX_EVENT];
static int cached_map_id=-1;
static u8 watched_vars[MAX_VAR+1],watched_switches[MAX_SWITCH+1];
static u16 background_maps[MAX_EVENT],background_commons[MAX_COMMON];
static int background_map_count,background_common_count;
static u16 live_map_ids[MAX_EVENT],autorun_maps[MAX_EVENT],autorun_commons[MAX_COMMON];
static int live_map_count,autorun_map_count,autorun_common_count;
Frame stack[32];
int depth,halt_code;
volatile u32 debug_state[24];
LcfSpan field(LcfSpan o,int id){LcfSpan r={0,0};int ok=lcf_field(o,id,&r);if(ok<0)fault(9001);return r;}
int val(LcfSpan o,int id,int def){LcfSpan f=field(o,id);ru32 n;if(!f.data)return def;if(!lcf_integer(f,&n)){fault(9002);return def;}return (int)n;}
LcfSpan entry(LcfSpan a,int id){LcfSpan r={0,0};if(a.data&&lcf_array(a,id,&r)<0)fault(9003);return r;}
int variable(int id){return id>0&&id<=MAX_VAR?game.vars[id]:0;}
int sw(int id){return id>0&&id<=MAX_SWITCH?game.switches[id]:0;}
int random_n(int n){game.rng=game.rng*1664525U+1013904223U;return n>0?(game.rng>>8)%(unsigned)n:0;}
int event_is_erased(int id){return id>0&&id<MAX_EVENT&&(game.erased_events[id/8]&(1<<(id%8)));}
void erase_event(int id){if(id>0&&id<MAX_EVENT){if(!event_is_erased(id))parallel_revision++;game.erased_events[id/8]|=1<<(id%8);}else fault(9194);}
static void copy_text(char*d,int limit,LcfSpan s){unsigned n=s.size;if(n>=(unsigned)limit)n=limit-1;memcpy(d,s.data,n);d[n]=0;}
int learned(int a,int sk){return a>0&&a<=MAX_ACTOR&&sk>0&&sk<=MAX_SKILL&&(game.actors[a].skills[sk/8]&(1<<(sk%8)));}
void set_learned(int a,int sk,int yes){if(a<1||a>MAX_ACTOR||sk<1||sk>MAX_SKILL){fault(9004);return;}if(yes)game.actors[a].skills[sk/8]|=1<<(sk%8);else game.actors[a].skills[sk/8]&=~(1<<(sk%8));}
int has_state(int a,int s){return a>0&&a<=MAX_ACTOR&&s>0&&s<256&&(game.actors[a].states[s/8]&(1<<(s%8)));}
void set_state(int a,int s,int yes){if(a<1||a>MAX_ACTOR||s<1||s>=256){fault(9005);return;}if(yes){int i,priority=0;game.actors[a].states[s/8]|=1<<(s%8);for(i=1;i<=MAX_STATE;i++)if(has_state(a,i)){int n=val(entry(db[18],i),4,50);if(n>priority)priority=n;}if(has_state(a,1))priority=val(entry(db[18],1),4,50);for(i=1;i<=MAX_STATE;i++)if(has_state(a,i)&&val(entry(db[18],i),4,50)<=priority-10)game.actors[a].states[i/8]&=~(1<<(i%8));if(has_state(a,1))game.actors[a].hp=0;}else {game.actors[a].states[s/8]&=~(1<<(s%8));if(s==1&&game.actors[a].hp==0)game.actors[a].hp=1;}}
int stat(int aid,int which){
    LcfSpan p;int levels,lv,n=0,i;Actor*a;
    if(aid<1||aid>MAX_ACTOR||which<0||which>5){fault(9006);return 0;}
    a=&game.actors[aid];p=field(actor_data[aid],31);levels=p.size/12;lv=clamp(a->level,1,levels)-1;
    if(levels>0){const u8*v=p.data+(which*levels+lv)*2;n=v[0]|v[1]<<8;}n+=a->bonus[which];
    if(which>=2)for(i=0;i<5;i++)if(a->equipment[i])n+=val(item_data[a->equipment[i]],11+which-2,0);
    return clamp(n,which==1?0:1,999);
}
int actor_effective_stat(int a,int which){int n=stat(a,which),sid,half=0,dbl=0;if(which<2)return n;for(sid=1;sid<=MAX_STATE;sid++)if(has_state(a,sid)){LcfSpan st=entry(db[18],sid);if(val(st,31+which-2,0)){if(val(st,30,0)==0)half=1;else if(val(st,30,0)==1)dbl=1;}}return half!=dbl?(half?(n/2?n/2:1):n*2):n;}
int actor_query(int a,int type){Actor*s;int current;if(battle_actor_query(a,type,&current))return current;if(a<1||a>MAX_ACTOR)return 0;s=&game.actors[a];if(type==0)return s->level;if(type==1)return s->exp;if(type==2)return s->hp;if(type==3)return s->mp;if(type>=4&&type<=9)return actor_effective_stat(a,type-4);if(type>=10&&type<=14)return s->equipment[type-10];fault(9020+type);return 0;}
void actor_level(int aid,int lv){
    LcfSpan list=field(actor_data[aid],63);LcfReader r={list,0,0};ru32 count=0,i,key;Actor*a=&game.actors[aid];int old=a->level;a->level=clamp(lv,1,val(actor_data[aid],8,50));
    if(list.data&&!lcf_number(&r,&count)){fault(9030);return;}
    for(i=0;i<count;i++){LcfSpan l;int level;if(!lcf_next_entry(&r,&key,&l)){fault(9031);return;}level=val(l,1,1);if(level>old&&level<=a->level)set_learned(aid,val(l,2,1),1);}
    a->hp=clamp(a->hp,0,stat(aid,0));a->mp=clamp(a->mp,0,stat(aid,1));
    if(a->level>old&&a->exp<actor_next_xp(aid,a->level-1))a->exp=actor_next_xp(aid,a->level-1);
    else if(a->level<old&&a->exp>=actor_next_xp(aid,a->level))a->exp=actor_next_xp(aid,a->level-1);
}
int actor_next_xp(int aid,int level){
    return rm2k_exp(val(actor_data[aid],41,30),val(actor_data[aid],42,30),val(actor_data[aid],43,0),level);
}
void actor_exp(int aid,int exp){Actor*a=&game.actors[aid];int level=a->level,max=val(actor_data[aid],8,50);exp=clamp(exp,0,999999);while(level<max&&exp>=actor_next_xp(aid,level))level++;while(level>1&&exp<actor_next_xp(aid,level-1))level--;a->exp=exp;if(level!=a->level)actor_level(aid,level);}
void fault(int code){if(!halt_code)halt_code=code;debug_state[0]=0x4641554c;debug_state[1]=code;if(depth){debug_state[2]=stack[depth-1].common_id;debug_state[3]=stack[depth-1].event_id;debug_state[4]=stack[depth-1].reader.pos;}}
LcfSpan map_data(int id){char n[]="Map0000.lmu";LcfSpan f={0,0},header,root;if(id==cached_map_id)return cached_map;n[3]='0'+id/1000%10;n[4]='0'+id/100%10;n[5]='0'+id/10%10;n[6]='0'+id%10;if(lcf_resource((LcfSpan){original_lcf_start,original_lcf_end-original_lcf_start},n,&f)!=1){fault(9060);return f;}lcf_root(f,&header,&root);return root;}
static void index_map(void){
    int id;if(!lcf_index(field(cached_map,81),map_events,MAX_EVENT)){fault(9065);return;}
    memset(watched_vars,0,sizeof(watched_vars));memset(watched_switches,0,sizeof(watched_switches));
    /* Foreground common events can be enabled by a parallel event even when
     * their switch is absent from every map-page condition. Wake autorun
     * detection for those live switch changes as well. */
    for(id=0;id<autorun_common_count;id++){int flag=val(common_data[autorun_commons[id]],12,0)?val(common_data[autorun_commons[id]],13,1):0;if(flag>0&&flag<=MAX_SWITCH)watched_switches[flag]=1;}
    background_map_count=autorun_map_count=live_map_count=0;
    for(id=1;id<MAX_EVENT;id++)if(map_events[id].data){LcfSpan pages=field(map_events[id],5);LcfReader r={pages,0,0};ru32 count=0,key,j;int background=0,autorun=0;audio_service();live_map_ids[live_map_count++]=id;if(!pages.data)continue;if(!lcf_number(&r,&count)){fault(9066);return;}
        for(j=0;j<count;j++){LcfSpan p,c;int f,n;if(!(j&7))audio_service();if(!lcf_next_entry(&r,&key,&p)){fault(9067);return;}c=field(p,2);f=val(c,1,0);
            if(val(p,33,0)==4)background=1;
            if(val(p,33,0)==3)autorun=1;
            if(f&1){n=val(c,2,1);if(n>0&&n<=MAX_SWITCH)watched_switches[n]=1;}if(f&2){n=val(c,3,1);if(n>0&&n<=MAX_SWITCH)watched_switches[n]=1;}if(f&4){n=val(c,4,1);if(n>0&&n<=MAX_VAR)watched_vars[n]=1;}
        }
        if(background)background_maps[background_map_count++]=id;
        if(autorun)autorun_maps[autorun_map_count++]=id;
    }
}
int map_watches_variable(int id){return id>0&&id<=MAX_VAR&&watched_vars[id];}
int map_watches_switch(int id){return id>0&&id<=MAX_SWITCH&&watched_switches[id];}
void set_map(int id,int x,int y){game.map=id;game.x=x;game.y=y;game.selected=-1;scene_image=-1;world_reset();game.player_step_wait=0;game.panorama=-1;game.pan_x=game.pan_y=game.pan_target_x=game.pan_target_y=0;reset_tiles();movement_reset();memset(game.moved_events,0,sizeof(game.moved_events));memset(game.extra_positions,0,sizeof(game.extra_positions));memset(game.event_sprite,255,sizeof(game.event_sprite));event_position_index_reset();cached_map_id=-1;cached_map=map_data(id);cached_map_id=id;index_map();map_music(id);parallel_revision++;}
LcfSpan map_event(int id){if(cached_map_id!=game.map){cached_map_id=-1;cached_map=map_data(game.map);cached_map_id=game.map;index_map();}return id>0&&id<MAX_EVENT?map_events[id]:(LcfSpan){0,0};}
const u16*parallel_map_events(int*count){(void)map_event(1);*count=background_map_count;return background_maps;}
const u16*parallel_common_events(int*count){*count=background_common_count;return background_commons;}
const u16*map_event_ids(int*count){(void)map_event(1);*count=live_map_count;return live_map_ids;}
const u16*autorun_map_events(int*count){(void)map_event(1);*count=autorun_map_count;return autorun_maps;}
const u16*autorun_common_events(int*count){*count=autorun_common_count;return autorun_commons;}
static int page_ok(LcfSpan p){
    LcfSpan c=field(p,2);int flags=val(c,1,0);
    if((flags&1)&&!sw(val(c,2,1)))return 0;if((flags&2)&&!sw(val(c,3,1)))return 0;
    if((flags&4)&&variable(val(c,4,1))<val(c,5,0))return 0;
    if((flags&8)&&!game.items[val(c,6,1)])return 0;
    if(flags&16){int i,a=val(c,7,1),ok=0;for(i=0;i<game.party_count;i++)if(game.party[i]==a)ok=1;if(!ok)return 0;}
    if((flags&32)&&timer_seconds(0)>val(c,8,0))return 0;
    return 1;
}
#ifdef RUINA_PREDECODE_PAGES
extern const u8 predecoded_pages_start[];
typedef struct {u32 offset,size,first;u16 count,pad;} PageEvent;
typedef struct {u32 offset,size,minimum,timer;u16 id,flags,switch1,switch2,variable,item,actor,pad;} PageCondition;
static int page_transport(LcfSpan event,int explicit_page,int*pid,LcfSpan*out){
 const u32*h=(const u32*)predecoded_pages_start;unsigned long address=(unsigned long)event.data,base=(unsigned long)original_lcf_start;u32 offset,slot,i;const u16*table;const PageEvent*events;
 if(!event.data||address<base||address-base>=h[2]||h[0]!=0x44475052U)return 0;
 offset=address-base;slot=(offset*2654435761U)&h[3];table=(const u16*)(predecoded_pages_start+h[4]);events=(const PageEvent*)(predecoded_pages_start+h[5]);
 while(table[slot]){
  const PageEvent*e=events+table[slot]-1;
  if(e->offset==offset&&e->size==event.size){
   const PageCondition*pages=(const PageCondition*)(predecoded_pages_start+h[6])+e->first;*out=(LcfSpan){0,0};*pid=explicit_page;
   for(i=0;i<e->count;i++){const PageCondition*p=pages+i;unsigned f=p->flags;
    if(explicit_page){if((int)p->id!=explicit_page)continue;}
    else{
     if((f&1)&&!sw(p->switch1))continue;if((f&2)&&!sw(p->switch2))continue;
     if((f&4)&&variable(p->variable)<(int)p->minimum)continue;
     if((f&8)&&!game.items[p->item])continue;
     if(f&16){int k;for(k=0;k<game.party_count;k++)if(game.party[k]==p->actor)break;if(k==game.party_count)continue;}
     if((f&32)&&timer_seconds(0)>(int)p->timer)continue;
    }
    *out=(LcfSpan){original_lcf_start+p->offset,p->size};*pid=p->id;if(explicit_page)break;
   }return 1;
  }slot=(slot+1)&h[3];
 }return 0;
}
#endif
LcfSpan event_page(int eid,int explicit_page,int*pid){
#ifdef RUINA_PREDECODE_PAGES
 LcfSpan fast;*pid=explicit_page;if(!explicit_page&&event_is_erased(eid)){*pid=0;return(LcfSpan){0,0};}if(page_transport(map_event(eid),explicit_page,pid,&fast))return fast;
#endif
 LcfSpan pages=field(map_event(eid),5),r={0,0};LcfReader reader={pages,0,0};ru32 count,i,key;*pid=0;if(explicit_page){*pid=explicit_page;return entry(pages,explicit_page);}if(!pages.data||event_is_erased(eid))return r;if(!lcf_number(&reader,&count)){fault(9066);return r;}for(i=0;i<count;i++){LcfSpan p;if(!lcf_next_entry(&reader,&key,&p)){fault(9067);return r;}if(page_ok(p)){r=p;*pid=key;}}return r;}
static void push(LcfSpan cmd,int eid,int pid,int cid){if(depth>=32){fault(9062);return;}stack[depth++]=(Frame){{cmd,0,0},eid,pid,cid,game.map};}
void push_event(int eid,int pg){int pid;LcfSpan p=event_page(eid,pg,&pid);if(!p.data){fault(9063);return;}push(field(p,52),eid,pid,0);}
void push_common(int id){LcfSpan c=id>0&&id<=MAX_COMMON?common_data[id]:(LcfSpan){0,0};if(!c.data){fault(9064);return;}push(field(c,22),depth?stack[depth-1].event_id:0,0,id);}
void push_battle_event(LcfSpan commands,int troop,int page){push(commands,0,page,0);if(depth)stack[depth-1].source_map=-troop;}
void extended_state_defaults(void){int i;memset(game.extra_positions,0,sizeof(Game)-((unsigned long)game.extra_positions-(unsigned long)&game));for(i=0;i<=MAX_PICTURE;i++)game.pictures[i].image=-1;for(i=0;i<=MAX_ACTOR;i++){game.actor_sprite[i]=game.actor_face_sheet[i]=65535;}for(i=0;i<MAX_EVENT;i++)game.event_sprite[i]=65535;game.panorama=game.battle_backdrop=-1;game.player_sprite=65535;game.pan_speed=4;for(i=0;i<4;i++)game.screen_tone[i]=100;}
void engine_init(u32 seed){
    int i;LcfSpan file,head,root,pack={original_lcf_start,original_lcf_end-original_lcf_start};
    memset(&game,0,sizeof(game));memset(stack,0,sizeof(stack));memset((void*)debug_state,0,sizeof(debug_state));depth=halt_code=engine_clock_paused=0;parallel_reset();presentation_reset();event_position_index_reset();game.version=1;game.rng=seed;cached_map_id=-1;
    if(lcf_resource(pack,"RPG_RT.ldb",&file)!=1||!lcf_root(file,&head,&root)){fault(9070);return;}
    for(i=11;i<26;i++)db[i]=field(root,i);
    if(!lcf_index(db[11],actor_data,MAX_ACTOR+1)||!lcf_index(db[13],item_data,MAX_ITEM+1)||!lcf_index(db[12],skill_data,MAX_SKILL+1)||!lcf_index(db[14],enemy_data,MAX_ENEMY+1)||!lcf_index(db[15],troop_data,MAX_TROOP+1)||!lcf_index(db[25],common_data,MAX_COMMON+1)){fault(9071);return;}
    background_common_count=autorun_common_count=0;for(i=1;i<=MAX_COMMON;i++)if(common_data[i].data){int trigger=val(common_data[i],11,5);if(trigger==4)background_commons[background_common_count++]=i;else if(trigger==3)autorun_commons[autorun_common_count++]=i;}
    for(i=1;i<=MAX_ACTOR;i++){
        LcfSpan eq;int j;Actor*a=&game.actors[i];if(!actor_data[i].data)continue;
        copy_text(a->name,sizeof(a->name),field(actor_data[i],1));copy_text(a->title,sizeof(a->title),field(actor_data[i],2));
        a->level=0;a->face=val(actor_data[i],16,0);eq=field(actor_data[i],51);
        for(j=0;j<5&&j*2+1<(int)eq.size;j++)a->equipment[j]=eq.data[j*2]|eq.data[j*2+1]<<8;
        actor_level(i,val(actor_data[i],7,1));a->exp=actor_next_xp(i,a->level-1);a->hp=stat(i,0);a->mp=stat(i,1);
    }
    /* Source LDB System party is used before the character-creation event. */
    {LcfSpan system=field(root,22),party=field(system,22);for(i=0;i+1<(int)party.size&&game.party_count<4;i+=2)game.party[game.party_count++]=party.data[i]|party.data[i+1]<<8;}
    game.menu_enabled=1;game.save_enabled=1;extended_state_defaults();
}
