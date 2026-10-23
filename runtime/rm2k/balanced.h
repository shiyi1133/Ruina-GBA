#ifndef RUINA_BALANCED_RUNTIME_H
#define RUINA_BALANCED_RUNTIME_H
#include "engine.h"
extern volatile u32 balanced_surface_epoch;
int balanced_rgb_mode(void);
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
