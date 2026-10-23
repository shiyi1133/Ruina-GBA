#include "game.h"
#include "assets.h"
extern const char*const music_room_names[];
volatile u32 music_room_video_metrics[5];/* full, lists, rows, footer, badges */
static void row(int index,int selected,int from){
    int y=38+(index-from)*14,tid=audio_music_id(index);
    box(3,y-1,234,14,index==selected?8:11);
    if(index==selected)draw_text(5,y,">",2,8);
    draw_text(16,y,music_room_names[tid],index==selected?1:6,215);music_room_video_metrics[2]++;
}
static void footer(int playing,int second,int finished){
    unsigned seconds=playing>=0?audio_music_frames(audio_music_id(playing))/16384:0;
    box(7,136,226,14,11);
    if(playing>=0){draw_text(8,137,finished?"已结束":audio_music_paused()?"已暂停":"播放中",3,48);draw_num(65,137,second/60,1);draw_text(84,137,":",1,6);draw_num(91,137,second%60,1);draw_text(112,137,"/",6,6);draw_num(125,137,seconds/60,6);draw_text(145,137,":",6,6);draw_num(152,137,seconds%60,6);}
    else draw_text(8,137,"选择曲目试听",6,132);music_room_video_metrics[3]++;
}
void music_room(void){
    Music previous=game.music;unsigned previous_position=audio_debug[3];
    int old_pause=engine_clock_paused,old_quality=audio_current_quality(),selected=0,playing=-1,dirty=1,last_second=-1,last_finished=-1,quality=1;
    int first=1,last_selected=-1,last_from=-1,last_quality=-1,last_playing=-2,last_paused=-1;unsigned revision=0;
    int count=audio_music_count();engine_clock_paused=1;audio_music((Music){0,100,100,50},0);audio_music_quality(quality);debug_state[15]=18;
    for(;;){
        unsigned k;int second=(int)(audio_debug[3]/16384),finished=playing>=0&&audio_music_finished(),paused=audio_music_paused();
        debug_state[16]=selected;debug_state[17]=count;debug_state[18]=playing+1;debug_state[19]=quality;debug_state[23]=paused;
        if(dirty||second!=last_second||finished!=last_finished){
            int from=selected>3?selected-3:0,i,full=first||revision!=video_revision();
            if(from+7>count)from=count>7?count-7:0;
            if(full){video_scene_palette(-1);clear(11);draw_text(8,3,"音乐欣赏 · 简化音色",2,224);music_room_video_metrics[0]++;}
            if(full||selected!=last_selected){box(7,18,74,14,11);draw_num(8,19,selected+1,1);draw_text(32,19,"/",6,10);draw_num(43,19,count,1);}
            if(full||quality!=last_quality){box(90,18,142,14,11);draw_text(91,19,quality?"欣赏 [START]":"游玩 [START]",quality?3:6,140);music_room_video_metrics[4]++;}
            if(full||from!=last_from){box(3,37,234,98,11);for(i=from;i<count&&i<from+7;i++)row(i,selected,from);music_room_video_metrics[1]++;}
            else if(selected!=last_selected){row(last_selected,selected,from);row(selected,selected,from);}
            if(full||playing!=last_playing||second!=last_second||finished!=last_finished||paused!=last_paused)footer(playing,second,finished);
            flip();last_second=second;last_finished=finished;last_selected=selected;last_from=from;last_quality=quality;last_playing=playing;last_paused=paused;revision=video_revision();first=dirty=0;
        }
        k=wait_frame();if(k&KEY_B)break;
        if(k&KEY_DOWN){selected=(selected+1)%count;dirty=1;}
        if(k&KEY_UP){selected=(selected+count-1)%count;dirty=1;}
        if(k&(KEY_LEFT|KEY_RIGHT|KEY_L|KEY_R)){selected=(selected+count+((k&(KEY_RIGHT|KEY_R))?1:-1))%count;k|=KEY_A;playing=-1;dirty=1;}
        if(k&KEY_START){unsigned pos=audio_debug[3];int was_paused=audio_music_paused();quality=!quality;if(playing>=0)audio_music((Music){0,100,100,50},0);audio_music_quality(quality);if(playing>=0){Music now={audio_music_id(playing),90,100,50};audio_music((Music){0,100,100,50},0);audio_music(now,0);audio_music_position(pos);audio_pause_music(was_paused);}dirty=1;}
        if(k&KEY_A){if(playing==selected&&!audio_music_finished())audio_pause_music(!audio_music_paused());else{audio_music((Music){0,100,100,50},0);audio_music((Music){audio_music_id(selected),90,100,50},0);playing=selected;}dirty=1;}
    }
    audio_music((Music){0,100,100,50},0);audio_music_quality(old_quality);audio_music(previous,0);audio_music_position(previous_position);
    engine_clock_paused=old_pause;debug_state[15]=0;world_render_invalidate();
}
