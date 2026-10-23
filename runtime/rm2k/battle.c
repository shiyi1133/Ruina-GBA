#include "engine.h"
#include "balanced.h"
/* Original RM2000 data drive these rules. Unsupported branches stop explicitly.
 * References: EasyRPG Player algo.cpp / enemyai.cpp, under research/reference/.
 * Formula checks and emulator acceptance are recorded separately in evidence/.
 */
typedef struct {
    int aid,eid,hp,mp,base[6],mod[4],hidden,defend,charged;
    int action,skill,item,target,order;
    u8 states[MAX_STATE+1],age[MAX_STATE+1];
    signed char shifts[MAX_ATTRIBUTE+1];
    char name[32];
} Unit;
static Unit units[MAX_BATTLE_UNIT];
static int allies,total,turn,escape_chance,focus=-1;
static LcfSpan states[MAX_STATE+1],attributes[MAX_ATTRIBUTE+1];
static char logline[1024];
static int logpos;
int battle_active;
static int battle_aborted;
static LcfSpan battle_pages[MAX_BATTLE_PAGE+1];
static u8 battle_pages_executed[MAX_BATTLE_PAGE+1];
volatile u32 battle_event_trace[16];
static int slen(const char*s){int n=0;while(s[n])n++;return n;}
static void log_reset(void){logpos=0;logline[0]=0;}
static void log_span(LcfSpan s){unsigned i;for(i=0;i<s.size&&logpos<1022;i++)logline[logpos++]=s.data[i];logline[logpos]=0;}
static void log_text(const char*s){log_span((LcfSpan){(const u8*)s,slen(s)});}
static void log_num(int value){char b[16];int k=15;unsigned n=value<0?-(unsigned)value:(unsigned)value;b[k]=0;do{b[--k]='0'+n%10;n/=10;}while(n);if(value<0)b[--k]='-';log_text(b+k);}
static void log_show(void){current_face=-1;describe(logline);}
static void term(int n){log_span(field(db[21],n));}
static int active(int n){return n>=0&&n<total&&units[n].hp>0&&!units[n].hidden;}
static int alive_count(int side){int i,n=0;for(i=side?allies:0;i<(side?total:allies);i++)if(active(i))n++;return n;}
static int chance(int percent){return random_n(100)<clamp(percent,0,100);}
static int restriction(int index);
static void inflict(int index,int sid,int yes){
    Unit*u=&units[index];int i,priority=0,before=restriction(index);
    if(sid<1||sid>MAX_STATE){fault(9400);return;}u->states[sid]=yes;u->age[sid]=1;
    if(yes){for(i=1;i<=MAX_STATE;i++)if(u->states[i]&&val(states[i],4,50)>=priority)priority=val(states[i],4,50);
        if(u->states[1])priority=val(states[1],4,50);
        for(i=1;i<=MAX_STATE;i++)if(u->states[i]&&val(states[i],4,50)<=priority-10)u->states[i]=0;
        if(u->states[1]){u->hp=0;memset(u->mod,0,sizeof(u->mod));memset(u->shifts,0,sizeof(u->shifts));u->defend=u->charged=0;}
    }else if(sid==1&&u->hp==0)u->hp=1;
    if((yes&&restriction(index))||(!yes&&before!=restriction(index))){u->action=7;u->charged=u->defend=0;}
}
static int restriction(int index){int s,result=0;for(s=1;s<=MAX_STATE;s++)if(units[index].states[s]){int n=val(states[s],5,0);if(n==1)return 1;if(n==2)result=2;else if(n==3&&!result)result=3;}return result;}
static int bst(int index,int statid){
    Unit*u=&units[index];int i,n=u->base[statid]+(statid>=2?u->mod[statid-2]:0),half=0,dbl=0;
    if(statid<2)return n;n=clamp(n,1,999);
    for(i=1;i<=MAX_STATE;i++)if(u->states[i]&&val(states[i],31+statid-2,0)){if(val(states[i],30,0)==0)half=1;else if(val(states[i],30,0)==1)dbl=1;}
    return half!=dbl?(half?(n/2?n/2:1):n*2):n;
}
static int state_probability(int index,int sid){
    Unit*u=&units[index];LcfSpan ranks=field(u->aid?actor_data[u->aid]:enemy_data[u->eid],u->aid?72:32);int rank=sid<=(int)ranks.size?ranks.data[sid-1]:(u->aid?2:1),mul=100,i;
    if(u->aid)for(i=1;i<5;i++){int id=game.actors[u->aid].equipment[i];LcfSpan item=item_data[id],set=field(item,64);if(id&&val(item,3,0)!=1&&sid<=(int)set.size&&set.data[sid-1]){int m=100-val(item,67,0);if(m<mul)mul=m;}}
    {static const int defs[5]={100,80,60,30,0};rank=clamp(rank,0,4);return val(states[sid],11+rank,defs[rank])*mul/100;}
}
static int attribute_rank(int index,int id){
    Unit*u=&units[index];LcfSpan ranks=field(u->aid?actor_data[u->aid]:enemy_data[u->eid],u->aid?74:34);int rank=id<=(int)ranks.size?ranks.data[id-1]:2,i,boost=0;
    if(u->aid)for(i=1;i<5;i++){int item=game.actors[u->aid].equipment[i];LcfSpan set=field(item_data[item],66);if(item&&val(item_data[item],3,0)!=1&&id<=(int)set.size&&set.data[id-1])boost=1;}
    return clamp(rank+boost+u->shifts[id],0,4);
}
static int attribute_effect(int effect,int target,LcfSpan a,LcfSpan b){
    int id,physical=-1,magical=-1;static const int defaults[5]={200,150,100,50,0};
    for(id=1;id<=MAX_ATTRIBUTE;id++)if((id<=(int)a.size&&a.data[id-1])||(id<=(int)b.size&&b.data[id-1])){int rank=attribute_rank(target,id),rate=val(attributes[id],11+rank,defaults[rank]);if(val(attributes[id],2,0)==0){if(rate>physical)physical=rate;}else if(rate>magical)magical=rate;}
    if(physical>=0)effect=effect*physical/100;if(magical>=0)effect=effect*magical/100;return effect;
}
static int variance(int base,int v){int adj=rm2k_variance_range(base,v);return rm2k_variance(base,v,adj?random_n(adj+1):0);}
static int hit_chance(int source,int target,int base,int physical){
    Unit*u=&units[source];int i;if(!physical)return base;if(restriction(target)==1)return 100;
    {int modifier=100;for(i=1;i<=MAX_STATE;i++)if(u->states[i]){int m=val(states[i],35,100);if(m<modifier)modifier=m;}base=base*modifier/100;}
    if(u->aid){int j;for(j=0;j<2;j++){int item=game.actors[u->aid].equipment[j];if(item&&val(item_data[item],3,0)==1&&val(item_data[item],24,0))return base;}}
    {float src=bst(source,5),tgt=bst(target,5);int result=(int)(100.0f-(100-base)*(1.0f+(tgt/src-1.0f)/2.0f));
     Unit*t=&units[target];if(t->aid)for(i=1;i<5;i++){int item=game.actors[t->aid].equipment[i];if(item&&val(item_data[item],26,0)){result-=25;break;}}return result;}
}
static void hp_change(int index,int delta,int lethal){Unit*u=&units[index];if(!u->hp)return;u->hp=clamp(u->hp+delta,lethal?0:1,u->base[0]);if(!u->hp)inflict(index,1,1);}
static int random_target(int side){int targets[MAX_BATTLE_UNIT],n=0,i;for(i=side?allies:0;i<(side?total:allies);i++)if(active(i))targets[n++]=i;return n?targets[random_n(n)]:-1;}
static void physical_recovery(int target,int strength){int sid;for(sid=1;sid<=MAX_STATE;sid++)if(units[target].states[sid]&&chance(val(states[sid],23,0)*strength/100))inflict(target,sid,0);}
static void damage_message(int target,int delta){log_reset();log_text(units[target].name);if(delta<0){audio_effect(units[target].aid?8:7);log_text("受到");log_num(-delta);term(units[target].aid?22:20);}else if(delta==0)term(units[target].aid?23:21);else{log_text("的HP");log_num(delta);term(29);}log_show();if(delta<0&&!active(target)&&!units[target].aid)audio_effect(10);}
static void normal_attack(int source,int target){
    Unit*u=&units[source];int hit=90,critical=0,bonus=0,dmg,i;LcfSpan attr[2]={{0,0},{0,0}};
    if(target<0||!active(target))return;
    if(u->aid){Actor*a=&game.actors[u->aid];int found=0;for(i=0;i<2;i++){int item=a->equipment[i];if(item&&val(item_data[item],3,0)==1){int h=val(item_data[item],17,90);if(!found||h>hit)hit=h;found=1;if(val(item_data[item],18,0)>bonus)bonus=val(item_data[item],18,0);attr[i]=field(item_data[item],66);}}
        critical=(val(actor_data[u->aid],9,1)?(int)(10000.0f/clamp(val(actor_data[u->aid],10,30),1,9999)):0)+bonus*100;
    }else{hit=val(enemy_data[u->eid],26,0)?70:90;critical=val(enemy_data[u->eid],21,0)?(int)(10000.0f/clamp(val(enemy_data[u->eid],22,30),1,9999)):0;}
    if(!u->aid)audio_effect(6);else {int item=game.actors[u->aid].equipment[0];if(item)animation_battle(val(item_data[item],20,1));}log_reset();log_text(u->name);term(11);log_show();
    if(!chance(hit_chance(source,target,hit,1))){audio_effect(9);log_reset();log_text(units[target].name);term(27);log_show();return;}
    if(units[target].aid)for(i=1;i<5;i++){int item=game.actors[units[target].aid].equipment[i];if(item&&val(item_data[item],25,0))critical=0;}
    if((source<allies)==(target<allies))critical=0;critical=random_n(10000)<critical;dmg=rm2k_normal_base(bst(source,2),bst(target,3));dmg=attribute_effect(dmg,target,attr[0],attr[1]);if(critical)dmg*=3;else if(u->charged)dmg*=2;dmg=variance(dmg,4);dmg=rm2k_defend(dmg,units[target].defend,units[target].aid&&val(actor_data[units[target].aid],24,0));dmg=clamp(dmg,0,999);
    hp_change(target,-dmg,1);damage_message(target,-dmg);
    if(active(target)){physical_recovery(target,100);if(u->aid){int sid;for(sid=1;sid<=MAX_STATE;sid++){int odds=0;for(i=0;i<2;i++){int item=game.actors[u->aid].equipment[i];LcfSpan set=field(item_data[item],64);if(item&&val(item_data[item],3,0)==1&&sid<=(int)set.size&&set.data[sid-1]&&val(item_data[item],67,0)>odds)odds=val(item_data[item],67,0);}if(odds&&chance(odds*state_probability(target,sid)/100))inflict(target,sid,1);}}}
}
static int weapon_flag(int index,int field_id){int i;if(!units[index].aid)return 0;for(i=0;i<2;i++){int id=game.actors[units[index].aid].equipment[i];if(id&&val(item_data[id],3,0)==1&&val(item_data[id],field_id,0))return 1;}return 0;}
static void normal_action(int source,int target,int repeats){Unit*u=units+source;int hit,i,cost=0,side=target>=allies,charged=u->charged;if(u->aid)for(i=0;i<2;i++){int id=game.actors[u->aid].equipment[i];if(id&&val(item_data[id],3,0)==1)cost+=val(item_data[id],16,0);}u->mp=clamp(u->mp-cost,0,u->base[1]);if(weapon_flag(source,22))repeats*=2;
 for(hit=0;hit<repeats&&active(source);hit++){if(weapon_flag(source,23)){for(i=side?allies:0;i<(side?total:allies)&&active(source);i++)if(active(i)){u->charged=charged;normal_attack(source,i);}}else {if(!active(target))target=random_target(side);u->charged=charged;normal_attack(source,target);}}u->charged=0;}
