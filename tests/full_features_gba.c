#include "game.h"
#include "assets.h"
/* Separate test cartridge. Controlled starting states unlock specific source
 * interfaces; this file is never linked into the playable release. */
int main(void){int option,i;static const char menu[]="Walk and touch/Original handbook/Original world map/Original weapon workshop/Original armor workshop";
 video_init();audio_init();scene_image=IMG_TITLE;option=choices((LcfSpan){(const u8*)menu,sizeof(menu)-1},0);
 init_game();depth=0;set_map(3,15,12);game.party_count=1;game.party[0]=1;game.vars[2]=1;game.vars[41]=20;game.vars[26]=100;game.menu_enabled=game.save_enabled=1;game.gold=99999;
 game.vars[51]=3;game.vars[52]=15;game.vars[53]=12;for(i=1;i<=MAX_ITEM;i++)game.items[i]=50;for(i=1;i<=MAX_SKILL;i++)set_learned(1,i,1);actor_level(1,10);game.actors[1].hp=stat(1,0);game.actors[1].mp=stat(1,1);
 if(option==1)push_common(132);else if(option==2)push_common(129);else if(option>=3){game.vars[201]=1;game.vars[29]=1;set_map(option==3?14:15,1,1);}else {game.vars[41]=1;set_map(23,15,12);push_common(5);}
 while(!halt_code){run_events();if(!depth)map_screen();}for(;;)wait_frame();
}
