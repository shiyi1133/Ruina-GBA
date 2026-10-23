/* Census only: no cartridge behaviour or event state is modified. */
static void character_visibility_census(void){
 int mid,scenario,worst=0,worst_map=0,worst_x=0,worst_y=0;
 for(mid=3;mid<RM2K_MAP_COUNT;mid++)for(scenario=0;scenario<2;scenario++){
  int w,h,cx,cy,i;if(!map_data(mid).data||mid==16||mid==17)continue;engine_init(1);battle_active=0;set_map(mid,0,0);
  if(scenario){memset(game.switches,1,sizeof(game.switches));memset(game.items,99,sizeof(game.items));for(i=1;i<=MAX_VAR;i++)game.vars[i]=999;}
  w=val(map_data(mid),2,20);h=val(map_data(mid),3,15);
  for(cy=0;cy<h*16;cy+=64)for(cx=0;cx<w*16;cx+=64){
   LcfSpan seen[512];int indices[512],directions[512],count=0;
   for(i=1;i<MAX_EVENT;i++){int pid,x,y,j,index,d;LcfSpan p=event_page(i,0,&pid),name;if(!p.data)continue;
    x=event_coordinate(i,0)*16-cx-4;y=event_coordinate(i,1)*16-cy-16;if(x<=-32||y<=-32||x>=240||y>=160)continue;
    name=field(p,21);if(!name.size)continue;index=val(p,22,0);d=val(p,23,2);
    for(j=0;j<count;j++)if(indices[j]==index&&directions[j]==d&&seen[j].size==name.size&&!memcmp(seen[j].data,name.data,name.size))break;
    if(j==count){seen[count]=name;indices[count]=index;directions[count++]=d;}
   }
   if(count>worst){worst=count;worst_map=mid;worst_x=cx;worst_y=cy;}
  }
 }
 fprintf(stderr,"character visibility original pages census: max %d unique poses, map %d camera %d,%d (two controlled switch/variable fixtures)\n",worst,worst_map,worst_x,worst_y);
}
