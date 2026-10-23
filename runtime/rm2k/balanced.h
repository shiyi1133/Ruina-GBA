#ifndef RUINA_BALANCED_RUNTIME_H
#define RUINA_BALANCED_RUNTIME_H
#include "engine.h"
extern volatile u32 balanced_surface_epoch;
int balanced_rgb_mode(void);
void balanced_animation_cell(const Image*image,int x,int y,int w,int h,int opacity,const u8*tone);
void balanced_animation_flash(int x,int y,int w,int h,int r,int g,int b,int power);
void balanced_animation_target_flash(int image,int x,int y,int w,int h,int r,int g,int b,int power);
void balanced_animation_background_store(void);
int balanced_animation_background_restore(int x,int y,int w,int h);
void*balanced_save_workspace(void);
u32 balanced_scene_stamp(void);
int balanced_native_ui_begin(void);
void balanced_native_ui_end(void);
void balanced_menu_background(int x,int y,int width,int height);
u32 battle_render_stamp(void);
u32 battle_background_stamp(void);
void balanced_menu_invalidate(void);
int balanced_battle_cache_store(void);
void balanced_battle_cache_restore(int x,int y,int width,int height);
#endif