static int skill_cost(int index,int id){Unit*u=&units[index];int cost=val(skill_data[id],11,0),i;if(u->aid)for(i=1;i<5;i++){int item=game.actors[u->aid].equipment[i];if(item&&val(item_data[item],27,0))return rm2k_skill_cost(cost,1);}return rm2k_skill_cost(cost,0);}
static int skill_usable(int index,int id){int sid,phy=val(skill_data[id],21,0),mag=val(skill_data[id],22,3);Unit*u=&units[index];if(u->mp<skill_cost(index,id))return 0;
    if(u->aid&&!val(skill_data[id],45,0)){LcfSpan set=field(skill_data[id],44);for(sid=1;sid<=(int)set.size&&sid<=MAX_ATTRIBUTE;sid++)if(set.data[sid-1]&&val(attributes[sid],2,0)==0){int j,found=0;for(j=0;j<2;j++){int item=game.actors[u->aid].equipment[j];LcfSpan attr=field(item_data[item],66);if(item&&val(item_data[item],3,0)==1&&sid<=(int)attr.size&&attr.data[sid-1])found=1;}if(!found)return 0;}}
    for(sid=1;sid<=MAX_STATE;sid++)if(u->states[sid]){if(val(states[sid],41,0)&&phy>=val(states[sid],42,0))return 0;if(val(states[sid],43,0)&&mag>=val(states[sid],44,0))return 0;}return 1;}
