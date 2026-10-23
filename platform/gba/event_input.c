#include "balanced.h"
/* GBA input adapter for original LCF input commands. Key numbers and priority
 * follow EasyRPG Player 0.8.1.1 game_interpreter.cpp, RM2000 >=1.50 format. */
#include "engine.h"
#include "assets.h"
extern volatile unsigned input_sampled,input_frame_keys;
extern volatile unsigned input_triggered;
static int key_number(unsigned keys,const int*p,unsigned count){
    int all_directions=count<6&&p[2];
    if(count>5&&p[5]&&(keys&KEY_SELECT))return 7;
    if(p[4]&&(keys&KEY_B))return 6;
    if(p[3]&&(keys&KEY_A))return 5;
    if((all_directions||(count>9&&p[9]))&&(keys&KEY_UP))return 4;
    if((all_directions||(count>8&&p[8]))&&(keys&KEY_RIGHT))return 3;
    if((all_directions||(count>7&&p[7]))&&(keys&KEY_LEFT))return 2;
    if((all_directions||(count>6&&p[6]))&&(keys&KEY_DOWN))return 1;
    return 0;
}
void event_key_input(const int*p,unsigned count){
    int key=0;if(p[0]<1||p[0]>MAX_VAR||count<5){fault(9200);return;}
    if(p[1]){debug_state[15]=13;do{key=key_number(wait_frame(),p,count);}while(!key);debug_state[15]=0;}
    else key=key_number(input_frame_keys,p,count);
    game.vars[p[0]]=key;
}
int event_input_ready(const int*p,unsigned count){int key;if(p[0]<1||p[0]>MAX_VAR||count<5){fault(9200);return 0;}key=key_number(p[1]?input_triggered:input_frame_keys,p,count);if(p[1]&&!key)return 0;game.vars[p[0]]=key;return 1;}
int event_number_input(int id,int digits){
    int maximum=1,value,position=0,i,dirty=1;
    if(id<1||id>MAX_VAR||digits<1||digits>6){fault(9201);return 0;}
    for(i=0;i<digits;i++)maximum*=10;maximum--;
    value=clamp(variable(id),0,maximum);debug_state[15]=16;engine_ui_depth++;
    for(;;){unsigned key;int place=1;for(i=0;i<digits-position-1;i++)place*=10;
        if(dirty){draw_scene();box(12,38,216,100,11);rect(12,38,216,100,6);draw_text(22,48,"输入数值",2,190);
            for(i=0;i<digits;i++){int factor=1,j;for(j=0;j<digits-i-1;j++)factor*=10;if(i==position)box(24+i*26,83,22,19,8);draw_num(30+i*26,86,value/factor%10,1);}flip();dirty=0;}
        key=wait_frame();if(key&KEY_LEFT){position=(position+digits-1)%digits;dirty=1;}if(key&KEY_RIGHT){position=(position+1)%digits;dirty=1;}
        if(key&KEY_UP){value+=((value/place%10)==9?-9:1)*place;dirty=1;}if(key&KEY_DOWN){value+=((value/place%10)==0?9:-1)*place;dirty=1;}
        if(key&KEY_A){game.vars[id]=value;debug_state[15]=0;engine_ui_depth--;return 1;}
    }
}

/* Small GBK name pools, separate from the full dialogue font. Keeping the
 * font does not require making every dialogue glyph a selectable name key. */
