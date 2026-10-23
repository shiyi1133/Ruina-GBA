/* Deliberate test entry point, never linked into the game ROM.
 * Uses the unchanged original troop 202 to exercise ten target choices. */
#include "engine.h"
int main(void){int i;static const int party[4]={1,6,7,4};video_init();audio_init();engine_init(123);audio_reset();set_map(23,2,3);game.party_count=4;for(i=0;i<4;i++)game.party[i]=party[i];battle(202,1,1,0);for(;;)wait_frame();}