static int skill_power(int source,int target,int id,int vary){
 LcfSpan sk=skill_data[id];int positive=val(sk,12,0)>=2,effect=rm2k_skill_base(val(sk,24,0),val(sk,21,0),val(sk,22,3),bst(source,2),bst(source,4),bst(target,3),bst(target,4),!positive,val(sk,38,0));effect=attribute_effect(effect,target,field(sk,44),(LcfSpan){0,0});return vary?variance(effect,val(sk,23,4)):effect;
}
static void skill_effect(int source,int target,int id){
    Unit*s=&units[source],*t=&units[target];LcfSpan sk=skill_data[id],set=field(sk,42),attrs=field(sk,44);int positive=val(sk,12,0)>=2,hit=hit_chance(source,target,val(sk,25,100),!positive&&val(sk,7,0)==3),effect,delta,sid,i,success=0;
    if(!t->hp&&!(positive&&set.size&&set.data[0]))return;
    effect=clamp(skill_power(source,target,id,1),0,999);delta=positive?effect:-effect;
    if(val(sk,31,0)&&chance(hit)){
        int change=delta,old=t->hp;if(!positive&&t->defend)change/=t->aid&&val(actor_data[t->aid],24,0)?4:2;
        if(val(sk,37,0)&&!positive&&-change>t->hp)change=-t->hp;
        if(t->hp)hp_change(target,change,!positive);else if(positive)t->hp=clamp(change,0,t->base[0]);
        damage_message(target,t->hp-old);success=1;if(val(sk,37,0)&&!positive)hp_change(source,old-t->hp,0);
        if(t->hp>0&&!positive)physical_recovery(target,val(sk,21,0)*10);
    }
    if(t->hp==0&&!positive)return;
    if(val(sk,32,0)&&chance(hit)){int old=t->mp;t->mp=clamp(t->mp+delta,0,t->base[1]);if(val(sk,37,0)&&!positive)s->mp=clamp(s->mp+old-t->mp,0,s->base[1]);success|=old!=t->mp;}
    if(!positive&&!success&&(val(sk,31,0)||val(sk,32,0)))return;
    for(i=0;i<4;i++)if(val(sk,33+i,0)&&chance(hit)){int old=t->mod[i];t->mod[i]=clamp(old+delta,-t->base[i+2]/2,t->base[i+2]);success|=old!=t->mod[i];}
    for(sid=1;sid<=(int)set.size&&sid<=MAX_STATE;sid++)if(set.data[sid-1]){if(!positive&&t->states[sid])success=1;else if(chance(hit)){if(positive){if(t->states[sid]){inflict(target,sid,0);success=1;if(sid==1)t->hp=clamp(val(sk,31,0)?effect:t->base[0]*effect/100,1,t->base[0]);}}else if(chance(state_probability(target,sid))){inflict(target,sid,1);success=1;}}}
    if(val(sk,45,0))for(i=1;i<=(int)attrs.size&&i<=MAX_ATTRIBUTE;i++)if(attrs.data[i-1]&&chance(hit)){int old=t->shifts[i];t->shifts[i]=clamp(old+(positive?1:-1),-1,1);success|=old!=t->shifts[i];}
    if(!success){log_reset();term(24+clamp(val(sk,7,0),0,2));log_show();}
}
static void use_skill(int source,int id,int target,int from_item){
    Unit*u=&units[source];LcfSpan sk=skill_data[id];int scope=val(sk,12,0),i,enemy_side=u->aid?1:0;
    if(!from_item&&!skill_usable(source,id))return;if(!from_item)u->mp-=skill_cost(source,id);
    log_reset();log_text(u->name);log_span(field(sk,3));log_show();
    if(val(sk,8,0)==3){int swid=val(sk,13,1);if(swid>0&&swid<=MAX_SWITCH)game.switches[swid]=1;return;}
    if(val(sk,8,0)!=0){fault(9440);return;}
    animation_battle(val(sk,14,1));
    if(scope==0||scope==3)skill_effect(source,target,id);
    else if(scope==2)skill_effect(source,source,id);
    else if(scope==1||scope==4){int side=scope==1?enemy_side:!enemy_side;for(i=side?allies:0;i<(side?total:allies);i++)if(!units[i].hidden)skill_effect(source,i,id);}
    else fault(9441);
}
static u32 render_stamp(int include_focus){
    u32 h=2166136261U;int i,j,values[5]={allies,total,turn,include_focus?focus:0,battle_background_image()};
    for(i=0;i<5;i++)h=(h^(u32)values[i])*16777619U;
    for(i=0;i<total;i++){Unit*u=units+i;int fields[5]={u->aid,u->eid,u->hp,u->mp,u->hidden};
        for(j=0;j<5;j++)h=(h^(u32)fields[j])*16777619U;
        for(j=0;j<32&&u->name[j];j++)h=(h^(u8)u->name[j])*16777619U;
    }return h;
}
u32 battle_render_stamp(void){return render_stamp(1);}
u32 battle_background_stamp(void){return render_stamp(0);}
void draw_battle(void){int i,visible=0;clear(11);picture(battle_background_image(),0,0,0,0,240,96,0);for(i=allies;i<total;i++)if(active(i))visible++;
    {int at=0;for(i=allies;i<total;i++)if(active(i)){int img=enemy_image_ids[units[i].eid],x=(at+1)*240/(visible+1)-(img>=0?images[img].width/2:0);if(img<0)continue;picture(img,x,18,0,0,images[img].width,images[img].height,1);at++;}}
    box(0,0,240,15,11);draw_text(7,1,focus>=0?units[focus].name:"战斗",2,150);draw_text(164,1,"回合",6,30);draw_num(197,1,turn,1);
    box(0,97,240,63,11);for(i=0;i<allies;i++){int y=99+i*14;draw_text(5,y,units[i].name,units[i].hp?1:6,90);draw_text(94,y,"HP",6,16);draw_num(112,y,units[i].hp,1);draw_text(155,y,"MP",6,16);draw_num(175,y,units[i].mp,1);}
}
static int select_target(int side,int allow_dead){char text[512];debug_state[19]=side?3:4;int list[MAX_BATTLE_UNIT],n=0,i,pos=0;for(i=side?allies:0;i<(side?total:allies);i++)if(!units[i].hidden&&(units[i].hp||allow_dead)){int j;if(n)text[pos++]='/';list[n++]=i;for(j=0;units[i].name[j]&&pos<480;j++)text[pos++]=units[i].name[j];}text[pos]=0;if(!n)return -1;i=choices((LcfSpan){(u8*)text,pos},n+1);return i<n?list[i]:-1;}
static int battle_skill_id(const u32*mask,int position){
    unsigned word;for(word=0;word<(MAX_SKILL+31)/32;word++){unsigned bits=mask[word],count=__builtin_popcount(bits),bit=0;
        if((unsigned)position>=count){position-=count;continue;}while(position--)bits&=bits-1;
        while(!(bits&1)){bits>>=1;bit++;}return word*32+bit+1;
    }return 0;
}
static void battle_skill_row(const u32*list,int pos,int selected,int top,int actor){
    int id=battle_skill_id(list,pos),y=31+(pos-top)*17;char name[128];LcfSpan label=field(skill_data[id],1);int n=label.size<127?label.size:127;
    memcpy(name,label.data,n);name[n]=0;box(6,y-2,228,16,pos==selected?8:11);
    draw_text(10,y,name,skill_usable(actor,id)?1:6,185);draw_num(202,y,skill_cost(actor,id),6);
}
static int __attribute__((noinline)) select_skill(int index,int initial){
    u32 list[(MAX_SKILL+31)/32];int n=0,sel=0,top=0,id,i,dirty=1,first=1,previous=-1,previous_top=-1;u32 scene_stamp=0;
    memset(list,0,sizeof(list));for(id=1;id<=MAX_SKILL;id++)if(learned(units[index].aid,id)){int type=val(skill_data[id],8,0);
        if(type==0||(type==3&&val(skill_data[id],19,0))){list[(id-1)/32]|=1U<<((id-1)&31);if(id==initial)sel=n;n++;}}
    if(!n)return 0;debug_state[15]=6;debug_state[19]=5;
    for(;;){unsigned k;debug_state[15]=6;debug_state[19]=5;debug_state[14]=battle_skill_id(list,sel);debug_state[16]=sel;debug_state[17]=n;
        if(dirty){u32 stamp=balanced_scene_stamp();int full=first||stamp!=scene_stamp;
            if(sel<top)top=sel;if(sel>=top+6)top=sel-5;
            if(full){balanced_menu_background(3,24,234,134);box(3,24,234,134,11);rect(3,24,234,134,6);for(i=top;i<n&&i<top+6;i++)battle_skill_row(list,i,sel,top,index);draw_text(10,140,"A确定 B返回",2,216);}
            else if(top!=previous_top){box(6,29,228,102,11);for(i=top;i<n&&i<top+6;i++)battle_skill_row(list,i,sel,top,index);}
            else if(sel!=previous){battle_skill_row(list,previous,sel,top,index);battle_skill_row(list,sel,sel,top,index);}flip();
            dirty=first=0;previous=sel;previous_top=top;scene_stamp=balanced_scene_stamp();}
        k=wait_frame();if(k&KEY_B){debug_state[15]=0;return 0;}if(k&KEY_UP){sel=(sel+n-1)%n;dirty=1;}if(k&KEY_DOWN){sel=(sel+1)%n;dirty=1;}
        if((k&KEY_A)&&skill_usable(index,battle_skill_id(list,sel))){debug_state[15]=0;return battle_skill_id(list,sel);}
    }
}
/* RPG_RT-compatible automatic action ranking, adapted from EasyRPG's
 * GPL-3.0-or-later autobattle.cpp. Skills retain variance; normal attack ranking
 * deliberately retains the original no-variance and half-SP-cost quirks. */
