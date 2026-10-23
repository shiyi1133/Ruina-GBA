#include "game.h"
#include "assets.h"
static void halted_screen(void){presentation_reset();debug_state[15]=5;for(;;){unsigned k;draw_scene();box(4,21,232,134,11);rect(4,21,232,134,4);draw_text(12,28,"移植校验暂停",4,215);draw_text(12,49,"遇到尚未支持的原版逻辑。",1,215);draw_text(12,65,"本版不跳过、不替换规则。",1,215);draw_text(12,89,"指令 / 校验号",6,180);draw_num(150,89,halt_code,2);if(depth){draw_text(12,105,"公共事件",6,80);draw_num(75,105,stack[depth-1].common_id,2);draw_text(112,105,"地图事件",6,80);draw_num(180,105,stack[depth-1].event_id,2);}draw_text(12,135,"START 返回标题",2,215);flip();k=wait_frame();if(k&KEY_START){depth=0;halt_code=0;return;}}}
int main(void){
    video_init();audio_init();for(;;){int choice;presentation_reset();audio_music((Music){0,100,100,50},0);scene_image=IMG_TITLE;video_scene_palette(IMG_TITLE);clear(0);picture(IMG_TITLE,0,0,0,0,240,160,0);flip();while(!(wait_frame()&KEY_A)){}
        {static const char menu[]="开始游戏/继续游戏/制作信息/音乐欣赏";choice=choices((LcfSpan){(const u8*)menu,sizeof(menu)-1},0);}
        if(choice==2){current_face=-1;describe("胖胖&咩咩 移植\n原作：枯草章吉\n汉化、修复名单见原版说明。\n完整通关与实机尚未验收。\n源码、操作与验证见发布说明。");continue;}
        if(choice==3){music_room();continue;}
        init_game();chapter_notice=0;if(choice==1){if(!load_game()){describe("没有可读取的存档，或存档校验未通过。");continue;}audio_restore();}
        while(!halt_code){run_events();if(halt_code)break;if(!depth)map_screen();}
        if(halt_code==RM2K_GameOver||halt_code==RM2K_ReturntoTitleScreen){depth=0;halt_code=0;continue;}if(halt_code)halted_screen();
    }
}
