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
static const char name_surnames[]="王李张刘陈杨黄赵吴周徐孙马朱胡郭何林高罗";
static const char name_given[]="明华宇浩子轩安宁晨阳思雨雪梅兰芳静敏诗涵梦瑶欣怡佳清远乐文然";

volatile u32 balanced_name_metrics[4];/* scenes, grids, cells, name fields */
static void name_cell(const char*pool,int i,int selected){
    char b[3]={pool[i*2],pool[i*2+1],0};
    box(11+i%10*22,54+i/10*20,18,18,i==selected?8:11);
    draw_text(14+i%10*22,57+i/10*20,b,i==selected?2:1,12);balanced_name_metrics[2]++;
}
void event_name_input(int id){
    char name[32];int selected=0,page=0,i,first=1,grid_dirty=1,name_dirty=1,cursor_dirty=0,old_cursor=0,editing=0;Actor*a;u32 scene_stamp=0;
    if(id<1||id>MAX_ACTOR){fault(9205);return;}
    a=&game.actors[id];memcpy(name,a->name,sizeof(name));name[31]=0;engine_ui_depth++;
    debug_state[15]=3;debug_state[16]=id;
    for(;;){unsigned k;const char*pool=page?name_given:name_surnames;
        int count=(page?sizeof(name_given):sizeof(name_surnames))/2,n=0,old_page=page,old_selected=selected;
        while(name[n])n++;
        debug_state[17]=page;debug_state[18]=selected;debug_state[19]=count;debug_state[20]=n;debug_state[23]=editing;
        if(first||grid_dirty||name_dirty||cursor_dirty){
            u32 stamp=balanced_scene_stamp();if(stamp!=scene_stamp)first=grid_dirty=name_dirty=1;
            if(first){draw_scene();balanced_name_metrics[0]++;box(2,3,236,155,11);rect(2,3,236,155,6);
                draw_text(9,9,"姓名：",6,48);draw_text(9,121,"A选字  B删除  START完成",2,222);
                draw_text(9,142,"首次选字替换原名",6,144);draw_text(166,142,"SELECT原名",6,66);}
            if(name_dirty){box(58,9,166,12,11);draw_text(58,9,name,1,166);balanced_name_metrics[3]++;}
            if(grid_dirty){box(8,29,222,20,11);box(page?126:8,29,104,20,8);
                draw_text(18,33,"L 常见姓氏",page?6:2,100);draw_text(136,33,"R 名字用字",page?2:6,100);
                box(8,51,222,62,11);for(i=0;i<count;i++)name_cell(pool,i,selected);balanced_name_metrics[1]++;
            }else if(cursor_dirty){name_cell(pool,old_cursor,selected);name_cell(pool,selected,selected);}
            flip();first=grid_dirty=name_dirty=cursor_dirty=0;scene_stamp=balanced_scene_stamp();
        }
        k=wait_frame();
        if(k&KEY_UP)selected=(selected+count-10)%count;
        if(k&KEY_DOWN)selected=(selected+10)%count;
        if(k&KEY_LEFT)selected=(selected+count-1)%count;
        if(k&KEY_RIGHT)selected=(selected+1)%count;
        if(k&(KEY_L|KEY_R)){page=(k&KEY_R)?1:0;selected=0;}
        if(k&KEY_SELECT){memcpy(name,a->name,sizeof(name));name[31]=0;editing=0;name_dirty=1;}
        if(k&KEY_B){int j=0,last=0;while(name[j]){last=j;j+=((u8)name[j]<128?1:2);}if(j)name[last]=0;editing=1;name_dirty=1;}
        if(k&KEY_A){
            if(!editing){memset(name,0,sizeof(name));editing=1;}
            n=0;while(name[n])n++;pool=page?name_given:name_surnames;
            if(n<=10){name[n++]=pool[selected*2];name[n++]=pool[selected*2+1];name[n]=0;}
            if(!page){page=1;selected=0;}name_dirty=1;
        }
        if(page!=old_page)grid_dirty=1;
        else if(selected!=old_selected){old_cursor=old_selected;cursor_dirty=1;}
        if(k&KEY_START){if(name[0])memcpy(a->name,name,sizeof(name));debug_state[15]=0;engine_ui_depth--;return;}
    }
}
