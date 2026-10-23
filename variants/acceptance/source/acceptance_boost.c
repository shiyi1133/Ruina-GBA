/* Acceptance variant only. Ordinary skill costs, weapons, events,
 * damage and save format are unchanged. Grant once per fresh new game. */
#include "game.h"
static int pending;
volatile u32 acceptance_boost_trace[4];/* grants, actors, skills/actor, cap */
static const u16 actors[]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,16,17,18,19,20};
static const u16 skills[]={4,5,7,8,9,10,11,12,21,22,23,26,27,28,30,31,33,34,35,37,38,39,40,41,42,44,45,46,49,52,53,54,59,60,61,62,63,64,65,66,67,68,69,70,72,73,74,77,78,79,80,82,83,84,85,86,92,95,96,97,98,99,101,102,103,104,109,110,111,112,113,114,118,119,120,121,122,123,124,125,126,127,129,132,133,134,139,140,141,142,143,144,145,149,150,152,153,155,156,157,158,159,160,162,163,169,170,171,172,173,175,182,183,184,185,186,188,190,191,192,193,194,195,201,202,203,204,212,214,215,216,217,219,220,221,222,224,225,226,227,228,229,230,231,235,241,242,243,244,245,246,248,256,257,259,260,261,263,265,266,267,268,269,270,274,276,280,281,283,284,285,286,287,288,289,291,292,293,294,296,297,301,306,307,308,309,346,399,400,401,402,403,404,410};
void acceptance_boost_arm(void){pending=1;memset((void*)acceptance_boost_trace,0,sizeof(acceptance_boost_trace));}
void acceptance_boost_skip(void){pending=0;}
void acceptance_boost_prepare(void){
    unsigned i,j;if(!pending||game.map==RUINA_START_MAP||!game.party_count)return;
    pending=0;
    for(i=0;i<sizeof(actors)/sizeof(actors[0]);i++){
        int id=actors[i];Actor*a=&game.actors[id];
        for(j=0;j<6;j++)a->bonus[j]=999;
        for(j=0;j<sizeof(skills)/sizeof(skills[0]);j++){
            set_learned(id,skills[j],1);if(!(j&31))audio_service();
        }
        a->hp=stat(id,0);a->mp=stat(id,1);
    }
    /* A legal one-handed magic blade supplies all spell weapon attributes.
     * Keep the selected protagonist's original weapon, with three spares
     * for manually equipping later companions. Do not loot future actors. */
    for(i=0;i<(unsigned)game.party_count;i++){
        int id=game.party[i];Actor*a=&game.actors[id];
        if(id>=1&&id<=4){int old=a->equipment[0];
            if(old&&old!=453)game.items[old]=clamp(game.items[old]+1,0,99);
            a->equipment[0]=453;
        }
    }
    game.items[453]=clamp(game.items[453]+3,0,99);
    acceptance_boost_trace[0]++;acceptance_boost_trace[1]=sizeof(actors)/sizeof(actors[0]);
    acceptance_boost_trace[2]=sizeof(skills)/sizeof(skills[0]);acceptance_boost_trace[3]=999;
}
