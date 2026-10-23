#include "game.h"
#include "assets.h"
#include "music_complete_config.h"
extern volatile u32 audio_stream_debug[4];
int main(void){
 unsigned i;video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
 for(i=0;i<sizeof(music_complete)/sizeof(music_complete[0]);i++){
  const unsigned*r=music_complete[i];int j;
  audio_music((Music){0,100,100,50},0);audio_music_quality(r[1]);audio_music((Music){r[0],90,100,50},0);
  for(j=0;j<8;j++)audio_service();
  debug_state[13]=audio_stream_debug[0];
  clear(11);draw_text(8,8,"原曲简化音色：整曲检查",1,220);draw_num(8,30,r[0],2);draw_num(80,30,r[1],3);flip();debug_state[14]=i+1;
  while(!(wait_frame()&KEY_A)){}
 }
 debug_state[14]=999;for(;;)wait_frame();
}
