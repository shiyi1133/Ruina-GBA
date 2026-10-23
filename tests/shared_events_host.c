/* Controlled host fixtures execute unchanged original battle event streams.
 * This is not gameplay acceptance and is never linked into the release ROM. */
#include "engine.h"
#include <assert.h>
#include <stdio.h>
extern int memcmp(const void*,const void*,size_t);
#include "../runtime/rm2k/battle.c"
#include "../runtime/rm2k/parallel.c"
__asm__(".section .rodata\n.global original_lcf_start\noriginal_lcf_start:\n.incbin \"build/original_lcf.bin\"\n.global original_lcf_end\noriginal_lcf_end:\n.previous\n");
#ifdef RUINA_PREDECODE_COMMANDS
__asm__(".section .rodata\n.balign 4\n.global predecoded_commands_start\npredecoded_commands_start:\n.incbin \"build/commands.bin\"\n.previous\n");
#endif
#ifdef RUINA_PREDECODE_PAGES
__asm__(".section .rodata\n.balign 4\n.global predecoded_pages_start\npredecoded_pages_start:\n.incbin \"build/pages.bin\"\n.previous\n");
#endif
int scene_image,current_face;volatile unsigned input_sampled;
void audio_effect(int which){(void)which;}
void audio_service(void){}
int resource_image(int kind,LcfSpan name){(void)kind;return name.size?0:-1;}
int chipset_quadrant(int atlas,int x,int y){(void)atlas;(void)x;(void)y;return -1;}
void picture_region_scaled(int id,int x,int y,int sx,int sy,int sw,int sh,int w,int h,int transparent,int opacity,const u8*tone){(void)id;(void)x;(void)y;(void)sx;(void)sy;(void)sw;(void)sh;(void)w;(void)h;(void)transparent;(void)opacity;(void)tone;}
void source_menu_screen(void){}
static int messages;
int clamp(int n,int low,int high){return n<low?low:n>high?high:n;}
const Image images[1]={{0,1,1}};
const short enemy_image_ids[MAX_ENEMY+1]={0};
static int host_brightness;
unsigned video_ticks(void){return 0;}
unsigned video_revision(void){return 0;}
/* Host rule tests have no GBA graphics surface. These renderer-only hooks
 * preserve their indexed/no-window backend while real-GBA tests exercise
 * the RGB surface and retained native text layer separately. */
