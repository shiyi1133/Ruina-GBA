#ifndef RM2K_TYPES_H
#define RM2K_TYPES_H
#include "lcf.h"
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned char u8;
typedef struct { const u8 *pixels; u16 width, height; const u32 *rows; const u8 *palette; u8 encoding,transparent;u16 stored_width,stored_height;const u16*colors;u16 color_count; } Image;
typedef struct {const u16*colors;const u8*nearest;const u8*source_remap;unsigned lookup_bits;const u16*sorted_colors;const u8*sorted_indices;} ScenePalette;
extern const ScenePalette image_scenes[];
unsigned image_scene_nearest(const ScenePalette*scene,unsigned index);
extern const unsigned image_scene_count;
int chipset_quadrant(int atlas,int x,int y);
int decode_image_span(const Image*image,int y,int x,int length,u8*row,unsigned capacity);
int decode_image_row(const Image*image,int y,u8*row,unsigned capacity);
int decode_image_storage_row(const Image*image,int y,u8*row,unsigned capacity);
int decode_image_storage_span(const Image*image,int y,int x,int length,u8*row,unsigned capacity);
/* Borrow one stored 8x8 tile until the next image decoder/scratch call. */
const u8*image_storage_tile(const Image*image,int tile_x,int tile_y);
/* Lossless native OBJ pixels, borrowed until the next image decoder call. */
const u8*image_portrait_pixels(const u8*packed);
int image_unpack_block(const u8*in,unsigned size,u8*out,unsigned capacity);
typedef struct {int kind;u32 hash;int image;} ResourceImage;
extern const ResourceImage resource_images[];
extern const unsigned resource_image_count;
int resource_image(int kind,LcfSpan name);
extern const Image images[];
extern const u16 game_palette[256];
extern const u16 glyph_codes[];
extern const u16 glyph_rows[][12];
extern const u16 exfont_rows[52][12];
extern const short map_image_ids[],face_image_ids[][16];
extern const u32 face_name_hashes[];
extern const short enemy_image_ids[],story_image_ids[];
extern const u32 story_name_hashes[];
int story_image(LcfSpan name);
int face_image(LcfSpan name,int index);
void picture_scaled(int id,int x,int y,int width,int height);
void picture_region_scaled(int id,int x,int y,int sx,int sy,int sw,int sh,int width,int height,int transparent,int opacity,const u8*tone);
#define KEY_A 1
#define KEY_B 2
#define KEY_SELECT 4
#define KEY_START 8
#define KEY_RIGHT 16
#define KEY_LEFT 32
#define KEY_UP 64
#define KEY_DOWN 128
#define KEY_R 256
#define KEY_L 512
void *memcpy(void *dest,const void *src,unsigned int n);
void *memset(void *dest,int value,unsigned int n);
int clamp(int n,int lo,int hi);
void video_init(void);
void *image_decode_scratch(void);
void video_brightness(int level);
void video_scene_palette(int image);
unsigned video_ticks(void);
unsigned video_clock(void);
unsigned video_revision(void);
void video_clip(int x,int y,int width,int height);
void video_map_cursor(int x,int y,int visible);
void video_overlays_present(void);
int video_map_active(void);
void *video_map_scratch(void);
void video_map_upload(int x,int y,int width,int height,int camera_x,int camera_y);
void video_map_cache_reset(void);
int video_map_reuse(int x,int y,int width,int height,int camera_x,int camera_y);
void video_map_objects_begin(void);
int video_map_objects_retry(void);
void video_map_scene_reset(void);
void video_map_actor(int image,int index,int direction,int x,int y);
void video_map_point(int x,int y,int selected,int reachable);
void video_map_player(int x,int y);
void video_map_hud(int image,int x,int y);
void video_map_present(int camera_x,int camera_y,int directions);
unsigned wait_frame(void);
void clear(int color);
void box(int x,int y,int w,int h,int fill);
void rect(int x,int y,int w,int h,int color);
void picture(int id,int x,int y,int sx,int sy,int w,int h,int transparent);
void portrait(int id,int x,int y);
int draw_text(int x,int y,const char *text,int color,int max_width);
void draw_num(int x,int y,int n,int color);
void flip(void);
#endif
