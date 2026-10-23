#include "game.h"
#include "assets.h"
static int len(const char*s){int n=0;while(s[n])n++;return n;}
void map_screen(void){world_screen();}
static void status(void){int i,from=0,dirty=1;for(;;){unsigned k;int next=from;if(dirty){clear(11);draw_text(8,5,"队伍状态 · 原始数值",2,224);
    for(i=from;i<game.party_count&&i<from+2;i++){int y=26+(i-from)*52,a=game.party[i];Actor*s=&game.actors[a];draw_text(8,y,s->name,1,112);draw_text(143,y,"LV",6,20);draw_num(161,y,s->level,1);draw_text(8,y+14,"HP",6,18);draw_num(27,y+14,s->hp,1);draw_text(49,y+14,"/",6,6);draw_num(57,y+14,stat(a,0),6);draw_text(94,y+14,"MP",6,18);draw_num(112,y+14,s->mp,1);draw_text(135,y+14,"/",6,6);draw_num(143,y+14,stat(a,1),6);draw_text(8,y+28,s->title,2,220);}
    if(game.party_count>2){draw_num(194,143,from+1,6);draw_text(205,143,"/",6,6);draw_num(214,143,game.party_count,6);}flip();dirty=0;}k=wait_frame();if(k&KEY_B)return;if(k&KEY_DOWN)next=clamp(from+1,0,game.party_count-1);if(k&KEY_UP)next=clamp(from-1,0,game.party_count-1);if(next!=from){from=next;dirty=1;}}}
static void inventory(void){int id=inventory_select(0),option,aid=0;if(!id)return;{static const char menu[]="使用/查看说明/返回";option=choices((LcfSpan){(const u8*)menu,len(menu)},3);}if(option==1){message(field(item_data[id],2));return;}if(option!=0)return;
    if(val(item_data[id],3,0)<6){describe("这件物品不能直接使用，可查看说明或通过装备菜单操作。");return;}
    if(val(item_data[id],3,0)!=10&&!val(item_data[id],31,0)){aid=party_select();if(!aid)return;}
    if(!use_map_item(id,aid)&&!halt_code)describe("没有产生效果。");
}
void system_menu(void){static const char menu[]="队伍状态/随身物品/保存游戏/装备/特技/返回地图";int old_pause=engine_clock_paused,n;engine_clock_paused=1;n=choices((LcfSpan){(const u8*)menu,len(menu)},6);switch(n){case 0:status();break;case 1:inventory();break;case 2:if(!game.save_enabled)describe("现在不能保存。");else if((depth?save_checkpoint():save_game()))describe("已保存。可以关闭模拟器后继续游戏。");else describe("保存校验失败，请保留当前运行状态。");break;case 3:equipment_menu();break;case 4:field_skill_menu();break;}engine_clock_paused=old_pause;}
