#include "game.h"
#include "assets.h"
#include "music_matrix_config.h"
int main(void){
 unsigned i;video_init();audio_init();init_game();depth=0;engine_clock_paused=1;
 for(i=0;i<sizeof(music_matrix)/sizeof(music_matrix[0]);i++){
  const unsigned*r=music_matrix[i];int j;
  audio_music((Music){0,100,100,50},0);audio_music_quality(r[1]);audio_music((Music){r[0],90,r[3],50},0);audio_pause_music(1);audio_music_position(r[2]);audio_pause_music(0);
  for(j=0;j<8;j++)audio_service();
  clear(11);draw_text(8,8,"原曲简化音色：运行检查",1,220);draw_num(8,30,r[0],2);draw_num(80,30,r[1],3);flip();debug_state[14]=i+1;
  while(!(wait_frame()&KEY_A)){}
 }
 debug_state[14]=999;for(;;)wait_frame();
}
