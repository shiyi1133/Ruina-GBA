#include "engine.h"
static int cost(int a,int skill){int n=val(skill_data[skill],11,0),i;for(i=1;i<5;i++){int item=game.actors[a].equipment[i];if(item&&val(item_data[item],27,0))return rm2k_skill_cost(n,1);}return rm2k_skill_cost(n,0);}
int map_skill_valid(int a,int skill,int from_item){
    LcfSpan sk=skill_data[skill],effects=field(sk,42),attrs=field(sk,44);int type=val(sk,8,0),scope=val(sk,12,0),i,j;
    if(a<1||a>MAX_ACTOR||game.actors[a].hp<=0)return 0;
    if(!from_item){
        if(game.actors[a].mp<cost(a,skill))return 0;
        if(!val(sk,45,0))for(i=1;i<=(int)attrs.size;i++)if(attrs.data[i-1]&&val(entry(db[17],i),2,0)==0){int found=0;for(j=0;j<2;j++){int item=game.actors[a].equipment[j];LcfSpan wa=field(item_data[item],66);if(item&&val(item_data[item],3,0)==1&&i<=(int)wa.size&&wa.data[i-1])found=1;}if(!found)return 0;}
        for(i=1;i<=42;i++)if(has_state(a,i)){LcfSpan st=entry(db[18],i);if(val(st,41,0)&&val(sk,21,0)>=val(st,42,0))return 0;if(val(st,43,0)&&val(sk,22,3)>=val(st,44,0))return 0;}
    }
    if(type==3)return val(sk,18,1);
    if(type!=0)return 0;
    if(scope<2)return 0;
    if(from_item||val(sk,31,0)||val(sk,32,0))return 1;
    if(scope==2)return 0;
    for(i=1;i<=(int)effects.size;i++)if(effects.data[i-1]&&val(entry(db[18],i),2,0)==1)return 1;
    return 0;
}
static int stat_with_states(int aid,int which){int n=stat(aid,which),sid,half=0,dbl=0;for(sid=1;sid<=42;sid++)if(has_state(aid,sid)){LcfSpan st=entry(db[18],sid);if(val(st,31+which-2,0)){if(val(st,30,0)==0)half=1;if(val(st,30,0)==1)dbl=1;}}return half!=dbl?(half?(n/2?n/2:1):n*2):n;}
static int effect(int source,int target,int skill){
    LcfSpan sk=skill_data[skill],attrs=field(sk,44),ranks=field(actor_data[target],74);int n=val(sk,24,0),physical=-1,magical=-1,id,i,var;
    n=rm2k_skill_base(n,val(sk,21,0),val(sk,22,3),stat_with_states(source,2),stat_with_states(source,4),0,0,0,0);
    for(id=1;id<=(int)attrs.size;id++)if(attrs.data[id-1]){LcfSpan attr=entry(db[17],id);int rank=id<=(int)ranks.size?ranks.data[id-1]:2,boost=0,rate;static const int defaults[5]={200,150,100,50,0};for(i=1;i<5;i++){int item=game.actors[target].equipment[i];LcfSpan set=field(item_data[item],66);if(item&&val(item_data[item],3,0)!=1&&id<=(int)set.size&&set.data[id-1])boost=1;}rank=clamp(rank+boost,0,4);rate=val(attr,11+rank,defaults[rank]);if(val(attr,2,0)==0){if(rate>physical)physical=rate;}else if(rate>magical)magical=rate;}
    if(physical>=0)n=n*physical/100;if(magical>=0)n=n*magical/100;var=val(sk,23,4);{int adj=rm2k_variance_range(n,var);n=rm2k_variance(n,var,adj?random_n(adj+1):0);}return n;
}
int use_map_skill(int actor,int skill,int target,int from_item){
    LcfSpan sk=skill_data[skill],cure=field(sk,42);int type=val(sk,8,0),scope=val(sk,12,0),used=0,i;
    if(!map_skill_valid(actor,skill,from_item))return 0;
    if(type==3){int id=val(sk,13,1);if(id<1||id>MAX_SWITCH){fault(9510);return 0;}game.switches[id]=1;used=1;}
    else if(type==0){for(i=0;i<game.party_count;i++){int aid=game.party[i],sid,revived=0,change=0,n;Actor*a=&game.actors[aid];
        if(scope==2&&aid!=actor)continue;if(scope==3&&aid!=target)continue;
        n=effect(actor,aid,skill);
        for(sid=1;sid<=(int)cure.size;sid++)if(cure.data[sid-1]){if(val(sk,20,0)){if(!has_state(aid,sid))change=1;set_state(aid,sid,1);}else {if(sid==1&&has_state(aid,1))revived=1;if(has_state(aid,sid))change=1;set_state(aid,sid,0);}}
        if(n>0&&a->hp>0){if(val(sk,31,0)&&a->hp<stat(aid,0)){a->hp=clamp(a->hp+n-revived,1,stat(aid,0));change=1;}else if(revived&&!val(sk,31,0)){a->hp=clamp(stat(aid,0)*n/100,1,stat(aid,0));change=1;}if(val(sk,32,0)&&a->mp<stat(aid,1)){a->mp=clamp(a->mp+n,0,stat(aid,1));change=1;}}
        used|=change;
    }}
    if(used&&!from_item)game.actors[actor].mp=clamp(game.actors[actor].mp-cost(actor,skill),0,stat(actor,1));return used;
}
void field_skill_menu(void){int actor=party_select();u16 ids[MAX_SKILL];int count=0,sel=0,top=0,i,dirty=1;if(!actor)return;
    for(i=1;i<=MAX_SKILL;i++)if(learned(actor,i)){int type=val(skill_data[i],8,0),scope=val(skill_data[i],12,0);if((type==3&&val(skill_data[i],18,1))||(type==0&&scope>=2))ids[count++]=i;}
    if(!count){describe("当前没有可在地图上直接使用的特技。探索能力会由事件自动检查。");return;}
    for(;;){unsigned k;debug_state[15]=15;debug_state[14]=ids[sel];debug_state[13]=actor;if(dirty){draw_scene();box(3,18,234,140,11);rect(3,18,234,140,6);draw_text(10,23,game.actors[actor].name,2,210);if(sel<top)top=sel;if(sel>=top+5)top=sel-4;
        for(i=top;i<count&&i<top+5;i++){LcfSpan s=field(skill_data[ids[i]],1);char name[128];int n=s.size<127?s.size:127;memcpy(name,s.data,n);name[n]=0;if(i==sel)box(7,42+(i-top)*18,226,16,8);draw_text(12,44+(i-top)*18,name,map_skill_valid(actor,ids[i],0)?1:6,185);draw_num(202,44+(i-top)*18,cost(actor,ids[i]),6);}draw_text(10,142,"A使用 L说明 B返回",6,218);flip();dirty=0;}
        k=wait_frame();if(k&KEY_B){debug_state[15]=0;return;}if(k&KEY_UP){sel=(sel+count-1)%count;dirty=1;}if(k&KEY_DOWN){sel=(sel+1)%count;dirty=1;}if(k&KEY_L){message(field(skill_data[ids[sel]],2));dirty=1;}
        if(k&KEY_A){int skill=ids[sel],scope=val(skill_data[skill],12,0),target=scope==3?party_select():actor;if(!target&&scope==3)continue;if(!use_map_skill(actor,skill,target,0))describe("没有产生效果，MP没有消耗。");debug_state[15]=0;return;}
    }
}
