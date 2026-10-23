#include "game.h"
#include "assets.h"
static int len(const char*s){int n=0;while(s[n])n++;return n;}
void map_screen(void){acceptance_boost_prepare();world_screen();}
static void status(void){int i,from=0,dirty=1;for(;;){unsigned k;int next=from;if(dirty){clear(11);draw_text(8,5,"队伍状态 · 验收版",2,224);
    for(i=from;i<game.party_count&&i<from+2;i++){int y=26+(i-from)*52,a=game.party[i];Actor*s=&game.actors[a];draw_text(8,y,s->name,1,112);draw_text(143,y,"LV",6,20);draw_num(161,y,s->level,1);draw_text(8,y+14,"HP",6,18);draw_num(27,y+14,s->hp,1);draw_text(49,y+14,"/",6,6);draw_num(57,y+14,stat(a,0),6);draw_text(94,y+14,"MP",6,18);draw_num(112,y+14,s->mp,1);draw_text(135,y+14,"/",6,6);draw_num(143,y+14,stat(a,1),6);draw_text(8,y+28,s->title,2,220);}
    if(game.party_count>2){draw_num(194,143,from+1,6);draw_text(205,143,"/",6,6);draw_num(214,143,game.party_count,6);}flip();dirty=0;}k=wait_frame();if(k&KEY_B)return;if(k&KEY_DOWN)next=clamp(from+1,0,game.party_count-1);if(k&KEY_UP)next=clamp(from-1,0,game.party_count-1);if(next!=from){from=next;dirty=1;}}}
static void inventory(void){int id=inventory_select(0),option,aid=0;if(!id)return;{static const char menu[]="使用/查看说明/返回";option=choices((LcfSpan){(const u8*)menu,len(menu)},3);}if(option==1){message(field(item_data[id],2));return;}if(option!=0)return;
    if(val(item_data[id],3,0)<6){describe("这件物品不能直接使用，可查看说明或通过装备菜单操作。");return;}
    if(val(item_data[id],3,0)!=10&&!val(item_data[id],31,0)){aid=party_select();if(!aid)return;}
    if(!use_map_item(id,aid)&&!halt_code)describe("没有产生效果。");
}
/* Help is an overlay on the paused field, never an original game event. */
static void controls_help(void){
    static const char*const headings[]={"移动与调查","地图视野与标记","菜单与战斗","输入名字","音乐与存档"};
    static const char*const lines[][7]={
        {"方向键：移动当前位置。","A：调查脚下或面前的地点。","短按 L/R：选择远处调查点。","选点后 A：沿通路前往并调查。","手动移动会取消远处目标。","L+R：只前往选点，不自动调查。","B 或 START：打开系统菜单。"},
        {"按住 R+方向键：浏览地图。","浏览视野不会移动角色。","黄色标记：可以调查的地点。","灰色标记：当前暂时无法到达。","蓝色标记：当前位置。","边缘亮三角：视野还能滚动。","灰三角表示视野边界，不是路障。"},
        {"上下：选择；A：确定。","B：返回上一层或取消当前选择。","战斗中选目标时 B：回到列表。","技能或物品列表 B：回到指令。","物品、特技列表按 L 查看说明。","对话按 A 继续，长对话按 A 翻页。","原作制作等列表：L/R 快速翻页。"},
        {"L/R：切换姓、名、字母等分类。","方向键选字，跨过本页自动翻页。","名字用字共四页，可混合输入。","A：添加；第一次选字替换原名。","B：删除最后一个完整字符。","START：完成；空名字保留原名。","SELECT：还原；最多输入六个字。"},
        {"保存：B 菜单内选择保存游戏。","只有原事件允许时才能保存。","继续游戏读取普通 SAV 存档。","标题菜单可进入音乐欣赏。","上下选曲；A 播放或暂停。","左右或 L/R 换曲；B 返回。","START 切换两种简化音色。"}
    };
    int page=0,dirty=1,i;engine_ui_depth++;
    for(;;){unsigned k;debug_state[15]=19;debug_state[16]=page;debug_state[17]=5;
        if(dirty){draw_scene();box(2,3,236,155,11);rect(2,3,236,155,6);
            draw_text(10,9,"操作说明",2,96);draw_num(199,9,page+1,6);draw_text(208,9,"/5",6,18);
            draw_text(10,27,headings[page],2,216);
            for(i=0;i<7;i++)draw_text(10,44+i*12,lines[page][i],1,222);
            draw_text(10,142,"左右/LR翻页  B返回菜单",6,222);flip();dirty=0;}
        k=wait_frame();if(k&KEY_B)break;
        if(k&(KEY_LEFT|KEY_L)){page=(page+4)%5;dirty=1;}
        if(k&(KEY_RIGHT|KEY_R)){page=(page+1)%5;dirty=1;}
    }
    debug_state[15]=0;engine_ui_depth--;
}
static void animation_settings(void){static const char menu[]="原速播放（推荐）/完整播放/返回";int n;
    describe("原速播放保持出招节奏，繁重的过渡画面可能略过。完整播放保留全部画面，复杂技能会放慢。本次运行内有效。");
    n=choices_selected((LcfSpan){(const u8*)menu,len(menu)},3,animation_playback_full());if(n<2)animation_playback_mode(n);
}
void system_menu(void){static const char menu[]="队伍状态/随身物品/保存游戏/装备/特技/操作说明/动画播放/返回地图";int old_pause=engine_clock_paused,n,initial=0;engine_clock_paused=1;
    for(;;){n=choices_selected((LcfSpan){(const u8*)menu,len(menu)},8,initial);if(n==5){controls_help();initial=5;}else if(n==6){animation_settings();initial=6;}else break;}
    switch(n){case 0:status();break;case 1:inventory();break;case 2:if(!game.save_enabled)describe("现在不能保存。");else if((depth?save_checkpoint():save_game()))describe("已保存。可以关闭模拟器后继续游戏。");else describe("保存校验失败，请保留当前运行状态。");break;case 3:equipment_menu();break;case 4:field_skill_menu();break;}engine_clock_paused=old_pause;}
