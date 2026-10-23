#include "engine.h"
#include "balanced.h"
#include "item_mask.h"
int party_select(void){char text[256];int i,j,pos=0,n;for(i=0;i<game.party_count;i++){if(i)text[pos++]='/';for(j=0;game.actors[game.party[i]].name[j]&&pos<250;j++)text[pos++]=game.actors[game.party[i]].name[j];}text[pos]=0;if(game.party_count==1)return game.party[0];n=choices((LcfSpan){(u8*)text,pos},game.party_count+1);return n<game.party_count?game.party[n]:0;}
static int usable_actor(int id,int actor){LcfSpan set=field(item_data[id],62);return actor>0&&actor<=MAX_ACTOR&&(actor>(int)set.size||set.data[actor-1]);}
void consume_item(int id){int uses=val(item_data[id],6,1),type=val(item_data[id],3,0);if(id<1||id>MAX_ITEM||!game.items[id]||type<6||uses==0)return;if(++game.item_usage[id]>=uses){game.items[id]--;game.item_usage[id]=0;}}
static void inventory_full(const u32*ids,int count,int sel,int top,int battle_mode){int i;balanced_menu_background(3,19,234,139);box(3,19,234,139,11);rect(3,19,234,139,6);draw_text(10,23,battle_mode?"战斗物品":"随身物品",2,215);
        for(i=top;i<count&&i<top+5;i++){char name[96];LcfSpan s=field(item_data[item_mask_id(ids,i)],1);int size=s.size<95?s.size:95;memcpy(name,s.data,size);name[size]=0;if(i==sel)box(7,41+(i-top)*18,226,16,8);draw_text(12,43+(i-top)*18,name,i==sel?2:1,185);draw_num(207,43+(i-top)*18,game.items[item_mask_id(ids,i)],6);}
        draw_text(10,142,"A选择 L说明 B返回",6,220);flip();}
static void inventory_row(const u32*ids,int index,int selected,int top){
 int id=item_mask_id(ids,index),y=43+(index-top)*18;char name[96];LcfSpan text=field(item_data[id],1);int n=text.size<95?text.size:95;
 memcpy(name,text.data,n);name[n]=0;box(7,y-2,226,16,index==selected?8:11);draw_text(12,y,name,index==selected?2:1,185);draw_num(207,y,game.items[id],6);
}
int inventory_select_from(int battle_mode,int initial_item){
    u32 ids[ITEM_MASK_WORDS];int count=0,sel=0,top=0,i,dirty=1,first=1,previous=-1,previous_top=-1;unsigned scene_stamp=0,last_quantities=0;memset(ids,0,sizeof(ids));for(i=1;i<=MAX_ITEM;i++)if(game.items[i]){int t=val(item_data[i],3,0);if(!battle_mode||(t==6&&!val(item_data[i],37,0))||(t==10&&val(item_data[i],58,0))||(t==9&&usable_actor(i,battle_mode))){item_mask_add(ids,i);if(i==initial_item)sel=count;count++;}}
    if(!count){describe(battle_mode?"没有可在战斗中使用的物品。":"没有物品。");return 0;}debug_state[15]=7;
    for(;;){unsigned k;debug_state[15]=7;debug_state[16]=sel;debug_state[17]=count;debug_state[18]=item_mask_id(ids,sel);if(dirty){u32 stamp=balanced_scene_stamp(),quantities=2166136261U;int full=first||stamp!=scene_stamp,complex=0;
        if(sel<top)top=sel;if(sel>=top+5)top=sel-4;
        for(i=top;i<count&&i<top+5;i++){int id=item_mask_id(ids,i);LcfSpan text=field(item_data[id],1);unsigned j;quantities=(quantities^(unsigned)id)*16777619U;quantities=(quantities^game.items[id])*16777619U;for(j=0;j<text.size;j++)if(text.data[j]=='\n')complex=1;}
        if(full||complex)inventory_full(ids,count,sel,top,battle_mode);
        else{if(top!=previous_top||quantities!=last_quantities){box(7,41,226,90,11);for(i=top;i<count&&i<top+5;i++)inventory_row(ids,i,sel,top);}
            else if(sel!=previous){inventory_row(ids,previous,sel,top);inventory_row(ids,sel,sel,top);}flip();}
        dirty=first=0;previous=sel;previous_top=top;last_quantities=quantities;scene_stamp=balanced_scene_stamp();}
        k=wait_frame();if(k&KEY_B){debug_state[15]=0;return 0;}if(k&KEY_UP){sel=(sel+count-1)%count;dirty=1;}if(k&KEY_DOWN){sel=(sel+1)%count;dirty=1;}if(k&KEY_L){message(field(item_data[item_mask_id(ids,sel)],2));debug_state[15]=7;dirty=first=1;}if(k&KEY_A){debug_state[15]=0;return item_mask_id(ids,sel);}
    }
}
int inventory_select(int battle_mode){return inventory_select_from(battle_mode,0);}
int use_map_item(int id,int aid){
    LcfSpan item=item_data[id];int type=val(item,3,0),i,success=0;
    if(!game.items[id])return 0;
    if(type==10){int swid=val(item,55,1);if(!val(item,57,1))return 0;if(swid<1||swid>MAX_SWITCH){fault(9500);return 0;}game.switches[swid]=1;consume_item(id);return 1;}
    if(type==9){int skill=val(item,53,1),caster=0,scope=val(skill_data[skill],12,0);for(i=0;i<game.party_count;i++){int a=game.party[i];if(usable_actor(id,a)&&(!caster||game.actors[a].level>game.actors[caster].level))caster=a;}if(scope==2)caster=aid;if(!caster||!usable_actor(id,caster))return 0;if(use_map_skill(caster,skill,aid,1)){consume_item(id);return 1;}return 0;}
    if(type!=6&&type!=7&&type!=8)return 0;
    for(i=0;i<game.party_count;i++){
        int a=game.party[i],changed=0,sid;Actor*s=&game.actors[a];LcfSpan cure=field(item,64);
        if((aid&&a!=aid)||!usable_actor(id,a))continue;
        if(type==6){
            int revived=0,hp=stat(a,0)*val(item,32,0)/100+val(item,33,0),mp=stat(a,1)*val(item,34,0)/100+val(item,35,0);
            if((has_state(a,1)&&!(cure.size&&cure.data[0]))||(!has_state(a,1)&&val(item,38,0)))continue;
            for(sid=1;sid<=(int)cure.size;sid++)if(cure.data[sid-1]&&has_state(a,sid)){if(sid==1)revived=1;set_state(a,sid,0);changed=1;}
            if(hp>0&&s->hp<stat(a,0)){s->hp=clamp(s->hp+hp-revived,1,stat(a,0));changed=1;}
            if(mp>0&&s->mp<stat(a,1)){s->mp=clamp(s->mp+mp,0,stat(a,1));changed=1;}
        }else if(s->hp>0){
            if(type==7){int skill=val(item,53,1);if(!learned(a,skill)){set_learned(a,skill,1);changed=1;}}
            else {for(sid=0;sid<6;sid++)s->bonus[sid]+=val(item,41+sid,0);changed=1;}
        }
        success|=changed;
    }
    if(success)consume_item(id);return success;
}