int balanced_rgb_mode(void){return 0;}
void balanced_native_ui_end(void){}
void video_clip(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;}
void video_map_cursor(int x,int y,int visible){(void)x;(void)y;(void)visible;}
void video_overlays_present(void){}
int video_map_active(void){return 0;}
void *video_map_scratch(void){static u8 scratch[6144];return scratch;}
void video_map_upload(int x,int y,int w,int h,int cx,int cy){(void)x;(void)y;(void)w;(void)h;(void)cx;(void)cy;}
void video_map_cache_reset(void){}
int video_map_reuse(int x,int y,int w,int h,int cx,int cy){(void)x;(void)y;(void)w;(void)h;(void)cx;(void)cy;return 0;}
void video_map_objects_begin(void){}
int video_map_objects_retry(void){return 0;}
void video_map_scene_reset(void){}
void video_map_actor(int a,int b,int c,int d,int e){(void)a;(void)b;(void)c;(void)d;(void)e;}
void video_map_point(int x,int y,int s,int r){(void)x;(void)y;(void)s;(void)r;}
void video_map_player(int x,int y){(void)x;(void)y;}
void video_map_hud(int i,int x,int y){(void)i;(void)x;(void)y;}
void video_map_present(int x,int y,int d){(void)x;(void)y;(void)d;}
void video_brightness(int n){host_brightness=n;}
void clear(int n){(void)n;}void box(int a,int b,int c,int d,int e){(void)a;(void)b;(void)c;(void)d;(void)e;}
void rect(int a,int b,int c,int d,int e){box(a,b,c,d,e);}void picture(int a,int b,int c,int d,int e,int f,int g,int h){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h;}
int draw_text(int a,int b,const char*c,int d,int e){(void)a;(void)b;(void)c;(void)d;return e;}
void draw_num(int a,int b,int c,int d){(void)a;(void)b;(void)c;(void)d;}void flip(void){}unsigned wait_frame(void){return KEY_A;}
void describe(const char*s){(void)s;messages++;}void message(LcfSpan text){(void)text;messages++;}const char*format_text(LcfSpan text){(void)text;return "";}
int choices(LcfSpan text,int cancel){(void)text;(void)cancel;return 0;}
int choices_selected(LcfSpan text,int cancel,int initial){(void)initial;return choices(text,cancel);}
u32 balanced_scene_stamp(void){return 0;}
void balanced_menu_background(int x,int y,int w,int h){(void)x;(void)y;(void)w;(void)h;draw_scene();}
int face_image(LcfSpan n,int i){(void)n;(void)i;return -1;}
void render_picture_show(LcfSpan n,const int*p){(void)n;(void)p;}void render_picture_erase(int slot){(void)slot;}void render_choice_header(int n){(void)n;}
int battle_background_image(void){return 0;}void draw_scene(void){}void draw_background(void){}void system_menu(void){}
void audio_music(Music m,int fade){(void)m;(void)fade;}void audio_system(int n){(void)n;}void audio_command(int c,LcfSpan n,const int*p){(void)c;(void)n;(void)p;}int audio_midi_ticks(void){return 0;}int audio_played_once(void){return 0;}
int source_menu_active(void){return 0;}int event_input_ready(const int*p,unsigned n){(void)p;(void)n;return 0;}
void event_name_input(int n){(void)n;}int event_number_input(int v,int d){(void)v;(void)d;return 0;}void event_key_input(const int*p,unsigned n){(void)p;(void)n;}
int open_shop(int m,const int*g,int n){(void)m;(void)g;(void)n;return 0;}int save_game(void){return 0;}int save_checkpoint(void){return 0;}
int inventory_select(int n){(void)n;return 0;}int inventory_select_from(int n,int initial){(void)initial;return inventory_select(n);}int party_select(void){return 0;}void consume_item(int n){(void)n;}int map_skill_valid(int a,int s,int f){(void)a;(void)s;(void)f;return 0;}
static void setup(int troop){
 int i,j;LcfSpan members;LcfReader r;ru32 count,key;
 engine_init(123);set_map(23,0,0);game.party_count=1;game.party[0]=1;
 memset(units,0,sizeof(units));allies=1;total=1;turn=0;battle_active=1;battle_aborted=0;
 assert(lcf_index(db[18],states,MAX_STATE+1));assert(lcf_index(db[17],attributes,MAX_ATTRIBUTE+1));
 units[0].aid=1;for(j=0;j<6;j++)units[0].base[j]=stat(1,j);units[0].hp=units[0].base[0];units[0].mp=units[0].base[1];
 members=field(troop_data[troop],2);r=(LcfReader){members,0,0};assert(lcf_number(&r,&count));assert(count<=MAX_BATTLE_ENEMY);
 for(i=0;i<(int)count;i++){LcfSpan member;Unit*u=units+total++;assert(lcf_next_entry(&r,&key,&member));u->eid=val(member,1,1);u->hidden=val(member,4,0);for(j=0;j<6;j++)u->base[j]=val(enemy_data[u->eid],4+j,10);u->hp=u->base[0];u->mp=u->base[1];}
 assert(lcf_index(field(troop_data[troop],11),battle_pages,MAX_BATTLE_PAGE+1));memset(battle_pages_executed,0,sizeof(battle_pages_executed));memset((void*)battle_event_trace,0,sizeof(battle_event_trace));
 push_event(1,1);assert(depth==1);assert(!halt_code);
}
static void check_parallel(void){
 Frame parent,held;Parallel*p;
 engine_init(123);battle_active=0;set_map(23,2,3);game.party_count=1;game.party[0]=1;game.vars[2]=1;
 push_event(1,1);parent=stack[0];
 p=find_context(100,0,0);assert(p);push_common(100);p->depth=1;p->frames[0]=stack[1];depth=1;held=p->frames[0];
 game.switches[5]=0;parallel_tick();assert(p->depth==1&&!memcmp(&p->frames[0],&held,sizeof(held)));assert(depth==1&&!memcmp(&stack[0],&parent,sizeof(parent)));
 game.switches[5]=1;parallel_tick();assert(!halt_code);assert(parallel_trace[0]>0);assert(depth==1&&!memcmp(&stack[0],&parent,sizeof(parent)));
 assert(!p->depth||p->frames[0].reader.pos!=held.reader.pos);
 game.switches[5]=0;held=p->frames[0];{int saved=p->depth;parallel_tick();assert(p->depth==saved&&!memcmp(&p->frames[0],&held,sizeof(held)));}
 parallel_reset();assert(!parallel_active());
}
static void check_movement(void){
 LcfReader r;LcfCommand cmd;int pid,found=0,x,y,i;
 engine_init(123);battle_active=0;set_map(3,3,3);game.reserved=2;
 r=(LcfReader){field(event_page(10,1,&pid),52),0,0};
 while(r.pos<r.span.size){int p[64];assert(lcf_command_values(&r,&cmd,p,64));if(cmd.code==RM2K_MoveEvent&&p[0]==10001&&p[1]==8&&p[2]==0&&p[3]==1&&cmd.parameter_count==5&&p[4]==2){found=1;break;}}
 assert(found);x=game.x;y=game.y;movement_start(&cmd);assert(movement_active());movement_tick();assert(!halt_code);assert(game.x==x&&game.y==y+1&&game.direction==2);
 assert(game.routes[0].wait==8&&game.routes[0].active);
 for(i=0;i<7;i++){movement_tick();assert(game.routes[0].active);}
 movement_tick();assert(!movement_active());
 movement_start(&cmd);assert(movement_active());set_map(3,3,3);assert(!movement_active());
 assert(!map_step_allowed(10001,0,0,-1,0,1));
}
static int checked_ranges,checked_enemy_operands;
static void execute_fragment(LcfSpan code,unsigned start,unsigned end){int base=depth;assert(depth<32);stack[depth++]=(Frame){{{code.data+start,end-start},0,0},0,0,0,game.map};run_events_until(base);assert(!halt_code&&depth==base);}
static void check_switch_stream(LcfSpan code){
 LcfReader r={code,0,0};LcfCommand c;int p[512];
 while(r.pos<r.span.size){unsigned start=r.pos;int i;assert(lcf_command_values(&r,&c,p,512));if(c.code!=RM2K_ControlSwitches||p[0]!=1)continue;
  assert(p[1]>=1&&p[2]<=MAX_SWITCH&&p[1]<=p[2]);for(i=1;i<=MAX_SWITCH;i++)game.switches[i]=i&1;
  execute_fragment(code,start,r.pos);
  for(i=1;i<=MAX_SWITCH;i++){int expected=i&1;if(i>=p[1]&&i<=p[2])expected=p[3]==2?!expected:p[3]==0;assert(game.switches[i]==expected);}
  checked_ranges++;
 }
}
static void check_switch_ranges(void){
 int mid,eid,pid,cid,tid;engine_init(123);battle_active=0;set_map(23,2,3);
 for(cid=1;cid<=MAX_COMMON;cid++)if(common_data[cid].data)check_switch_stream(field(common_data[cid],22));
 for(tid=1;tid<=MAX_TROOP;tid++){LcfSpan pages=field(troop_data[tid],11);LcfReader r={pages,0,0};ru32 count,key,i;if(!pages.data)continue;assert(lcf_number(&r,&count));for(i=0;i<count;i++){LcfSpan page;assert(lcf_next_entry(&r,&key,&page));check_switch_stream(field(page,12));}}
 for(mid=1;mid<RM2K_MAP_COUNT;mid++){LcfSpan map=map_data(mid),events=field(map,81);LcfReader r={events,0,0};ru32 count,key,i;if(!events.data)continue;assert(lcf_number(&r,&count));
  for(i=0;i<count;i++){LcfSpan e,pages;LcfReader pr;ru32 pc,pk,j;assert(lcf_next_entry(&r,&key,&e));eid=key;(void)eid;pages=field(e,5);pr=(LcfReader){pages,0,0};assert(lcf_number(&pr,&pc));for(j=0;j<pc;j++){LcfSpan page;assert(lcf_next_entry(&pr,&pk,&page));pid=pk;(void)pid;check_switch_stream(field(page,52));}}
 }
 assert(checked_ranges==189);
}
static void check_enemy_operands(void){
 int tid;for(tid=1;tid<=MAX_TROOP;tid++){LcfSpan pages=field(troop_data[tid],11);LcfReader r={pages,0,0};ru32 count,key,i;if(!pages.data)continue;assert(lcf_number(&r,&count));
  for(i=0;i<count;i++){LcfSpan page,code;LcfReader cr;ru32 pk;assert(lcf_next_entry(&r,&pk,&page));code=field(page,12);cr=(LcfReader){code,0,0};
   while(cr.pos<cr.span.size){LcfCommand c;int p[512],before,want;unsigned start=cr.pos;assert(lcf_command_values(&cr,&c,p,512));if(c.code!=RM2K_ControlVars||p[4]!=8)continue;
    setup(tid);before=variable(p[1]);want=rm2k_variable_op(before,battle_enemy_query(p[5],p[6]),p[3]);execute_fragment(code,start,cr.pos);assert(variable(p[1])==want);checked_enemy_operands++;
   }
  }
 }assert(checked_enemy_operands==10);
}
#include "full_features_host.inc"
int main(void){
 unsigned parent;
 setup(34);game.switches[155]=1;units[0].hp=1;parent=stack[0].reader.pos;run_battle_pages(34);
 assert(!halt_code);assert(depth==1&&stack[0].reader.pos==parent);assert(!game.switches[155]);assert(units[0].states[10]&&has_state(1,10));assert(battle_event_trace[0]==1);
 run_battle_pages(34);assert(battle_event_trace[0]==1);
 setup(29);parent=stack[0].reader.pos;run_battle_pages(29);assert(!halt_code&&!game.switches[53]);assert(battle_event_trace[0]==1);
 game.switches[53]=1;run_battle_pages(29);assert(!halt_code&&battle_aborted);assert(battle_event_trace[5]==1);assert(depth==1&&stack[0].reader.pos==parent);
 setup(58);units[allies].hp=units[allies].base[0]/5;run_battle_pages(58);assert(!halt_code);assert(battle_event_trace[6]==4);assert(depth==1);
 {int p[5]={0,1,2,25,0},old=units[allies].hp;assert(battle_event_command(RM2K_ChangeMonsterHP,p,(LcfSpan){0,0}));assert(units[allies].hp==old-old/4);
  p[2]=0;p[3]=999999;assert(battle_event_command(RM2K_ChangeMonsterHP,p,(LcfSpan){0,0}));assert(units[allies].hp==1);
  p[4]=1;assert(battle_event_command(RM2K_ChangeMonsterHP,p,(LcfSpan){0,0}));assert(units[allies].hp==0);
  p[1]=0;p[3]=5;assert(battle_event_command(RM2K_ChangeMonsterHP,p,(LcfSpan){0,0}));assert(units[allies].hp==0);
  p[1]=1;p[2]=1;assert(battle_event_command(RM2K_ChangeMonsterCondition,p,(LcfSpan){0,0}));assert(units[allies].hp==1);
 }
 assert(!halt_code);
 check_parallel();check_movement();check_switch_ranges();check_enemy_operands();check_grid();check_access_cache();check_picture_rules();check_full_battle_rules();check_realistic_save_capacity();
 fprintf(stderr,"grid edges checked: %d; routes checked: %d\n",full_grid_cases,full_route_cases);
 puts("{\"status\":\"pass\",\"kind\":\"controlled host integration fixtures using unchanged original event streams\",\"original_troops\":[34,29,58],\"checks\":[\"actor states synchronized with battle units\",\"parent event suspended and preserved\",\"once per turn scheduling\",\"original abort event\",\"original four hidden enemies revealed\",\"zero based monster slots\",\"percent HP uses current HP\",\"nonlethal HP floor\",\"lethal HP and dead-monster no-heal\",\"death state removal revives\",\"original common 100 pauses and resumes its program counter\",\"foreground frame survives parallel execution\",\"original Map3 event10 forced player movement\",\"movement direction, eight-frame step and asynchronous completion\",\"map transfer clears forced routes\",\"through movement still respects non-looping map bounds\"],\"emulator_gameplay\":\"not_run_by_this_fixture\"}");
 return 0;
}