static double skill_rank_target(int source,int target,int id){
 LcfSpan sk=skill_data[id],set=field(sk,42);int scope=val(sk,12,0),cost=val(sk,11,0),effect;double rank=0.0,sp=units[source].base[1];
 if(scope>=2){Unit*t=&units[target];if(t->hp>0){if(!val(sk,31,0))return 0.0;effect=skill_power(source,target,id,1);if(effect>t->base[0]-t->hp)effect=t->base[0]-t->hp;rank=(double)effect/t->base[0];if(sp>0){rank-=cost/sp/8.0;if(rank<0.0)rank=0.0;}return rank;}
  return set.size>1&&set.data[0]?(double)val(sk,24,0)/1000.0+1.0:0.0;
 }
 if(!val(sk,31,0)||!active(target))return 0.0;effect=skill_power(source,target,id,1);if(effect>units[target].hp)effect=units[target].hp;rank=(double)effect/units[target].hp;if(rank==1.0)rank=1.5;if(sp>0){rank-=cost/sp/4.0;if(rank<0.0)rank=0.0;}
 {int first;for(first=allies;first<total;first++)if(active(first)){if(first==target)rank=rank*1.5+0.5;break;}}return rank;
}
static double normal_rank_target(int source,int target){
 Unit*u=&units[source];LcfSpan a={0,0},b={0,0};int dmg,first;double rank;if(!active(target))return 0.0;
 if(u->aid){Actor*s=&game.actors[u->aid];if(val(item_data[s->equipment[0]],3,0)==1)a=field(item_data[s->equipment[0]],66);if(val(item_data[s->equipment[1]],3,0)==1)b=field(item_data[s->equipment[1]],66);}
 dmg=rm2k_normal_base(bst(source,2),bst(target,3));dmg=attribute_effect(dmg,target,a,b);if(dmg>units[target].hp)dmg=units[target].hp;rank=(double)dmg/units[target].hp;if(rank==1.0)rank=1.5;
 for(first=allies;first<total;first++)if(active(first)){if(first==target)rank=rank*1.5+0.5;break;}if(rank>0.0)rank=(double)random_n(100)/100.0+rank*1.5;return rank;
}
static void auto_plan(int index){
 Unit*u=&units[index];double best_skill=0.0,normal=0.0,best_target=0.0;int chosen=0,id,i,scope;
 for(id=1;id<=MAX_SKILL;id++)if(learned(u->aid,id)&&val(skill_data[id],8,0)==0&&skill_usable(index,id)){
  double rank=0.0;scope=val(skill_data[id],12,0);
  if(scope==2)rank=skill_rank_target(index,index,id);else for(i=scope<2?allies:0;i<(scope<2?total:allies);i++){double r=skill_rank_target(index,i,id);if(scope==1||scope==4)rank+=r;else if(r>rank)rank=r;}
  if(rank>0.0)rank+=(double)random_n(100)/100.0;if(rank>best_skill){best_skill=rank;chosen=id;}
 }
 for(i=allies;i<total;i++){double rank=normal_rank_target(index,i);if(rank>normal)normal=rank;}
 u->action=7;u->target=-1;
 if(chosen&&normal<best_skill){scope=val(skill_data[chosen],12,0);u->action=10;u->skill=chosen;if(scope==1||scope==4||scope==2){u->target=index;return;}
  for(i=scope==0?allies:0;i<(scope==0?total:allies);i++){double rank=skill_rank_target(index,i,chosen);if(rank>best_target){best_target=rank;u->target=i;}}if(u->target<0)u->action=7;return;
 }
 for(i=allies;i<total;i++){double rank=normal_rank_target(index,i);if(rank>best_target){best_target=rank;u->target=i;}}if(u->target>=0)u->action=0;
}
static int actor_plan(int index){
    Unit*u=&units[index];int n,target,id,scope,command=0,skill=0,item=0;static const char menu[]="攻击/技能/防御/物品";
    for(;;){focus=index;debug_state[13]=u->aid;debug_state[19]=2;n=choices_selected((LcfSpan){(const u8*)menu,sizeof(menu)-1},5,command);
        if(halt_code||n==4)return 0;command=n;
        if(n==0){target=weapon_flag(index,23)?random_target(1):select_target(1,0);if(target<0)continue;u->action=0;u->target=target;return 1;}
        if(n==1){for(;;){id=select_skill(index,skill);if(!id)break;skill=id;scope=val(skill_data[id],12,0);
            target=scope==0?select_target(1,0):scope==3?select_target(0,1):index;if(target<0)continue;
            u->action=10;u->skill=id;u->target=target;return 1;}continue;}
        if(n==2){u->action=2;u->defend=1;return 1;}
        for(;;){id=inventory_select_from(u->aid,item);if(!id)break;item=id;
            if(val(item_data[id],3,0)==9){skill=val(item_data[id],53,1);scope=val(skill_data[skill],12,0);target=scope==0?select_target(1,0):scope==3?select_target(0,1):index;}
            else target=val(item_data[id],31,0)||val(item_data[id],3,0)==10?index:select_target(0,1);
            if(target<0)continue;u->action=11;u->item=id;u->skill=skill;u->target=target;return 1;}
    }
}
static void use_battle_item(int source,int id,int target){
    int type=val(item_data[id],3,0),i,start=target,end=target+1;LcfSpan item=item_data[id];
    if(!game.items[id])return;audio_effect(11);consume_item(id);log_reset();log_span(field(item,1));term(28);log_show();
    if(type==9){use_skill(source,val(item,53,1),target,1);return;}
    if(type==10){int s=val(item,55,1);if(s>0&&s<=MAX_SWITCH)game.switches[s]=1;else fault(9460);return;}
    if(type!=6){fault(9461);return;}if(val(item,31,0)){start=0;end=allies;}
    for(i=start;i<end;i++){Unit*t=&units[i];LcfSpan set=field(item,62),cure=field(item,64);int sid,hp,mp,revived=0,old=t->hp;if(t->aid<=(int)set.size&&!set.data[t->aid-1])continue;if(t->hp>0&&val(item,38,0))continue;if(t->hp==0&&!(cure.size&&cure.data[0]))continue;
        for(sid=1;sid<=(int)cure.size&&sid<=MAX_STATE;sid++)if(cure.data[sid-1]&&t->states[sid]){if(sid==1)revived=1;inflict(i,sid,0);}
        hp=t->base[0]*val(item,32,0)/100+val(item,33,0);mp=t->base[1]*val(item,34,0)/100+val(item,35,0);if(t->hp>0)t->hp=clamp(t->hp+hp-revived,1,t->base[0]);t->mp=clamp(t->mp+mp,0,t->base[1]);if(t->hp!=old)damage_message(i,t->hp-old);
    }
}
static int average_level(void){int i,n=0;for(i=0;i<allies;i++)n+=game.actors[units[i].aid].level;return allies?n/allies:1;}
static int party_fatigue(void){int i,hp=0,mhp=0,mp=0,mmp=0;for(i=0;i<allies;i++){hp+=units[i].hp;mhp+=units[i].base[0];mp+=units[i].mp;mmp+=units[i].base[1];}return rm2k_fatigue(hp,mhp,mp,mmp);}
static int action_valid(int index,LcfSpan action){Unit*u=&units[index];int type=val(action,5,0),a=val(action,6,0),b=val(action,7,0),n=0,id=val(action,3,1);if(val(action,1,0)==1&&!skill_usable(index,id))return 0;
    switch(type){case 0:return 1;case 1:return sw(val(action,8,1));case 2:return rm2k_turn_matches(turn,b,a);case 3:n=alive_count(1);break;case 4:n=u->hp*100/u->base[0];break;case 5:n=u->base[1]?u->mp*100/u->base[1]:0;break;case 6:n=average_level();break;case 7:n=party_fatigue();break;default:fault(9444);return 0;}return n>=a&&n<=b;
}
static void enemy_plan(int index){
    Unit*u=&units[index];LcfSpan list=field(enemy_data[u->eid],42),actions[32];LcfReader r={list,0,0};ru32 count=0,key,i;int weights[32],max=0,sum=0,choice;
    u->action=7;u->target=random_target(0);if(u->charged){u->action=0;return;}if(!list.data)return;if(!lcf_number(&r,&count)||count>32){fault(9445);return;}
    for(i=0;i<count;i++){if(!lcf_next_entry(&r,&key,&actions[i])){fault(9446);return;}weights[i]=action_valid(index,actions[i])?val(actions[i],13,50):0;if(weights[i]>max)max=weights[i];}
    for(i=0;i<count;i++){weights[i]=weights[i]?clamp(weights[i]-max+10,0,100):0;sum+=weights[i];}if(!sum)return;choice=random_n(sum);
    for(i=0;i<count;i++){choice-=weights[i];if(choice<0){LcfSpan a=actions[i];int kind=val(a,1,0);u->action=kind==0?val(a,2,1):kind==1?10:12;u->skill=val(a,3,1);if(kind==2)u->skill=val(a,4,1);if(kind==1&&val(skill_data[u->skill],12,0)>=2)u->target=val(skill_data[u->skill],12,0)==3?random_target(1):index;if(val(a,9,0))game.switches[val(a,10,1)]=1;if(val(a,11,0))game.switches[val(a,12,1)]=0;break;}}
}
static void unit_turn(int index){Unit*u=&units[index];int sid;for(sid=1;sid<=MAX_STATE;sid++)if(u->states[sid]){LcfSpan s=states[sid];if(u->age[sid]>val(s,21,0)&&chance(val(s,22,0)))inflict(index,sid,0);else u->age[sid]++;}
    for(sid=1;sid<=MAX_STATE;sid++)if(u->states[sid]){LcfSpan s=states[sid];int hp=val(s,62,0)+u->base[0]*val(s,61,0)/100,mp=val(s,66,0)+u->base[1]*val(s,65,0)/100;hp_change(index,val(s,45,0)==0?-hp:val(s,45,0)==1?hp:0,0);u->mp=clamp(u->mp+(val(s,46,0)==0?-mp:val(s,46,0)==1?mp:0),0,u->base[1]);}
}
static void finish_units(void){int i,sid;for(i=0;i<allies;i++){Actor*a=&game.actors[units[i].aid];a->hp=units[i].hp;a->mp=units[i].mp;memset(a->states,0,sizeof(a->states));for(sid=1;sid<=MAX_STATE;sid++)if(units[i].states[sid]&&val(states[sid],2,0)==1&&val(states[sid],22,0)==0)a->states[sid/8]|=1<<(sid%8);}}
static void export_event_actors(void){int i,s;for(i=0;i<allies;i++){Actor*a=&game.actors[units[i].aid];a->hp=units[i].hp;a->mp=units[i].mp;memset(a->states,0,sizeof(a->states));for(s=1;s<=MAX_STATE;s++)if(units[i].states[s])a->states[s/8]|=1<<(s%8);}}
static void import_event_actors(void){int i,s;for(i=0;i<allies;i++){Unit*u=&units[i];Actor*a=&game.actors[u->aid];for(s=0;s<6;s++)u->base[s]=stat(u->aid,s);u->hp=clamp(a->hp,0,u->base[0]);u->mp=clamp(a->mp,0,u->base[1]);memcpy(u->name,a->name,sizeof(u->name));for(s=1;s<=MAX_STATE;s++)if(!!u->states[s]!=!!has_state(u->aid,s))inflict(i,s,has_state(u->aid,s)!=0);}}
int battle_actor_query(int a,int type,int*out){int i;if(!battle_active||type<2||type>9)return 0;for(i=0;i<allies;i++)if(units[i].aid==a){*out=type==2?units[i].hp:type==3?units[i].mp:bst(i,type-4);return 1;}return 0;}
int battle_event_stopped(void){return battle_active&&battle_aborted;}
int battle_enemy_query(int slot,int type){int index=allies+slot;if(!battle_active||slot<0||index>=total)return 0;if(type==0)return units[index].hp;if(type==1)return units[index].mp;if(type>=2&&type<=7)return bst(index,type-2);fault(9474);return 0;}
int battle_event_condition(const int*p){
    int i;if(!battle_active){fault(9470);return 0;}
    switch(p[0]){
    case 0:return sw(p[1])==(p[2]==0);
    case 1:return rm2k_compare(variable(p[1]),p[2]?variable(p[3]):p[3],p[4]);
    case 2:for(i=0;i<allies;i++)if(units[i].aid==p[1])return active(i)&&restriction(i)!=1;return 0;
    case 3:i=allies+p[1];return i>=allies&&i<total&&active(i)&&restriction(i)!=1;
    case 4:case 5:return 0; /* RPG2003-only conditions. */
    default:fault(9471);return 0;
    }
}
int battle_event_command(int code,const int*p,LcfSpan text){
    int index=allies+p[0],change;if(!battle_active){fault(9472);return 0;}
    battle_event_trace[3]++;battle_event_trace[4]=code;
    if(code==RM2K_TerminateBattle){battle_aborted=1;battle_event_trace[5]++;return 1;}
    if(code==RM2K_ChangeBattleBG){game.battle_backdrop=resource_image(4,text);return 1;}
    if(code==RM2K_ShowBattleAnimation_B){if(p[2])animation_battle(p[0]);else animation_start(p[0]);return 1;}
    /* Original enemy operands are zero-based party slots, not database IDs. */
    if(index<allies||index>=total)return 1;
    switch(code){
    case RM2K_ChangeMonsterHP:
        change=p[2]==0?p[3]:p[2]==1?variable(p[3]):p[3]*units[index].hp/100;
        battle_event_trace[8]=units[index].hp;hp_change(index,p[1]?-change:change,p[4]!=0);battle_event_trace[9]=units[index].hp;break;
    case RM2K_ChangeMonsterMP:change=p[2]?variable(p[3]):p[3];units[index].mp=clamp(units[index].mp+(p[1]?-change:change),0,units[index].base[1]);break;
    case RM2K_ChangeMonsterCondition:inflict(index,p[2],p[1]==0);break;
    case RM2K_ShowHiddenMonster:units[index].hidden=0;battle_event_trace[6]++;break;
    default:return 0;
    }return 1;
}
static int battle_page_matches(LcfSpan page){
    LcfSpan p=field(page,2);int enemy=allies+val(p,10,0),actor=val(p,13,1),i,ahp,amax;
    Rm2kBattleCondition c={val(p,1,0),sw(val(p,2,1)),sw(val(p,3,1)),variable(val(p,4,1)),val(p,5,0),val(p,6,0),val(p,7,0),val(p,11,0),val(p,12,100),val(p,14,0),val(p,15,100)};
    ahp=actor>0&&actor<=MAX_ACTOR?game.actors[actor].hp:-1;amax=actor>0&&actor<=MAX_ACTOR?stat(actor,0):0;
    for(i=0;i<allies;i++)if(units[i].aid==actor){ahp=units[i].hp;amax=units[i].base[0];}
    return rm2k_battle_page(&c,turn,enemy>=allies&&enemy<total?units[enemy].hp:-1,enemy>=allies&&enemy<total?units[enemy].base[0]:0,ahp,amax);
}
static void run_battle_pages(int troop){
    int page,base;
    while(!halt_code&&!battle_aborted&&alive_count(0)&&alive_count(1)){
        for(page=1;page<=MAX_BATTLE_PAGE;page++)if(battle_pages[page].data&&!battle_pages_executed[page]&&battle_page_matches(battle_pages[page]))break;
        if(page>MAX_BATTLE_PAGE)return;
        battle_pages_executed[page]=1;battle_event_trace[0]++;battle_event_trace[1]=page;battle_event_trace[2]=turn;
        {int background=vm_background;vm_background=0;export_event_actors();base=depth;push_battle_event(field(battle_pages[page],12),troop,page);run_events_until(base);import_event_actors();vm_background=background;}
    }
}
int battle(int troop,int escape_mode,int defeat_mode,int first_strike){
    LcfSpan members,pages;LcfReader r;ru32 count=0,i,key;int j,result=2,prev_scene=scene_image,previous_face=current_face;Music before_battle=game.music;
    if(troop<1||troop>MAX_TROOP){fault(9450);return 2;}if(!lcf_index(db[18],states,MAX_STATE+1)||!lcf_index(db[17],attributes,MAX_ATTRIBUTE+1)){fault(9451);return 2;}
    members=field(troop_data[troop],2);pages=field(troop_data[troop],11);r=(LcfReader){members,0,0};
    if(!lcf_index(pages,battle_pages,MAX_BATTLE_PAGE+1)){fault(9452);return 2;}
    memset(battle_pages_executed,0,sizeof(battle_pages_executed));memset((void*)battle_event_trace,0,sizeof(battle_event_trace));battle_aborted=0;
    memset(units,0,sizeof(units));allies=game.party_count;total=allies;turn=0;
    for(i=0;i<(unsigned)allies;i++){Unit*u=&units[i];Actor*a=&game.actors[game.party[i]];u->aid=game.party[i];memcpy(u->name,a->name,32);u->hp=a->hp;u->mp=a->mp;for(j=0;j<6;j++)u->base[j]=stat(u->aid,j);for(j=1;j<=MAX_STATE;j++)if(has_state(u->aid,j)){u->states[j]=1;u->age[j]=1;}}
    if(!lcf_number(&r,&count)||count>MAX_BATTLE_ENEMY){fault(9455);return 2;}
    for(i=0;i<count;i++){LcfSpan member,name;Unit*u=&units[total++];if(!lcf_next_entry(&r,&key,&member)){fault(9456);return 2;}u->eid=val(member,1,1);u->hidden=val(member,4,0);for(j=0;j<6;j++)u->base[j]=val(enemy_data[u->eid],4+j,10);u->hp=u->base[0];u->mp=u->base[1];name=field(enemy_data[u->eid],1);memcpy(u->name,name.data,name.size<31?name.size:31);}
    {int aa=0,ea=0,ec=0;for(j=0;j<allies;j++)aa+=bst(j,5);for(j=allies;j<total;j++)if(active(j)){ea+=bst(j,5);ec++;}aa=allies?aa/allies:1;ea=ec?ea/ec:1;escape_chance=clamp(150-(int)(100.0*ea/(aa?aa:1)+0.5),0,100);}
    audio_effect(4);audio_system(0);
    battle_active=1;current_face=-1;
    log_reset();for(j=allies;j<total;j++)if(active(j)){log_text(units[j].name);break;}term(1);log_show();
    while(!halt_code){int order[MAX_BATTLE_UNIT],n=0,option,auto_mode=0,escaped=0,cancelled=0;u32 planning_rng;
        static const char menu[]="战斗/自动/逃跑";run_battle_pages(troop);
        if(halt_code||battle_aborted)break;if(!alive_count(0)){result=2;break;}if(!alive_count(1)){result=0;break;}
        debug_state[23]=turn+1;
        focus=-1;debug_state[19]=1;option=choices((LcfSpan){(const u8*)menu,sizeof(menu)-1},0);if(option==1)auto_mode=1;if(option==2){if(!escape_mode){describe("不能逃跑。");continue;}if(first_strike||chance(escape_chance)){audio_effect(5);message(field(db[21],3));result=1;break;}message(field(db[21],4));escape_chance+=10;escaped=1;}
        planning_rng=game.rng;for(j=0;j<total;j++)units[j].defend=0;
        for(j=0;j<allies&&!escaped&&!halt_code;j++)if(active(j)){units[j].action=7;if(restriction(j)==1)continue;if((auto_mode||val(actor_data[units[j].aid],23,0))&&restriction(j)==0){auto_plan(j);}else if(restriction(j)>=2){units[j].action=0;units[j].target=random_target(restriction(j)==3?0:1);}else if(!actor_plan(j)){cancelled=1;break;}}
        if(cancelled){game.rng=planning_rng;for(j=0;j<allies;j++){units[j].action=7;units[j].defend=0;}continue;}
        turn++;memset(battle_pages_executed,0,sizeof(battle_pages_executed));
        if(!first_strike)for(j=allies;j<total&&!halt_code;j++)if(active(j)){if(restriction(j)==1)units[j].action=7;else if(restriction(j)>=2){units[j].action=0;units[j].target=random_target(restriction(j)==3?1:0);}else enemy_plan(j);units[j].defend=units[j].action==2;}
        for(j=0;j<total;j++)if(active(j)&&(!escaped||j>=allies)&&(!first_strike||j<allies)){units[j].order=bst(j,5)+random_n(bst(j,5)/4+4);if(units[j].aid&&units[j].action==0){int k;for(k=0;k<2;k++){int item=game.actors[units[j].aid].equipment[k];if(item&&val(item_data[item],3,0)==1&&val(item_data[item],21,0)){units[j].order+=9999;break;}}}order[n++]=j;}
        for(j=0;j<n;j++){int k;for(k=j+1;k<n;k++)if(units[order[k]].order>units[order[j]].order){int t=order[j];order[j]=order[k];order[k]=t;}}
        for(j=0;j<n&&!halt_code;j++){
            int index=order[j],target,retarget;Unit*u=&units[index];
            run_battle_pages(troop);if(halt_code||battle_aborted||!alive_count(0)||!alive_count(1))break;
            if(!active(index))continue;unit_turn(index);if(restriction(index)==1)continue;
            u->defend=u->action==2;target=u->target;
            retarget=u->action==0||u->action==1||(u->action==10&&val(skill_data[u->skill],12,0)<2)||(u->action==11&&val(item_data[u->item],3,0)==9&&val(skill_data[u->skill],12,0)<2);
            if(target>=0&&!active(target)&&retarget)target=random_target(target>=allies);
            switch(u->action){
            case 0:normal_action(index,target,1);break;
            case 1:normal_action(index,target,2);break;
            case 2:log_reset();log_text(u->name);term(14);log_show();break;
            case 3:case 7:break;
            case 4:u->charged=1;log_reset();log_text(u->name);term(16);log_show();break;
            case 5:{int k;log_reset();log_text(u->name);term(17);log_show();for(k=0;k<allies;k++)if(active(k)){int damage=bst(index,2)-bst(k,3)/2;if(damage<0)damage=0;damage=clamp(rm2k_defend(variance(damage,4),units[k].defend,val(actor_data[units[k].aid],24,0)),0,999);hp_change(k,-damage,1);damage_message(k,-damage);if(active(k))physical_recovery(k,100);}u->hidden=1;break;}
            case 6:u->hidden=1;log_reset();log_text(u->name);term(18);log_show();break;
            case 10:use_skill(index,u->skill,target,0);break;
            case 11:use_battle_item(index,u->item,target);break;
            case 12:{int k;if(u->skill<1||u->skill>MAX_ENEMY){fault(9473);break;}u->eid=u->skill;for(k=0;k<6;k++)u->base[k]=val(enemy_data[u->eid],4+k,10);{LcfSpan name=field(enemy_data[u->eid],1);memset(u->name,0,sizeof(u->name));memcpy(u->name,name.data,name.size<31?name.size:31);}break;}
            default:fault(9457);
            }
            if(!alive_count(0)||!alive_count(1))break;
        }
        run_battle_pages(troop);first_strike=0;if(battle_aborted)break;if(!alive_count(0)){result=2;break;}if(!alive_count(1)){result=0;break;}
    }
    if(battle_aborted)result=3;
    finish_units();
    if(!halt_code&&result==0){int xp=0,gold=0;for(j=allies;j<total;j++)if(units[j].hp==0&&!units[j].hidden){xp+=val(enemy_data[units[j].eid],11,0);gold+=val(enemy_data[units[j].eid],12,0);}
        audio_system(1);message(field(db[21],5));log_reset();log_num(xp);term(7);log_show();for(j=0;j<allies;j++)if(game.actors[units[j].aid].hp>0)actor_exp(units[j].aid,game.actors[units[j].aid].exp+xp);game.gold=clamp(game.gold+gold,0,999999);
        if(gold){log_reset();log_num(gold);log_text("Ｇ");term(9);log_show();}
        for(j=allies;j<total;j++)if(units[j].hp==0&&!units[j].hidden){int item=val(enemy_data[units[j].eid],13,0);if(item&&chance(val(enemy_data[units[j].eid],14,100))){game.items[item]=clamp(game.items[item]+1,0,99);log_reset();log_span(field(item_data[item],1));term(10);log_show();}}
    }
    if(!halt_code&&result==2){if(!defeat_mode)audio_system(6);message(field(db[21],6));if(!defeat_mode)fault(RM2K_GameOver);}
    if(!halt_code||halt_code==RM2K_GameOver){game.battles++;if(result==0)game.wins++;else if(result==1)game.escapes++;else if(result==2)game.defeats++;}
    audio_music(before_battle,0);battle_active=0;focus=-1;debug_state[19]=0;scene_image=prev_scene;current_face=previous_face;return result;
}