static const char name_surnames[]="王李张刘陈杨黄赵吴周徐孙马朱胡郭何林高罗郑梁谢宋唐许韩冯邓曹";
static const char name_given[]="明华宇浩子轩安宁晨阳思雨雪梅兰芳静敏诗涵梦瑶欣怡佳清远乐文然俊杰伟强磊勇军峰涛鹏飞龙松柏枫林山川海洋天星月云风霖露冰霜虹彩春夏秋冬晓夕辰瑞嘉泽睿博智志诚信仁礼义贤德康健平顺成承启凯胜超卓扬帆逸舒宏美慧";
static const char name_upper[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char name_lower[]="abcdefghijklmnopqrstuvwxyz";
/* Exclude the engine's escape, ExFont and choice separator characters. */
static const char name_symbols[]=".,!?:;-_+=*#@%&()[]{}<>~^|'\"·";
static const char name_digits[]="0123456789";
static const char*const name_pools[]={name_surnames,name_given,name_upper,name_lower,name_symbols,name_digits};
static const char*const name_tabs[]={"姓氏","名字","ABC","abc","符号","数字"};

static int name_count(const char*s){int n=0;while(*s){s+=(u8)*s<128?1:2;n++;}return n;}
static const char*name_character(const char*s,int index){while(index--)s+=(u8)*s<128?1:2;return s;}

volatile u32 balanced_name_metrics[4];/* scenes, grids, cells, name fields */
static void name_cell(const char*pool,int i,int selected){
    const char*p=name_character(pool,i);int cell=i%30,ascii=(u8)*p<128;
    char b[3]={p[0],ascii?0:p[1],0};
    box(11+cell%10*22,54+cell/10*20,18,18,i==selected?8:11);
    draw_text((ascii?17:14)+cell%10*22,57+cell/10*20,b,i==selected?2:1,12);balanced_name_metrics[2]++;
}
void event_name_input(int id){
    char name[32];int selected=0,page=0,i,first=1,grid_dirty=1,name_dirty=1,cursor_dirty=0,old_cursor=0,editing=0;Actor*a;u32 scene_stamp=0;
    if(id<1||id>MAX_ACTOR){fault(9205);return;}
    a=&game.actors[id];memcpy(name,a->name,sizeof(name));name[31]=0;engine_ui_depth++;
    debug_state[15]=3;debug_state[16]=id;
    for(;;){unsigned k;const char*pool=name_pools[page];
        int count=name_count(pool),n=0,old_page=page,old_selected=selected,top=selected/30*30;
        while(name[n])n++;
        debug_state[17]=page;debug_state[18]=selected;debug_state[19]=count;debug_state[20]=n;debug_state[23]=editing;
        if(first||grid_dirty||name_dirty||cursor_dirty){
            u32 stamp=balanced_scene_stamp();if(stamp!=scene_stamp)first=grid_dirty=name_dirty=1;
            if(first){draw_scene();balanced_name_metrics[0]++;box(2,3,236,155,11);rect(2,3,236,155,6);
                draw_text(9,9,"姓名：",6,48);draw_text(9,121,"方向选字/翻页 L/R分类",6,190);
                draw_text(9,142,"A选 B删 START完成 SELECT原名",2,222);}
            if(name_dirty){box(58,9,170,12,11);draw_text(58,9,name,1,144);draw_num(209,9,name_count(name),6);draw_text(216,9,"/6",6,12);balanced_name_metrics[3]++;}
            if(grid_dirty){box(8,29,222,20,11);
                for(i=0;i<6;i++){int w=i==2||i==3?18:24;box(8+i*37,29,35,20,i==page?8:11);draw_text(8+i*37+(35-w)/2,33,name_tabs[i],i==page?2:6,30);}
                box(8,51,222,62,11);for(i=top;i<count&&i<top+30;i++)name_cell(pool,i,selected);
                box(201,119,29,15,11);draw_num(203,121,selected/30+1,6);draw_text(211,121,"/",6,6);draw_num(220,121,(count+29)/30,6);balanced_name_metrics[1]++;
            }else if(cursor_dirty){name_cell(pool,old_cursor,selected);name_cell(pool,selected,selected);}
            flip();first=grid_dirty=name_dirty=cursor_dirty=0;scene_stamp=balanced_scene_stamp();
        }
        k=wait_frame();
        if(k&KEY_UP)selected=(selected+count-10)%count;
        if(k&KEY_DOWN)selected=(selected+10)%count;
        if(k&KEY_LEFT)selected=(selected+count-1)%count;
        if(k&KEY_RIGHT)selected=(selected+1)%count;
        if(k&(KEY_L|KEY_R)){page=(page+((k&KEY_R)?1:5))%6;selected=0;}
        if(k&KEY_SELECT){memcpy(name,a->name,sizeof(name));name[31]=0;editing=0;name_dirty=1;}
        if(k&KEY_B){int j=0,last=0;while(name[j]){last=j;j+=((u8)name[j]<128?1:2);}if(j)name[last]=0;editing=1;name_dirty=1;}
        if(k&KEY_A){
            if(!editing){memset(name,0,sizeof(name));editing=1;}
            n=0;while(name[n])n++;pool=name_character(name_pools[page],selected);
            if(name_count(name)<6){name[n++]=*pool++;if((u8)name[n-1]>=128)name[n++]=*pool;name[n]=0;}
            if(!page){page=1;selected=0;}name_dirty=1;
        }
        if(page!=old_page||selected/30!=old_selected/30)grid_dirty=1;
        else if(selected!=old_selected){old_cursor=old_selected;cursor_dirty=1;}
        if(k&KEY_START){if(name[0])memcpy(a->name,name,sizeof(name));debug_state[15]=0;engine_ui_depth--;return;}
    }
}
