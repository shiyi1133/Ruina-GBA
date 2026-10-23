#include "game.h"
#include "assets.h"
extern const char*const music_room_names[];
/* No map/event animation runs in this room. The score and original clock are
 * shared with gameplay; only the explicitly simplified presentation differs. */
void music_room(void){
 Music previous=game.music;unsigned previous_position=audio_debug[3];
 int old_pause=engine_clock_paused,old_quality=audio_current_quality(),selected=0,playing=-1,dirty=1,last_second=-1,last_finished=-1,quality=1;
 int count=audio_music_count();engine_clock_paused=1;audio_music((Music){0,100,100,50},0);audio_music_quality(quality);debug_state[15]=18;
 for(;;){
  unsigned k;debug_state[16]=selected;debug_state[17]=count;debug_state[18]=playing+1;debug_state[19]=quality;debug_state[23]=audio_music_paused();int second=(int)(audio_debug[3]/16384),finished=playing>=0&&audio_music_finished();
  if(dirty||second!=last_second||finished!=last_finished){
   int from=selected>3?selected-3:0,i,y;unsigned seconds=playing>=0?audio_music_frames(audio_music_id(playing))/16384:0;
   if(from+7>count)from=count>7?count-7:0;
   clear(11);draw_text(8,3,"音乐欣赏 · 简化音色",2,224);draw_num(8,19,selected+1,1);draw_text(32,19,"/",6,10);draw_num(43,19,count,1);
   draw_text(91,19,quality?"欣赏 [START]":"游玩 [START]",quality?3:6,140);
   for(i=from,y=38;i<count&&i<from+7;i++,y+=14){int tid=audio_music_id(i);if(i==selected){box(3,y-1,234,14,8);draw_text(5,y,">",2,8);}draw_text(16,y,music_room_names[tid],i==selected?1:6,215);}
   if(playing>=0){draw_text(8,137,finished?"已结束":audio_music_paused()?"已暂停":"播放中",3,48);draw_num(65,137,second/60,1);draw_text(84,137,":",1,6);draw_num(91,137,second%60,1);draw_text(112,137,"/",6,6);draw_num(125,137,seconds/60,6);draw_text(145,137,":",6,6);draw_num(152,137,seconds%60,6);}
   else draw_text(8,137,"选择曲目试听",6,132);
   flip();last_second=second;last_finished=finished;dirty=0;
  }
  k=wait_frame();if(k&KEY_B)break;
  if(k&KEY_DOWN){selected=(selected+1)%count;dirty=1;}
  if(k&KEY_UP){selected=(selected+count-1)%count;dirty=1;}
  if(k&(KEY_LEFT|KEY_RIGHT|KEY_L|KEY_R)){selected=(selected+count+((k&(KEY_RIGHT|KEY_R))?1:-1))%count;k|=KEY_A;playing=-1;dirty=1;}
  if(k&KEY_START){unsigned pos=audio_debug[3];int paused=audio_music_paused();quality=!quality;if(playing>=0)audio_music((Music){0,100,100,50},0);audio_music_quality(quality);if(playing>=0){Music now={audio_music_id(playing),90,100,50};audio_music((Music){0,100,100,50},0);audio_music(now,0);audio_music_position(pos);audio_pause_music(paused);}dirty=1;}
  if(k&KEY_A){if(playing==selected&&!audio_music_finished())audio_pause_music(!audio_music_paused());else{audio_music((Music){0,100,100,50},0);audio_music((Music){audio_music_id(selected),90,100,50},0);playing=selected;}dirty=1;}
 }
 audio_music((Music){0,100,100,50},0);audio_music_quality(old_quality);audio_music(previous,0);audio_music_position(previous_position);
 engine_clock_paused=old_pause;debug_state[15]=0;world_render_invalidate();
}
