/* Independent old selection path against the immutable transport accelerator. */
#define main original_integration_main
#include "shared_events_host.c"
#undef main
static int reference_page_ok(LcfSpan p){
 LcfSpan c=field(p,2);int flags=val(c,1,0);
 if((flags&1)&&!sw(val(c,2,1)))return 0;if((flags&2)&&!sw(val(c,3,1)))return 0;
 if((flags&4)&&variable(val(c,4,1))<val(c,5,0))return 0;
 if((flags&8)&&!game.items[val(c,6,1)])return 0;
 if(flags&16){int i,a=val(c,7,1),ok=0;for(i=0;i<game.party_count;i++)if(game.party[i]==a)ok=1;if(!ok)return 0;}
 if((flags&32)&&timer_seconds(0)>val(c,8,0))return 0;return 1;
}
static LcfSpan reference_page(int eid,int explicit_page,int*pid){
 LcfSpan pages=field(map_event(eid),5),r={0,0};LcfReader reader={pages,0,0};ru32 count,i,key;*pid=0;
 if(explicit_page){*pid=explicit_page;return entry(pages,explicit_page);}if(!pages.data||event_is_erased(eid))return r;assert(lcf_number(&reader,&count));
 for(i=0;i<count;i++){LcfSpan p;assert(lcf_next_entry(&reader,&key,&p));if(reference_page_ok(p)){r=p;*pid=key;}}return r;
}
static unsigned comparisons;
static void same(int id,int page){int a,b;LcfSpan x=reference_page(id,page,&a),y=event_page(id,page,&b);if(a!=b||x.data!=y.data||x.size!=y.size){fprintf(stderr,"map%d event%d explicit%d: old%d %u new%d %u\n",game.map,id,page,a,x.size,b,y.size);assert(0);}assert(!halt_code);comparisons++;}
static void satisfy(LcfSpan p){
 LcfSpan c=field(p,2);int f=val(c,1,0);if(f&1)game.switches[val(c,2,1)]=1;if(f&2)game.switches[val(c,3,1)]=1;
 if(f&4)game.vars[val(c,4,1)]=val(c,5,0);if(f&8)game.items[val(c,6,1)]=1;
 if(f&16){game.party[0]=val(c,7,1);game.party_count=1;}if(f&32)game.timer_frames[0]=val(c,8,0)*60;
}
int main(void){
 int map,scenario,j,total=0,enabled=0;unsigned mutations=0;
 for(map=1;map<RM2K_MAP_COUNT;map++){
  for(scenario=0;scenario<3;scenario++){
   int count;const u16*ids;engine_init(123);battle_active=0;set_map(map,0,0);if(halt_code){halt_code=0;break;}
   if(scenario){memset(game.switches,scenario==1,sizeof(game.switches));memset(game.items,scenario==1?99:1,sizeof(game.items));for(j=1;j<=MAX_VAR;j++)game.vars[j]=scenario==1?999999:random_n(2000)-1000;game.party_count=4;for(j=0;j<4;j++)game.party[j]=j+1;game.timer_frames[0]=scenario==1?0:60*999;}
   ids=map_event_ids(&count);
   for(j=0;j<count;j++){
    int id=ids[j];LcfSpan pages=field(map_event(id),5);LcfReader r={pages,0,0};ru32 n,k,pk;same(id,0);same(id,9999);if(!pages.data)continue;assert(lcf_number(&r,&n));
    for(k=0;k<n;k++){
     LcfSpan p,c;int f;assert(lcf_next_entry(&r,&pk,&p));same(id,pk);satisfy(p);same(id,0);c=field(p,2);f=val(c,1,0);
     if(f&1){game.switches[val(c,2,1)]=0;same(id,0);satisfy(p);mutations++;}
     if(f&2){game.switches[val(c,3,1)]=0;same(id,0);satisfy(p);mutations++;}
     if(f&4){game.vars[val(c,4,1)]=val(c,5,0)-1;same(id,0);satisfy(p);mutations++;}
     if(f&8){game.items[val(c,6,1)]=0;same(id,0);satisfy(p);mutations++;}
     if(f&16){game.party_count=0;same(id,0);satisfy(p);mutations++;}
     if(f&32){game.timer_frames[0]=(val(c,8,0)+1)*60;same(id,0);satisfy(p);mutations++;}
    }
    erase_event(id);same(id,0);same(id,1);game.erased_events[id/8]&=~(1<<(id%8));
   }total++;
  }
 }
 engine_init(123);battle_active=0;set_map(23,0,0);
 {int count,i;const u16*ids=autorun_common_events(&count);for(i=0;i<count;i++){LcfSpan c=common_data[ids[i]];if(val(c,12,0)){assert(map_watches_switch(val(c,13,1)));enabled++;}}}
 assert(comparisons>50000&&mutations>1000&&enabled==22);printf("{\"status\":\"pass\",\"map_scenarios\":%d,\"page_selection_comparisons\":%u,\"condition_mutations\":%u,\"autorun_common_enabling_switches\":%d,\"all_conditions_evaluated_live\":true}\n",total,comparisons,mutations,enabled);return 0;
}
