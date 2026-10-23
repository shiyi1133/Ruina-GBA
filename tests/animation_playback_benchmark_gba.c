/* Identical original animation sequences; only observation data are added. */
#include "game.h"
#include "balanced.h"
extern volatile u32 video_frame_counter;
extern volatile u32 audio_stream_debug[4];
void animation_fixture_setup(void);
volatile u32 animation_playback_samples[4][5];
int main(void){int i;static const int ids[4]={46,62,78,191};static const unsigned masks[4]={2,16,112,112};
 video_init();audio_init();init_game();depth=0;animation_fixture_setup();
 audio_music((Music){1,90,100,50},0);for(i=0;i<8;i++)audio_service();
 for(i=0;i<4;i++){
  draw_background();flip();debug_state[18]=i+1;while(!(wait_frame()&KEY_A)){}
  animation_playback_samples[i][0]=video_frame_counter;animation_playback_samples[i][2]=audio_stream_debug[0];
  animation_targets(masks[i]);animation_battle(ids[i]);
  animation_playback_samples[i][1]=video_frame_counter;animation_playback_samples[i][3]=audio_stream_debug[0];animation_playback_samples[i][4]=halt_code;
  debug_state[18]=0x100+i;while(!(wait_frame()&KEY_A)){}
 }
 debug_state[18]=0x600d;for(;;)wait_frame();
}
