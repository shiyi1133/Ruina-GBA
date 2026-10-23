#include "game.h"
#include "assets.h"
#include "balanced.h"
#include "map_window_matrix_config.h"
static unsigned stage;
volatile u32 map_window_matrix_state[4];
extern volatile u32 audio_stream_debug[4];
volatile u32 map_window_matrix_audio[3];
volatile u32 map_window_matrix_music[2];
extern const u8 original_portraits_start[];
static int face(unsigned index){const u32*h=(const u32*)original_portraits_start;const u16*r=(const u16*)(original_portraits_start+h[2]);return r[index%h[1]*4];}
static void hold(unsigned kind){
    map_window_matrix_state[0]=game.map;map_window_matrix_state[1]=kind;
    debug_state[14]=++stage;while(!(wait_frame()&KEY_A)){}
}
static void world(unsigned kind){
#ifdef WINDOW_REFERENCE_FULL
    world_render_invalidate();
#endif
    world_redraw();if(!kind)map_window_matrix_audio[2]=audio_stream_debug[0];hold(kind);
}
int main(void){
    unsigned n,i;video_init();audio_init();init_game();if(!load_game())for(;;)wait_frame();
    depth=0;engine_clock_paused=1;scene_image=-1;game.screen_hidden=0;
    audio_music_quality(window_music_quality);audio_music((Music){window_music_id,90,100,50},0);
    for(n=0;n<sizeof(window_maps)/sizeof(window_maps[0]);n++){
        map_window_matrix_audio[0]=audio_stream_debug[0];map_window_matrix_music[0]=audio_debug[1];set_map(window_maps[n],5,5);map_window_matrix_audio[1]=audio_stream_debug[0];map_window_matrix_music[1]=audio_debug[1];depth=0;scene_image=-1;game.selected=0;
        for(i=1;i<=MAX_PICTURE;i++)game.pictures[i].image=-1;
        game.pan_locked=1;game.camera_lock_x=-40;game.camera_lock_y=-40;parallel_revision++;
        if(!world_native_map())continue;
        world(0);
        draw_scene();box(12,70,216,72,11);draw_text(22,80,"在地图上打开对话窗口",1,200);
        draw_text(22,100,"保留原图与人物的颜色",2,200);portrait(face(n*7),12,10);flip();hold(1);
        world(2);
        game.camera_lock_x=216;game.camera_lock_y=216;parallel_revision++;world(3);
        draw_scene();box(8,18,224,134,11);draw_text(20,30,"第一行文字",1,200);draw_text(20,50,"第二行文字",2,200);
        draw_text(20,70,"第三行文字",5,200);flip();hold(4);
        world(5);
        game.camera_lock_x=-40;game.camera_lock_y=-40;parallel_revision++;world(6);
        /* Real SRAM compression borrows the shared CPU drawing surface. */
        map_window_matrix_state[2]=save_game();world(7);
        video_scene_palette(IMG_TITLE);clear(11);picture_scaled(IMG_TITLE,0,0,240,160);portrait(face(n*7+1),12,10);flip();hold(8);
        world(9);map_window_matrix_state[3]++;
    }
    debug_state[14]=0x600d;for(;;)wait_frame();
}
