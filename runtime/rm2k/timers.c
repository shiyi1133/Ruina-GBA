/* Original 60-frame timer accounting, including the extra 59-frame offset.
 * Adapted from pinned EasyRPG Player game_party.cpp, GPL-3.0-or-later. */
#include "engine.h"
int engine_clock_paused;
int timer_seconds(int id){return id>=0&&id<2?game.timer_frames[id]/60:0;}
void timer_command(const int*p){
    parallel_revision++;
    /* This game uses the RM2000 timer. The sixth operand is RPG2003-only. */
    switch(p[0]){
    case 0:game.timer_frames[0]=(p[1]?variable(p[2]):p[2])*60+59;break;
    case 1:game.timer_active[0]=1;game.timer_visible[0]=p[3]!=0;game.timer_battle[0]=p[4]!=0;break;
    case 2:game.timer_active[0]=game.timer_visible[0]=0;break;
    default:fault(9083);
    }
}
void engine_tick(void){int i;if(engine_clock_paused)return;for(i=0;i<2;i++)if(game.timer_active[i]&&(game.timer_battle[i]||!battle_active)&&game.timer_frames[i]>0){int old=timer_seconds(i);game.timer_frames[i]--;if(timer_seconds(i)!=old)parallel_revision++;if(!timer_seconds(i))game.timer_active[i]=game.timer_visible[i]=0;}pictures_tick();animations_tick();movement_tick();presentation_tick();parallel_tick();}
