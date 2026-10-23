#include "engine.h"
static int equippable(int actor,int item,int slot){
    LcfSpan set=field(item_data[item],62);int type=val(item_data[item],3,0),dual=val(actor_data[actor],21,0);
    if(actor<=(int)set.size&&!set.data[actor-1])return 0;
    if(dual&&type==2)return 0;return type==(dual&&slot==1?1:slot+1);
}
static void unequip(int actor,int slot){int item=game.actors[actor].equipment[slot];if(item)game.items[item]=clamp(game.items[item]+1,0,99);game.actors[actor].equipment[slot]=0;}
void equipment_menu(void){
    int actor=party_select(),slot;u16 ids[MAX_ITEM+1];int count=1,i,selected=0,top=0,dirty=1;
    static const char slots[]="武器/盾牌或副手/身体防具/头部防具/装饰品";
    if(!actor)return;if(val(actor_data[actor],22,0)){describe("这个角色的装备不能变更。");return;}
    slot=choices((LcfSpan){(const u8*)slots,sizeof(slots)-1},6);if(slot>=5)return;ids[0]=0;
    for(i=1;i<=MAX_ITEM;i++)if(game.items[i]&&equippable(actor,i,slot))ids[count++]=i;
    for(;;){unsigned k;debug_state[15]=10;debug_state[16]=selected;debug_state[17]=count;debug_state[18]=ids[selected];if(dirty){draw_scene();box(3,18,234,140,11);rect(3,18,234,140,6);draw_text(10,23,game.actors[actor].name,2,210);if(selected<top)top=selected;if(selected>=top+5)top=selected-4;
        for(i=top;i<count&&i<top+5;i++){char name[96];int item=ids[i];if(item){LcfSpan text=field(item_data[item],1);int n=text.size<95?text.size:95;memcpy(name,text.data,n);name[n]=0;}else {const char *label="卸下";int j=0;while(label[j]){name[j]=label[j];j++;}name[j]=0;}if(i==selected)box(7,42+(i-top)*18,226,16,8);draw_text(12,44+(i-top)*18,name,i==selected?2:1,212);}
        draw_text(10,142,"A装备 L说明 B返回",6,218);flip();dirty=0;}k=wait_frame();
        if(k&KEY_B){debug_state[15]=0;return;}if(k&KEY_UP){selected=(selected+count-1)%count;dirty=1;}if(k&KEY_DOWN){selected=(selected+1)%count;dirty=1;}
        if((k&KEY_L)&&ids[selected]){message(field(item_data[ids[selected]],2));dirty=1;}
        if(k&KEY_A){int item=ids[selected],other=slot==0?1:0;Actor*a=&game.actors[actor];
            if(item==a->equipment[slot]){debug_state[15]=0;return;}
            if(slot<2&&item&&(val(item_data[item],15,0)||(a->equipment[other]&&val(item_data[a->equipment[other]],15,0))))unequip(actor,other);
            unequip(actor,slot);if(item){game.items[item]--;a->equipment[slot]=item;}
            /* Let the original Ruina event enforce its additional equipment rules. */
            debug_state[15]=0;push_common(100);return;
        }
    }
}
