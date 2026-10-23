#include "game.h"
#include "assets.h"
#include "native_midi.h"
/* Separate cartridge: automatic original battle10 playback. A fresh boot and
 * normal audio_music() exercise the production interrupt path. */
int main(void){
 video_init();audio_init();init_game();depth=0;scene_image=IMG_TITLE;
 audio_music((Music){5,100,100,50},0);
 clear(0);draw_text(8,20,"Original MIDI playback test",1,225);flip();
 for(;;){wait_frame();debug_state[14]++;}
}
