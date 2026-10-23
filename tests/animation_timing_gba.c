#include "game.h"
#include "animation_timing_cases.h"
void animation_fixture_setup(void);
extern volatile u32 audio_stream_debug[4];
extern volatile u32 animation_render_trace[16];
volatile u32 timing_case_audio[2];
int main(void){unsigned i;
 video_init();audio_init();init_game();depth=0;animation_fixture_setup();draw_background();flip();audio_music((Music){1,90,100,50},0);
 debug_state[18]=1;while(!(wait_frame()&KEY_A)){}
 for(i=0;i<sizeof(timing_cases)/sizeof(timing_cases[0]);i++){
  animation_playback_mode(timing_cases[i][1]);animation_render_trace[10]=0;timing_case_audio[0]=audio_stream_debug[0];animation_targets(112);animation_battle(timing_cases[i][0]);timing_case_audio[1]=audio_stream_debug[0];
  debug_state[18]=100+i;while(!(wait_frame()&KEY_A)){}
 }
 debug_state[18]=0x600d;for(;;)wait_frame();
}
