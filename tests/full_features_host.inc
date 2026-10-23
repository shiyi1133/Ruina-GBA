/* Production map, picture, state and weapon rules, with original LCF data.
 * Controlled fixtures deliberately set story flags; no release ROM is edited. */
#include "../runtime/rm2k/world.c"
#include "storage_codec.h"
static int full_grid_cases,full_route_cases;
static void check_access_cache(void){
 int map,scenario,sample,cases=0,hits=0,blocked=0,changes=0;u8 cached[sizeof(point_access)];
 for(map=1;map<RM2K_MAP_COUNT;map++){
  if(!map_data(map).data)continue;
  for(scenario=0;scenario<2;scenario++){
   int i,w,h;engine_init(567);battle_active=0;set_map(map,0,0);path_count=0;game.party_count=1;game.party[0]=1;
   if(scenario){memset(game.switches,1,sizeof(game.switches));memset(game.items,99,sizeof(game.items));for(i=1;i<=MAX_VAR;i++)game.vars[i]=999;}
   w=val(map_data(map),2,20);h=val(map_data(map),3,15);if(w*h>MAX_MAP_CELLS||w*h<1)continue;
   for(sample=0;sample<16;sample++){
    u32 before;game.x=(sample*137+3)%w;game.y=(sample*71+1)%h;
    if(sample==3){game.reserved^=2;changes++;}
    if(sample==5){game.switches[5]^=1;game.vars[41]++;changes++;}
    if(sample==7){tile_substitute(0,1,3);tile_substitute(1,2,3);changes++;}
    if(sample==9)for(i=1;i<MAX_EVENT;i++)if(map_event(i).data){event_relocate(i,(event_coordinate(i,0)+1)%w,event_coordinate(i,1));event_set_motion_flags(i,event_motion_flags(i)^2);changes++;break;}
    if(sample==11)for(i=1;i<MAX_EVENT;i++)if(map_event(i).data){game.event_sprite[i]=game.event_sprite[i]==65535?0:65535;changes++;break;}
    before=access_reuses;scan_points();memcpy(cached,point_access,sizeof(cached));hits+=access_reuses-before;
    access_valid=0;scan_points();assert(!memcmp(cached,point_access,sizeof(cached)));cases++;
    before=access_reuses;scan_points();assert(access_reuses==before+1);hits++;
    /* Occupied starts are intentionally not reusable from another cell: the
     * player may leave, while ordinary BFS may not re-enter the occupied cell. */
    if(sample==0&&map_walk_grid(grid,MAX_MAP_CELLS))for(i=0;i<w*h;i++)if(grid[i]&128){game.reserved&=~2;game.x=i%w;game.y=i/w;scan_points();assert(!access_reusable);blocked++;break;}
   }
  }
 }
 assert(cases>1000&&hits>=cases&&blocked>0&&changes>0);
 fprintf(stderr,"navigation cache: %d cached vs rebuilt states, %d reuse hits, %d occupied starts, %d dynamic changes\n",cases,hits,blocked,changes);
}
static void check_grid(void){
 engine_init(1);reset_tiles();tile_substitute(0,1,3);tile_substitute(0,3,7);assert(game.tile_substitutions[1]==7&&game.tile_substitutions[3]==7);tile_substitute(1,1,3);tile_substitute(1,3,7);assert(game.upper_substitutions[1]==7&&game.upper_substitutions[3]==7);reset_tiles();assert(game.tile_substitutions[1]==1&&game.upper_substitutions[3]==3);
 static const int maps[]={3,9,17,20,23,26,33,57,68,72};
 static const int dx[]={0,1,0,-1},dy[]={-1,0,1,0},bit[]={8,4,1,2},rev[]={1,2,8,4};int scenario,m;
 for(scenario=0;scenario<2;scenario++)for(m=0;m<10;m++){
  int i,w,h,x,y,k;engine_init(567);battle_active=0;set_map(maps[m],0,0);game.party_count=1;game.party[0]=1;
  if(scenario){memset(game.switches,1,sizeof(game.switches));memset(game.items,99,sizeof(game.items));for(i=1;i<=MAX_VAR;i++)game.vars[i]=999;}
  w=val(map_data(game.map),2,20);h=val(map_data(game.map),3,15);assert(map_walk_grid(grid,MAX_MAP_CELLS)==w*h);
  for(i=0;i<w*h;i+=7){x=i%w;y=i/w;for(k=0;k<4;k++){int nx=map_round_x(x+dx[k]),ny=map_round_y(y+dy[k]),expected=0,actual;if(nx>=0&&nx<w&&ny>=0&&ny<h)expected=(grid[i]&bit[k])&&(grid[nx+ny*w]&rev[k])&&!(grid[nx+ny*w]&128);actual=map_step_allowed(10001,x,y,x+dx[k],y+dy[k],0);if(actual!=!!expected){fprintf(stderr,"grid map%d scenario%d (%d,%d) dir%d: %d != %d\n",game.map,scenario,x,y,k,actual,!!expected);assert(0);}full_grid_cases++;}}
  /* The displayed yellow/gray marker uses the same reachability as routing. */
  scan_points();for(i=0;i<point_count;i++){int id=points[i],reachable=(point_access[id>>3]>>(id&7))&1;assert(route(id,0)==reachable);}
  /* Routing must leave the party in place and obey every crossed edge. */
  for(i=1;i<MAX_EVENT;i++){int ox=game.x,oy=game.y;if(route(i,0)){int at,px=ox,py=oy;assert(game.x==ox&&game.y==oy);for(at=path_count-1;at>=0;at--){int cell=queue[at],nx=cell%w,ny=cell/w;int mx=nx-px,my=ny-py;if(mx>1)mx=-1;if(mx< -1)mx=1;if(my>1)my=-1;if(my< -1)my=1;assert(map_step_allowed(10001,px,py,px+mx,py+my,0));px=nx;py=ny;}full_route_cases++;if(full_route_cases>30)break;}}
  assert(!halt_code);
 }
}
static void check_picture_rules(void){
 int p[16]={1,1,13,14,1,100,0,1,100,100,100,100,0,60,10,1},i;
 engine_init(1);battle_active=0;set_map(23,15,12);game.vars[13]=37;game.vars[14]=91;pictures_show((LcfSpan){(const u8*)"fixture",7},p);assert(!halt_code);assert(game.pictures[1].x==37&&game.pictures[1].y==91&&game.pictures[1].flags==3);
 {unsigned old=parallel_revision;pictures_show((LcfSpan){(const u8*)"fixture",7},p);assert(parallel_revision==old);}
 p[1]=0;p[2]=137;p[3]=31;p[5]=50;p[6]=100;assert(pictures_move(p)==60);for(i=0;i<60;i++)pictures_tick();assert(game.pictures[1].x==137&&game.pictures[1].y==31&&game.pictures[1].zoom==50&&game.pictures[1].transparency==100&&!game.pictures[1].remaining);
 {int pan[6]={2,1,2,4,1};render_screen_command(RM2K_PanScreen,(LcfSpan){0,0},pan);assert(render_screen_wait(RM2K_PanScreen,pan)==16);for(i=0;i<16;i++)pictures_tick();assert(game.pan_x==512);pan[0]=3;render_screen_command(RM2K_PanScreen,(LcfSpan){0,0},pan);assert(render_screen_wait(RM2K_PanScreen,pan)==16);for(i=0;i<16;i++)pictures_tick();assert(!game.pan_x);}
 {int tone[6]={50,100,150,80,10,1};render_screen_command(RM2K_TintScreen,(LcfSpan){0,0},tone);assert(!render_screen_wait(RM2K_TintScreen,tone));assert(game.screen_tone[0]==50&&game.screen_tone[2]==150&&!game.tone_remaining);}
 /* The opening uses MovePicture opacity as well as TintScreen. Static
  * partial transparency survives; alpha-only fades complete without ticks. */
 p[6]=70;assert(!pictures_move(p));assert(game.pictures[1].transparency==70&&!game.pictures[1].remaining);
 p[6]=0;assert(!pictures_move(p));assert(!game.pictures[1].transparency);
 /* Reclassification among the two hardware HUD slots must also remove any
  * former background copy, including a copy currently outside the viewport. */
 for(i=1;i<=MAX_PICTURE;i++)game.pictures[i].image=-1;
 for(i=1;i<=3;i++){PictureState*s=game.pictures+i;memset(s,0,sizeof(*s));s->image=0;s->x=160;s->y=120;s->zoom=100;s->red=s->green=s->blue=s->saturation=100;}
 assert(world_picture_is_hud(1)&&world_picture_is_hud(2)&&!world_picture_is_hud(3));collect_changes(1);
 game.pictures[1].image=-1;collect_changes(0);assert(cache_changed&&world_picture_is_hud(3));
 game.pictures[1]=game.pictures[2];collect_changes(0);assert(cache_changed&&!world_picture_is_hud(3));
 /* Old ordinary saves may contain a partially completed fade. */
 game.tone_remaining=40;game.screen_tone[0]=30;game.tone_target[0]=100;
 game.pictures[1].transparency=50;game.pictures[1].target_transparency=100;game.pictures[1].remaining=30;
 pictures_tick();assert(!game.tone_remaining&&game.screen_tone[0]==100&&game.pictures[1].transparency==100);
 /* Black cuts must not consume RNG, change character values, add transition
  * waits or leave later dialogue hidden under hardware brightness. */
 {int effect[6]={18,0,0,31,20,1},rng=game.rng,hp=game.actors[1].hp;
  assert(sizeof(Game)==39704);
  for(i=-1;i<=19;i++){
   effect[0]=i;
   assert(!presentation_command(RM2K_EraseScreen,effect)&&game.screen_hidden);
   assert(!presentation_busy()&&!host_brightness);
   assert(!presentation_command(RM2K_ShowScreen,effect)&&!game.screen_hidden);
   assert(!presentation_busy()&&!host_brightness);
  }
  assert(game.rng==(u32)rng&&game.actors[1].hp==hp);
  effect[0]=effect[1]=effect[2]=31;assert(presentation_command(RM2K_FlashScreen,effect)==120);
  for(i=0;i<12;i++)presentation_tick();assert(!host_brightness);
  effect[0]=2;effect[1]=2;presentation_command(RM2K_WeatherEffects,effect);assert(game.weather==10);
  presentation_reset();assert(!host_brightness&&game.weather==10);
  effect[0]=0;presentation_command(RM2K_WeatherEffects,effect);assert(!game.weather);
 }
}
static void check_full_battle_rules(void){
 int i,j,dual=0,wide=0;setup(1);units[0].mod[0]=12;assert(actor_query(1,6)==bst(0,2));units[0].hp=1;assert(actor_query(1,2)==1);
 for(i=1;i<=MAX_STATE;i++)assert(state_probability(allies,i)>=0);
 /* Actor and enemy HP/state changes use the same priority and revival rules. */
 inflict(0,1,1);assert(!units[0].hp&&!units[0].mod[0]&&!units[0].charged);inflict(0,1,0);assert(units[0].hp==1);
 for(i=1;i<=MAX_ITEM;i++)if(val(item_data[i],3,0)==1){game.actors[1].equipment[0]=i;game.actors[1].equipment[1]=0;assert(weapon_flag(0,22)==!!val(item_data[i],22,0));assert(weapon_flag(0,23)==!!val(item_data[i],23,0));dual+=weapon_flag(0,22);wide+=weapon_flag(0,23);}
 assert(dual==7&&wide==11);
 /* Every actual source status combination is evaluated with the strongest
  * accuracy reduction, not multiplied repeatedly. */
 for(i=1;i<=MAX_STATE;i++)for(j=1;j<=MAX_STATE;j++){int a=val(states[i],35,100),b=val(states[j],35,100),expected=a<b?a:b;memset(units[0].states,0,sizeof(units[0].states));units[0].states[i]=units[0].states[j]=1;game.actors[1].equipment[0]=0;for(int k=0;k<6;k++)units[0].base[k]=units[allies].base[k]=100;memset(units[allies].states,0,sizeof(units[allies].states));units[allies].base[5]=bst(0,5);assert(hit_chance(0,allies,100,1)==expected);}
 battle_active=0;
}
static void check_realistic_save_capacity(void){
 static u8 packed[32768],unpacked[sizeof(Game)];unsigned n;int i,j;
 engine_init(1);set_map(33,15,12);game.party_count=4;for(i=0;i<4;i++)game.party[i]=i+1;
 for(i=1;i<=MAX_ACTOR;i++){Actor*a=game.actors+i;actor_level(i,val(actor_data[i],8,50));a->hp=stat(i,0);a->mp=stat(i,1);a->exp=actor_next_xp(i,a->level-1);for(j=1;j<=MAX_SKILL;j++)if((i*17+j*31)%5)set_learned(i,j,1);for(j=0;j<5;j++)a->equipment[j]=(i*7+j*11)%MAX_ITEM+1;}
 memset(game.items,99,sizeof(game.items));for(i=1;i<=MAX_SWITCH;i++)game.switches[i]=random_n(2);for(i=1;i<=MAX_VAR;i++)game.vars[i]=random_n(999999);
 for(i=1;i<MAX_EVENT;i++)if(map_event(i).data)event_relocate(i,random_n(30),random_n(40));
 for(i=1;i<=MAX_PICTURE;i++){PictureState*p=game.pictures+i;p->image=i;p->x=p->target_x=random_n(640);p->y=p->target_y=random_n(480);p->zoom=p->target_zoom=100;p->red=p->green=p->blue=p->saturation=100;}
 n=pack_state((const u8*)&game,sizeof(game),packed,sizeof(packed)-28-32*20);assert(n>0);assert(unpack_state(packed,n,unpacked,sizeof(unpacked)));assert(!memcmp(&game,unpacked,sizeof(game)));fprintf(stderr,"expanded late-game fixture: %u raw -> %u packed bytes\n",(unsigned)sizeof(game),n);
}
