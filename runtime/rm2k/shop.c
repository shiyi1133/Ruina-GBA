#include "engine.h"
#include "balanced.h"
#include "item_mask.h"
static void quantity_full(const char*label,int selling,int price,int count){draw_scene();box(3,27,234,131,11);rect(3,27,234,131,6);draw_text(10,34,label,2,217);draw_text(10,55,selling?"卖出单价":"购买单价",6,100);draw_num(137,55,price,1);draw_text(10,75,"数量",6,80);draw_num(137,75,count,2);draw_text(10,95,"合计",6,80);draw_num(137,95,price*count,1);draw_text(10,115,"现有金钱",6,100);draw_num(137,115,game.gold,1);draw_text(10,141,"左右±1 L/R±10 A确定 B返回",6,220);flip();}
static int quantity(int item,int selling){
    int price=val(item_data[item],5,0)/(selling?2:1),limit=selling?game.items[item]:99-game.items[item],count=1,dirty=1,first=1,previous=-1,previous_gold=-1,complex=0;unsigned scene_stamp=0;
    LcfSpan name=field(item_data[item],1);char label[128];int n=name.size<127?name.size:127;memcpy(label,name.data,n);label[n]=0;{int c;for(c=0;c<n;c++)if(label[c]=='\n')complex=1;}
    if(selling&&price==0)return 0;if(!selling&&price>0&&limit>game.gold/price)limit=game.gold/price;if(limit<=0)return 0;
    for(;;){unsigned k;debug_state[15]=9;debug_state[16]=count;debug_state[18]=item;if(dirty){u32 stamp=balanced_scene_stamp();int full=first||complex||stamp!=scene_stamp;
        if(full)quantity_full(label,selling,price,count);
        else{if(previous!=count){box(137,75,90,12,11);box(137,95,90,12,11);draw_num(137,75,count,2);draw_num(137,95,price*count,1);}
            if(previous_gold!=game.gold){box(137,115,90,12,11);draw_num(137,115,game.gold,1);}flip();}
        dirty=first=0;previous=count;previous_gold=game.gold;scene_stamp=balanced_scene_stamp();}k=wait_frame();if(k&KEY_B){debug_state[15]=0;return 0;}if(k&(KEY_LEFT|KEY_DOWN)){count=clamp(count-1,1,limit);dirty=1;}if(k&(KEY_RIGHT|KEY_UP)){count=clamp(count+1,1,limit);dirty=1;}if(k&KEY_L){count=clamp(count-10,1,limit);dirty=1;}if(k&KEY_R){count=clamp(count+10,1,limit);dirty=1;}
        if(k&KEY_A){if(!game.items[item])game.item_usage[item]=0;game.items[item]+=selling?-count:count;game.gold=clamp(game.gold+(selling?1:-1)*count*price,0,999999);if(!game.items[item])game.item_usage[item]=0;debug_state[15]=0;return 1;}
    }
}
static int goods_id(const void*goods,int pos,int selling){return selling?item_mask_id((const u32*)goods,pos):((const int*)goods)[pos];}
static void goods_row(const void*goods,int index,int selected,int top,int selling){
    int item=goods_id(goods,index,selling),price=val(item_data[item],5,0)/(selling?2:1);LcfSpan text=field(item_data[item],1);char name[128];int n=text.size<127?text.size:127;
    memcpy(name,text.data,n);name[n]=0;box(7,42+(index-top)*18,226,16,index==selected?8:11);draw_text(12,44+(index-top)*18,name,1,166);draw_num(184,44+(index-top)*18,price,6);
}
static void goods_full(const void*goods,int count,int selling,int pos,int top){int i;draw_scene();box(3,19,234,139,11);rect(3,19,234,139,6);draw_text(10,23,selling?"出售":"购买",2,72);draw_text(135,23,"持金",6,40);draw_num(169,23,game.gold,1);
        for(i=top;i<count&&i<top+5;i++){int item=goods_id(goods,i,selling),price=val(item_data[item],5,0)/(selling?2:1);LcfSpan text=field(item_data[item],1);char name[128];int n=text.size<127?text.size:127;memcpy(name,text.data,n);name[n]=0;if(i==pos)box(7,42+(i-top)*18,226,16,8);draw_text(12,44+(i-top)*18,name,1,166);draw_num(184,44+(i-top)*18,price,6);}
        draw_text(10,142,"A选择 L说明 B返回",6,220);flip();}
static int goods_menu(const void*goods,int count,int selling){
    int pos=0,top=0,dirty=1,changed=0,i,first=1,previous=-1,previous_top=-1,previous_gold=-1;unsigned scene_stamp=0;if(!count){describe("没有可交易的物品。");return 0;}
    for(;;){unsigned k;debug_state[15]=8;debug_state[16]=pos;debug_state[17]=count;debug_state[18]=goods_id(goods,pos,selling);if(dirty){u32 stamp=balanced_scene_stamp();int full=first||stamp!=scene_stamp,complex=0;
        if(pos<top)top=pos;if(pos>=top+5)top=pos-4;
        for(i=top;i<count&&i<top+5;i++){LcfSpan text=field(item_data[goods_id(goods,i,selling)],1);unsigned j;for(j=0;j<text.size;j++)if(text.data[j]=='\n')complex=1;}
        if(full||complex)goods_full(goods,count,selling,pos,top);
        else{if(previous_gold!=game.gold){box(169,23,61,12,11);draw_num(169,23,game.gold,1);}
            if(top!=previous_top){box(7,42,226,90,11);for(i=top;i<count&&i<top+5;i++)goods_row(goods,i,pos,top,selling);}
            else if(pos!=previous){goods_row(goods,previous,pos,top,selling);goods_row(goods,pos,pos,top,selling);}flip();}
        dirty=first=0;previous=pos;previous_top=top;previous_gold=game.gold;scene_stamp=balanced_scene_stamp();}k=wait_frame();if(k&KEY_B){debug_state[15]=0;return changed;}if(k&KEY_UP){pos=(pos+count-1)%count;dirty=1;}if(k&KEY_DOWN){pos=(pos+1)%count;dirty=1;}if(k&KEY_L){message(field(item_data[goods_id(goods,pos,selling)],2));dirty=first=1;}if(k&KEY_A){changed|=quantity(goods_id(goods,pos,selling),selling);dirty=first=1;}
    }
}
int open_shop(int mode,const int*goods,int count){
    static const char both[]="购买/出售/离开",buy[]="购买/离开",sell[]="出售/离开";int changed=0;
    for(;;){const char*menu=mode==0?both:mode==1?buy:sell;int len=0,n;while(menu[len])len++;n=choices((LcfSpan){(const u8*)menu,len},mode==0?3:2);if(n==(mode==0?2:1))return changed;
        if((mode==0&&n==1)||mode==2){u32 list[ITEM_MASK_WORDS];int i,total=0;memset(list,0,sizeof(list));for(i=1;i<=MAX_ITEM;i++)if(game.items[i]&&val(item_data[i],5,0)>0){item_mask_add(list,i);total++;}changed|=goods_menu(list,total,1);}
        else changed|=goods_menu(goods,count,0);
    }
}
