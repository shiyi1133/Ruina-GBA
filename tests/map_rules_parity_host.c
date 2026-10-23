/* Pre-optimization map rules compiled beside the production rules. */
#define main original_integration_main
#include "shared_events_host.c"
#undef main
#define tile_substitute reference_tile_substitute
#define reset_tiles reference_reset_tiles
#define event_position_index_reset reference_event_position_index_reset
#define event_coordinate reference_event_coordinate
#define event_direction reference_event_direction
#define event_relocate reference_event_relocate
#define event_set_direction reference_event_set_direction
#define event_motion_flags reference_event_motion_flags
#define event_set_motion_flags reference_event_set_motion_flags
#define map_terrain reference_map_terrain
#define map_round_x reference_map_round_x
#define map_round_y reference_map_round_y
#define map_display_x reference_map_display_x
#define map_display_y reference_map_display_y
#define map_walk_grid reference_map_walk_grid
#define map_step_allowed reference_map_step_allowed
int reference_event_direction(int id);
#include "reference/map_rules_20261021.c"
#undef tile_substitute
#undef reset_tiles
#undef event_position_index_reset
#undef event_coordinate
#undef event_direction
#undef event_relocate
#undef event_set_direction
#undef event_motion_flags
#undef event_set_motion_flags
#undef map_terrain
#undef map_round_x
#undef map_round_y
#undef map_display_x
#undef map_display_y
#undef map_walk_grid
#undef map_step_allowed

static unsigned edges,queries,grids,cache_edges,mutations;
static u8 reference_grid[MAX_MAP_CELLS],current_grid[MAX_MAP_CELLS];
static void compare_map(void){
 static const int dx[4]={0,1,0,-1},dy[4]={-1,0,1,0};
 int count,k,id,i,w=val(map_data(game.map),2,20),h=val(map_data(game.map),3,15);const u16*ids=map_event_ids(&count);
 reference_event_position_index_reset();
 for(k=0;k<count;k++){id=ids[k];for(i=0;i<2;i++){assert(event_coordinate(id,i)==reference_event_coordinate(id,i));queries++;}assert(event_direction(id)==reference_event_direction(id));assert(event_motion_flags(id)==reference_event_motion_flags(id));queries+=2;}
 assert(map_walk_grid(current_grid,MAX_MAP_CELLS)==reference_map_walk_grid(reference_grid,MAX_MAP_CELLS));assert(!memcmp(current_grid,reference_grid,w*h));grids++;
 path_count=0;scan_points();
 for(i=0;i<w*h;i++){
  int x=i%w,y=i/w;
  assert(map_terrain(x,y)==reference_map_terrain(x,y));queries++;
  for(k=0;k<4;k++){
   int nx=x+dx[k],ny=y+dy[k],a=map_step_allowed(10001,x,y,nx,ny,game.reserved&2),b=reference_map_step_allowed(10001,x,y,nx,ny,game.reserved&2);
   if(a!=b){fprintf(stderr,"map%d (%d,%d) delta%d,%d: current%d old%d\n",game.map,x,y,dx[k],dy[k],a,b);assert(0);}edges++;
   if(walk_valid){int cached=cached_player_edge(x,y,map_round_x(nx),map_round_y(ny),dx[k],dy[k]);assert(!!cached==b);cache_edges++;}
  }
 }
 assert(!halt_code);
}
int main(void){
 int map,scenario,maps=0;
 for(map=1;map<RM2K_MAP_COUNT;map++)for(scenario=0;scenario<2;scenario++){
  int count,k,id,w,h;const u16*ids;engine_init(123);battle_active=0;set_map(map,0,0);if(halt_code){halt_code=0;break;}w=val(map_data(map),2,20);h=val(map_data(map),3,15);if(w*h>MAX_MAP_CELLS)continue;
  if(scenario){memset(game.switches,1,sizeof(game.switches));memset(game.items,99,sizeof(game.items));for(k=1;k<=MAX_VAR;k++)game.vars[k]=999999;game.party_count=4;for(k=0;k<4;k++)game.party[k]=k+1;}
  compare_map();ids=map_event_ids(&count);
  for(k=0;k<count;k+=3){id=ids[k];event_relocate(id,(event_coordinate(id,0)+7)%w,(event_coordinate(id,1)+3)%h);event_set_direction(id,8);event_set_motion_flags(id,event_motion_flags(id)^2);mutations++;}
  tile_substitute(0,1,3);tile_substitute(1,1,3);compare_map();
  /* Cold state restoration must rebuild the eager position and origin caches. */
  {static Game saved;memcpy(&saved,&game,sizeof(game));set_map(map,1,1);memcpy(&game,&saved,sizeof(game));event_position_index_reset();world_reset();compare_map();}
  game.reserved|=2;compare_map();maps++;
 }
 assert(edges>100000&&cache_edges>100000&&queries>100000&&mutations>1000);printf("{\"status\":\"pass\",\"map_scenarios\":%d,\"full_grid_comparisons\":%u,\"original_rule_edges\":%u,\"cached_player_edges\":%u,\"coordinate_direction_terrain_queries\":%u,\"relocated_events\":%u}\n",maps,grids,edges,cache_edges,queries,mutations);return 0;
}
