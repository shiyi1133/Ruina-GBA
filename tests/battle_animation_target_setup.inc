/* Test-only setup appended to the unchanged production battle translation. */
void animation_fixture_setup(void){int i;allies=4;total=7;turn=1;focus=-1;battle_active=1;memset(units,0,sizeof(units));lcf_index(db[18],states,MAX_STATE+1);lcf_index(db[17],attributes,MAX_ATTRIBUTE+1);game.party_count=4;for(i=0;i<4;i++)game.party[i]=i+1;
 for(i=0;i<7;i++){Unit*u=units+i;int j;u->aid=i<4?i+1:0;u->eid=i<4?0:1;u->hp=u->mp=999;for(j=0;j<6;j++)u->base[j]=999;
  {LcfSpan name=field(i<4?actor_data[i+1]:enemy_data[1],1);memcpy(u->name,name.data,name.size<31?name.size:31);}
  if(i<4){game.actors[i+1].equipment[0]=453;game.actors[i+1].hp=game.actors[i+1].mp=999;}
 }
}
void animation_fixture_skill(int id,int target){use_skill(0,id,target,0);}
