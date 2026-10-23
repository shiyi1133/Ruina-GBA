#include "engine.h"
unsigned proof_game_size(void){return sizeof(Game);}
unsigned proof_extension_offset(void){return (unsigned long)&((Game*)0)->extra_positions;}
