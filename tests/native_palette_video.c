/* Controlled preparation of a native indexed map outside world_redraw().
 * Production world_redraw brackets the same video call with base_only=1.
 * Bitmap/portrait transitions still use the ordinary production selector. */
#include "engine.h"
static int fixture_preparing_native;
static int fixture_cached_background(void){return fixture_preparing_native||world_cached_background();}
#define world_cached_background fixture_cached_background
#include "../platform/gba/video.c"
#undef world_cached_background
void fixture_native_palette(int image){fixture_preparing_native=1;video_scene_palette(image);fixture_preparing_native=0;}
