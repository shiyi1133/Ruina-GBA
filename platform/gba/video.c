#include "gba_hw.h"
#include "types.h"
#include "assets.h"
#include "audio.h"
#include "balanced.h"
extern void engine_tick(void);
volatile u32 native_whole_tile_metrics[2];
static u16 framebuffer[240*160] __attribute__((aligned(4)));
static int clip_left,clip_top,clip_right=240,clip_bottom=160;
static unsigned framebuffer_revision;
static const ScenePalette*drawing_scene,*display_scene;
static int drawing_scene_image=-1,current_brightness;
static u8 *const global_remap=(u8*)framebuffer+38400;
static u8 (*const image_remaps)[256]=(u8(*)[256])((u8*)framebuffer+38656);
static const u16*remap_keys[8];
static unsigned remap_next;
/* Fog masks have only one or two source colors. Cache the exact palette
 * alpha result per source color/destination index, instead of doing RGB math
 * and a nearest-color search for every pixel of every cursor refresh. */
static u8 (*const blend_rows_cache)[256]=(u8(*)[256])((u8*)framebuffer+40704);
static u32 blend_keys[16];
static int page;
static int bitmap_direct;
static int native_ui,native_ui_map=-1;
static int native_ui_entering,native_ui_objects_changed;
static int native_ui_blocked_map=-1,native_ui_blocked_mode;
static unsigned native_ui_blocked_generation;
static unsigned native_ui_revision,native_ui_stamp;
static void native_ui_flip(void);
static void native_ui_damage(int,int,int,int);
static void native_ui_fill(int,int,int,int,int);
static void native_ui_glyph(int,int,const u16*,int,int,int,int,int);
volatile u32 balanced_surface_epoch;
static void rgb_clear(int);
static void rgb_box(int,int,int,int,int);
static void rgb_pixel(int,int,u16);
static void rgb_damage(int,int,int,int);
static void rgb_picture(int,int,int,int,int,int,int,int,int,int,int,const u8*);
static void rgb_portrait(int,int,int);
static void rgb_flip(void);
int balanced_rgb_mode(void){return bitmap_direct;}
void*balanced_save_workspace(void){balanced_surface_epoch++;framebuffer_revision++;if(!native_ui)world_render_invalidate();return framebuffer;}
typedef struct {u16 image,sheet;u32 tiles;} PortraitRecord;
typedef struct {const PortraitRecord*record;short x,y;} PendingPortrait;
extern const u8 original_portraits_start[];
extern const u8 portrait_combinations_start[];
extern const u8 original_characters_start[];
typedef struct {u16 image;u8 index,color_count;u32 palette,tiles;} CharacterRecord;
extern const u8 palette_rgb555_start[];
static PendingPortrait pending_portraits[4];
static int portrait_count,cached_portraits[7],cached_portrait_sheet=-1;
static unsigned portrait_visible,portrait_pending,portrait_upload_count;
static const u8*portrait_uploads[4];
static const u8*portrait_upload_remaps[4];
static u8 portrait_upload_slots[4];
static u16 object_palette[256],object_palette_dirty;
static int cursor_color=1,cursor_tile_color=1,cursor_tile_dirty;
static int cursor_x,cursor_y,cursor_visible;
static const u16 cursor_mask[64]={4369,4369,1,0,1,0,1,0,1,0,1,0,1,0,1,0,4369,17,0,16,0,16,0,16,0,16,0,16,0,16,0,16,1,0,1,0,1,0,1,0,4369,4369,0,0,0,0,0,0,0,16,0,16,0,16,0,16,4369,17,0,0,0,0,0,0};
static int map_active,map_actor_count,map_point_count,map_blink,map_objects_valid;
static int map_camera_x,map_camera_y;
static unsigned map_hints_pending;
#include "map_hints.h"
#define MAP_CACHE_ROWS 24
static short map_row_owner[MAP_CACHE_ROWS],map_column_owner[32];
static u32 map_resident[MAP_CACHE_ROWS];
/* Keep the displayed objects intact while decoding the next view. The OAM
 * stride is retained for a bounded DMA commit (1 KiB, not another framebuffer). */
static u16 map_oam[128][4] __attribute__((aligned(4)));
static int actor_cache[24];
static u32 actor_visible[2],actor_pending[2];
/* Native map preparation finishes all background uploads first. Its idle
 * 38,400-byte CPU framebuffer can stage 24 overlapping 1 KiB OBJ slots at
 * offset 4096; the first 4096 bytes remain available for two small HUDs. */
static u32 actor_deferred_uploads;
static int hud_count,hud_cache[2],object_color_count,object_palette_overflow;
static unsigned hud_pending_uploads;
volatile u32 video_native_commit_metrics[3];
volatile u32 video_native_texture_metrics[2];
volatile u32 object_palette_rebuilds;
static u32 *const object_color_cache=(u32*)((u8*)framebuffer+44800);
volatile u32 map_video_metrics[8];
static u8 image_line[1024] __attribute__((aligned(4)));
static unsigned old_keys, repeats;
static void upload_object_palette(void){
 unsigned bank=0;
 while(bank<16){unsigned first=bank,count;
  while(bank<16&&!(object_palette_dirty&(1U<<bank)))bank++;first=bank;
  while(bank<16&&(object_palette_dirty&(1U<<bank)))bank++;count=(bank-first)*16;
  if(count){REG32(0x040000d4)=(u32)(object_palette+first*16);REG32(0x040000d8)=0x05000200+first*32;REG32(0x040000dc)=0x80000000|count;}
 }object_palette_dirty=0;
}
static void upload_object_list(void){
 /* Four halfwords match real OAM stride, including the unused affine word.
  * A bounded 1 KiB DMA replaces 384 separate CPU writes. */
 REG32(0x040000d4)=(u32)map_oam;REG32(0x040000d8)=0x07000000;REG32(0x040000dc)=0x84000100;
}
volatile unsigned input_latched,input_sampled;
volatile unsigned input_triggered,input_frame_keys;
volatile unsigned ui_ready;
volatile u32 video_metrics[8];
volatile u32 video_commit_timing[4];
extern volatile u32 video_frame_counter;
static u32 last_logic_frame;
unsigned video_ticks(void){return REG16(0x04000108);}
unsigned video_revision(void){return native_ui?native_ui_revision:framebuffer_revision;}
void video_clip(int x,int y,int width,int height){
    clip_left=clamp(x,0,240);clip_top=clamp(y,0,160);
    clip_right=clamp(x+width,clip_left,240);clip_bottom=clamp(y+height,clip_top,160);
}
void* __attribute__((section(".iwram"),long_call,noinline)) memcpy(void *d,const void *s,unsigned int n) { u8 *a=d; const u8*b=s;if((((unsigned)a|(unsigned)b)&3)==0){while(n>=4){*(u32*)a=*(const u32*)b;a+=4;b+=4;n-=4;}}while(n--)*a++=*b++;return d; }
void* __attribute__((section(".iwram"),long_call,noinline)) memset(void *d,int v,unsigned int n) { u8 *a=d;u32 word=(v&255)*0x01010101U;while(n&&((unsigned)a&3)){*a++=v;n--;}while(n>=4){*(u32*)a=word;a+=4;n-=4;}while(n--)*a++=v;return d; }
int clamp(int n,int lo,int hi) {return n<lo?lo:n>hi?hi:n;}
void video_init(void) {
    volatile u16 *p=(volatile u16*)0x05000000;int i;video_frame_counter=last_logic_frame=0;
    for(i=0;i<256;i++)p[i]=game_palette[i];
    for(i=0;i<256;i++)global_remap[i]=i;
    /* Standard cartridge 3/1 ROM timing and instruction prefetch; SRAM timing
     * stays at its default four cycles. */
    REG16(0x04000204)=0x4014;REG16(0x04000000)=0x0404;
    for(i=0;i<128;i++)REG16(0x07000000+i*8)=0x0200;
    for(i=0;i<7;i++)cached_portraits[i]=-1;
    /* A separate 16x16, 4-bit OBJ. Its tile is beyond all four portrait
     * slots, so moving the cursor never rewrites background bitmap pixels. */
    for(i=0;i<64;i++){
        int tile=i/16,row=(i%16)/2,half=i&1,k;u16 packed=0;
        for(k=0;k<4;k++){int x=tile%2*8+half*4+k,y=tile/2*8+row;
            if(x<14&&y<13&&(!x||x==13||!y||y==12))packed|=1U<<(k*4);
        }REG16(0x06017f00+i*2)=packed;
    }
    video_brightness(0);
}
void video_brightness(int level){
    level=clamp(level,-16,16);
    current_brightness=level;
    REG16(0x04000050)=level?(level>0?0x00b7:0x00f7):0;
    REG16(0x04000054)=level<0?-level:level;
}
static const u16*background_colors(void){return drawing_scene?drawing_scene->colors:game_palette;}
static unsigned background_nearest(unsigned color,int exact){
 if(!drawing_scene)return palette_rgb555_start[color];
 if(drawing_scene->lookup_bits==15)return drawing_scene->nearest[color];
 if(exact){int lo=0,hi=256;while(lo<hi){int mid=(lo+hi)/2;if(drawing_scene->sorted_colors[mid]<color)lo=mid+1;else hi=mid;}if(lo<256&&drawing_scene->sorted_colors[lo]==color)return drawing_scene->sorted_indices[lo];}
 return drawing_scene->nearest[((color>>1)&15)|(((color>>6)&15)<<4)|(((color>>11)&15)<<8)];
}
void video_scene_palette(int image){
 const ScenePalette*next=image>=0&&(unsigned)image<image_scene_count?image_scenes+image:0;int i;
 int want_direct=!world_cached_background(),mode_changed=want_direct!=bitmap_direct;
 if(want_direct&&native_ui)balanced_native_ui_end();
 if(want_direct!=bitmap_direct){bitmap_direct=want_direct;balanced_surface_epoch++;drawing_scene=0;for(i=0;i<8;i++)remap_keys[i]=0;for(i=0;i<16;i++)blend_keys[i]=0;if(bitmap_direct)map_objects_valid=0;}
 if(bitmap_direct){drawing_scene=next;drawing_scene_image=next?image:-1;return;}
 if(next==drawing_scene&&!mode_changed)return;drawing_scene=next;drawing_scene_image=next?image:-1;
 for(i=0;i<256;i++)global_remap[i]=background_nearest(game_palette[i],1);
 for(i=0;i<8;i++)remap_keys[i]=0;
 for(i=0;i<16;i++)blend_keys[i]=0;
}
static const u8*image_color_map(const Image*im){
 unsigned i,slot,n;if(!im->colors)return global_remap;
 for(i=0;i<8;i++)if(remap_keys[i]==im->colors)return image_remaps[i];slot=remap_next++&7;
 if(drawing_scene_image>=0&&im->colors==images[drawing_scene_image].colors)memcpy(image_remaps[slot],drawing_scene->source_remap,256);
 else {n=im->color_count?im->color_count:im->encoding>=1&&im->encoding<=4?16:256;for(i=0;i<n;i++)image_remaps[slot][i]=background_nearest(im->colors[i],1);}
 remap_keys[slot]=im->colors;return image_remaps[slot];
}
static int prepare_blend_rows(const Image*im,const u16*toned,int alpha,const u8**rows){
 unsigned i,j,pinned=0,count=im->color_count?im->color_count:im->encoding>=1&&im->encoding<=4?16:256;u32 keys[16];const u16*bg=background_colors();
 if(!im->colors||count>16||!count)return 0;
 for(i=0;i<count;i++){
  unsigned color=toned?toned[i]:im->colors[i];keys[i]=0x80000000U|color|((unsigned)alpha<<15);rows[i]=0;
  for(j=0;j<16;j++)if(blend_keys[j]==keys[i]){pinned|=1U<<j;rows[i]=blend_rows_cache[j];break;}
 }
 for(i=0;i<count;i++)if(!rows[i]){
  unsigned slot,color=keys[i]&32767U,rb=(color&0x7c1f)*(32-alpha),green=(color&0x03e0)*(32-alpha);
  for(slot=0;slot<16&&blend_keys[slot]!=keys[i];slot++){}
  if(slot==16){for(slot=0;slot<16&&(pinned&(1U<<slot));slot++){}
   if(slot==16)return 0;
   for(j=0;j<256;j++){unsigned c=bg[j],v=(((rb+(c&0x7c1f)*alpha)>>5)&0x7c1f)|(((green+(c&0x03e0)*alpha)>>5)&0x03e0);blend_rows_cache[slot][j]=background_nearest(v,0);}
   blend_keys[slot]=keys[i];
  }pinned|=1U<<slot;rows[i]=blend_rows_cache[slot];
 }return 1;
}
static void upload_background_palette(void){
 const u16*colors=background_colors();if(drawing_scene==display_scene)return;
 REG32(0x040000d4)=(u32)colors;REG32(0x040000d8)=0x05000000;/* RGB555 arrays are halfword-aligned C objects. A word DMA rounds a
  * 2-byte-aligned source down, shifting every scene color by one entry. */
 REG32(0x040000dc)=0x80000100;display_scene=drawing_scene;
}
int face_image(LcfSpan name,int index){u32 h=2166136261U;unsigned i;for(i=0;i<name.size;i++){h^=name.data[i];h*=16777619U;}if(index<0||index>=16)return -1;for(i=0;i<FACE_SHEET_COUNT;i++)if(face_name_hashes[i]==h)return face_image_ids[i][index];return -1;}
int story_image(LcfSpan name){u32 h=2166136261U;unsigned i;for(i=0;i<name.size;i++){h^=name.data[i];h*=16777619U;}for(i=0;i<STORY_IMAGE_COUNT;i++)if(story_name_hashes[i]==h)return story_image_ids[i];return -1;}
unsigned wait_frame(void) {
    unsigned keys,result,ime;
    /* A completed presentation may already have crossed the next VBlank.
     * Consume that frame once instead of adding another idle frame after
     * every map redraw. Nested UI waits still get one tick per frame. */
    while(video_frame_counter==last_logic_frame)audio_service();
    last_logic_frame=video_frame_counter;
    ime=REG16(0x04000208);REG16(0x04000208)=0;
    keys=(~REG16(0x04000130))&1023;result=input_latched|(keys&~input_sampled);input_latched=0;input_sampled=keys;REG16(0x04000208)=ime;
    if(keys==old_keys&&keys) {repeats++;if(repeats>24&&repeats%6==0)result|=keys&(KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT);}
    else repeats=0;
    old_keys=keys;input_frame_keys=keys|result;input_triggered=result;ui_ready=0;engine_tick();
    if(map_active){map_blink++;REG16(0x07000000+120*8+4)=808+((map_blink>>4)&1)*8;}
    ui_ready=1;return result;
}
void clear(int c){if(bitmap_direct){rgb_clear(c);return;}ui_ready=0;portrait_count=0;cursor_visible=0;framebuffer_revision++;if(native_ui){native_ui_fill(clip_left,clip_top,clip_right,clip_bottom,c);return;}if(!clip_left&&!clip_top&&clip_right==240&&clip_bottom==160)memset(framebuffer,c,38400);else box(clip_left,clip_top,clip_right-clip_left,clip_bottom-clip_top,c);}
void video_map_cursor(int x,int y,int visible){cursor_x=x;cursor_y=y;cursor_visible=visible&&x> -16&&x<240&&y> -16&&y<160;}
void portrait(int id,int x,int y){
    if(bitmap_direct){rgb_portrait(id,x,y);return;}
    const u32*h=(const u32*)original_portraits_start;unsigned i;
    const PortraitRecord*r=(const PortraitRecord*)(original_portraits_start+h[2]);
    if(portrait_count>=4||h[0]!=0x43414652)return;
    for(i=0;i<h[1];i++)if(r[i].image==id){
        pending_portraits[portrait_count++]=(PendingPortrait){r+i,x,y};return;
    }
}
static void prepare_portraits(void){
    const u32*h=(const u32*)original_portraits_start,*mixed=(const u32*)portrait_combinations_start,*combination=0;unsigned mask=0;int i,j;
    portrait_pending=portrait_upload_count=0;
    for(i=0;i<128;i++)map_oam[i][0]=0x0200;
    if(!portrait_count)return;
    for(i=0;i<portrait_count;i++)mask|=1U<<pending_portraits[i].record->sheet;
    if(mask&(mask-1)){const u16*index=(const u16*)(portrait_combinations_start+mixed[4]);unsigned at=index[mask];if(at)combination=(const u32*)(portrait_combinations_start+mixed[5])+(at-1)*(mixed[2]+1);}
    if(cached_portrait_sheet!=(int)mask){
        const u16*colors=combination?(const u16*)(portrait_combinations_start+mixed[6]+combination[0]):(const u16*)(original_portraits_start+h[3])+pending_portraits[0].record->sheet*256;
        for(i=0;i<256;i++)object_palette[i]=colors[i];object_palette_dirty=65535;
        cached_portrait_sheet=mask;
    }
    for(i=0;i<portrait_count;i++){
        PendingPortrait*p=pending_portraits+i;int slot,key=(p->record->image<<10)|mask;
        for(slot=0;slot<7&&cached_portraits[slot]!=key;slot++){}
        if(slot==7){
            for(slot=0;slot<7;slot++)if(!((portrait_visible|portrait_pending)&(1U<<slot)))break;
            if(slot==7)for(slot=0;slot<7&&(portrait_pending&(1U<<slot));slot++){}
            {const u8*packed=original_portraits_start+h[4]+p->record->tiles;
             const u8*map=combination?portrait_combinations_start+mixed[7]+combination[p->record->sheet+1]:0;unsigned at;
             if((portrait_visible&(1U<<slot))||(native_ui&&native_ui_entering&&portrait_count==1)){
              portrait_uploads[portrait_upload_count]=packed;portrait_upload_remaps[portrait_upload_count]=map;
              portrait_upload_slots[portrait_upload_count++]=slot;
             }else{
              const u8*data=image_portrait_pixels(packed);if(!data)return;
              if(map){u8*scratch=(u8*)data;for(at=0;at<2304;at++)scratch[at]=map[scratch[at]];image_decode_scratch();}
              for(at=0;at<2304;at+=256){audio_service();REG32(0x040000d4)=(u32)(data+at);REG32(0x040000d8)=0x06014000+slot*2304+at;REG32(0x040000dc)=0x84000040;}
             }
            }
            cached_portraits[slot]=key;
        }
        portrait_pending|=1U<<slot;
        for(j=0;j<9;j++){
            u16*oam=map_oam[i*9+j];
            oam[0]=((p->y+j/3*16)&255)|0x2000;
            oam[1]=((p->x+j%3*16)&511)|0x4000;
            oam[2]=512+slot*72+j*8;
        }
    }
}
static void prepare_cursor(void){
    u16*oam=map_oam[36];int i,chosen=1,best=100000;unsigned target=game_palette[5];
    oam[0]=0x0200;
    if(!cursor_visible)return;
    if(portrait_count){
        /* Find an existing face-sheet color. A cursor must never replace one
         * of the portrait's 256 original colors with its own UI color. */
        for(i=1;i<256;i++)if(i&15){unsigned c=object_palette[i];int r=(int)(c&31)-(int)(target&31),g=(int)((c>>5)&31)-(int)((target>>5)&31),b=(int)(c>>10)-(int)(target>>10),d=r*r+g*g+b*b;if(d<best){best=d;chosen=i;}}
    }else{object_palette[1]=target;object_palette_dirty|=1;cached_portrait_sheet=-1;}
    cursor_color=chosen;
    if(cursor_tile_color!=(chosen&15))cursor_tile_dirty=1;
    oam[0]=cursor_y&255;oam[1]=(cursor_x&511)|0x4000;oam[2]=1016|((chosen>>4)<<12);
}
static void upload_ui_objects(void){
    unsigned i,at,start=REG16(0x04000006),end,elapsed;
    /* Palette, textures, complete OAM list and page are committed in the same
     * blanking interval. Short DMA bursts permit the audio IRQ between them. */
    for(i=0;i<portrait_upload_count;i++){
        const u8*data=image_portrait_pixels(portrait_uploads[i]);const u8*map=portrait_upload_remaps[i];if(!data)continue;
        if(map){u8*scratch=(u8*)data;for(at=0;at<2304;at++)scratch[at]=map[scratch[at]];image_decode_scratch();}
        for(at=0;at<2304;at+=256){REG32(0x040000d4)=(u32)(data+at);REG32(0x040000d8)=0x06014000+portrait_upload_slots[i]*2304+at;REG32(0x040000dc)=0x84000040;}
    }
    if(cursor_tile_dirty){for(i=0;i<64;i++)REG16(0x06017f00+i*2)=cursor_mask[i]*(cursor_color&15);cursor_tile_color=cursor_color&15;cursor_tile_dirty=0;}
    upload_object_palette();upload_object_list();portrait_visible=portrait_pending;
    end=REG16(0x04000006);elapsed=(end+228-start)%228;
    video_commit_timing[0]=start;video_commit_timing[1]=end;
    if(elapsed>video_metrics[6])video_metrics[6]=elapsed;
    if(end<160){video_metrics[5]++;video_commit_timing[2]=start;video_commit_timing[3]=end;}
    video_metrics[7]+=portrait_upload_count*2304;
}
/* Read VCOUNT once per decision. Two reads can straddle the end of VBlank
 * around a sound IRQ and incorrectly accept a visible scanline. */
static void wait_commit_window(void){for(;;){unsigned line=REG16(0x04000006);if(line>=160&&line<=170)return;audio_service();}}
void video_overlays_present(void){
    prepare_portraits();prepare_cursor();audio_service();
    wait_commit_window();
    upload_ui_objects();
    REG16(0x04000000)=(REG16(0x04000000)&~0x1000)|((portrait_count||cursor_visible)?0x1000:0);
    video_metrics[4]++;ui_ready=1;
}
/* Mode 0 background cache: 32 columns x 30 rows of 8bpp tiles (60 KiB).
 * The 32x64 screen map points into this ring. Scrolling changes HOFS/VOFS;
 * only newly exposed edge tiles are uploaded, never a scrolled framebuffer.
 * Mode 4 dialogue/menu flips invalidate VRAM ownership explicitly. */
int video_map_active(void){return map_active;}
void *video_map_scratch(void){return framebuffer;}
void video_map_cache_reset(void){memset(map_resident,0,sizeof(map_resident));}
int video_map_reuse(int x,int y,int width,int height,int camera_x,int camera_y){
 int xx,yy,all=1;if(!map_active)return 0;
 for(yy=y;yy<y+height;yy+=8)for(xx=x;xx<x+width;xx+=8){int tx=(xx+camera_x)/8,ty=(yy+camera_y)/8,row=ty%MAP_CACHE_ROWS,col=tx&31;
  if(map_row_owner[row]!=ty||map_column_owner[col]!=tx||!(map_resident[row]&(1U<<col)))all=0;
  else{
   /* The 64-row screen map and 30-row pixel ring wrap independently. A
    * resident tile still needs its screen-map entry restored after a wrap. */
   REG16(0x0600f000+(((ty&31)*32+col)*2))=row*32+col;
   map_video_metrics[7]++;
  }
 }
 if(all)map_video_metrics[3]++;return all;
}
void video_map_upload(int x,int y,int width,int height,int camera_x,int camera_y){
 int xx,yy,row;
 for(yy=y;yy<y+height;yy+=8)for(xx=x;xx<x+width;xx+=8){
  int tx=(xx+camera_x)/8,ty=(yy+camera_y)/8,ring_row=ty%MAP_CACHE_ROWS,col=tx&31,slot=ring_row*32+col,i;
  if(map_row_owner[ring_row]!=ty){map_row_owner[ring_row]=ty;map_resident[ring_row]=0;}
  if(map_column_owner[col]!=tx){map_column_owner[col]=tx;for(i=0;i<MAP_CACHE_ROWS;i++)map_resident[i]&=~(1U<<col);}
  volatile u16*dst=(volatile u16*)(0x06000000+slot*64);
  for(row=0;row<8;row++){const u16*src=framebuffer+(yy+row)*120+xx/2;int k;for(k=0;k<4;k++)*dst++=src[k];}
  REG16(0x0600f000+(((ty&31)*32+(tx&31))*2))=slot;
  map_resident[ring_row]|=1U<<col;
  map_video_metrics[0]++;map_video_metrics[1]+=64;
 }
}
static void map_obj(int id,int x,int y,int size,int tile){
 map_oam[id][0]=(y&255)|0x2000;map_oam[id][1]=(x&511)|(size<<14);map_oam[id][2]=tile;
}
static void map_hint_tiles(void){map_hints_pending=1;}

void video_map_objects_begin(void){
 int i;hud_pending_uploads=0;actor_deferred_uploads=0;object_palette_overflow=0;map_actor_count=map_point_count=hud_count=0;cursor_visible=0;portrait_count=0;
 actor_pending[0]=actor_pending[1]=0;
 for(i=0;i<128;i++)map_oam[i][0]=0x0200;
 if(!map_active||!map_objects_valid){
  for(i=0;i<256;i++)object_palette[i]=game_palette[i];object_palette_dirty=65535;
  for(i=0;i<24;i++)actor_cache[i]=-1;
  memset(object_color_cache,0,2048);object_color_count=16;
  actor_visible[0]=actor_visible[1]=0;
  hud_cache[0]=hud_cache[1]=-1;
  for(i=0;i<7;i++)cached_portraits[i]=-1;cached_portrait_sheet=-1;portrait_visible=0;
  map_hint_tiles();
  map_objects_valid=1;
 }
}
void video_map_scene_reset(void){map_objects_valid=0;}
int video_map_objects_retry(void){
 int i;if(!object_palette_overflow)return 0;
 /* Reclaim colors belonging only to actors that left this map view. Keep
  * the old displayed texture slots intact; the second pass uses free slots
  * and commits its new palette/OAM together in the next blanking interval. */
 for(i=0;i<256;i++)object_palette[i]=game_palette[i];object_palette_dirty=65535;
 for(i=0;i<24;i++)actor_cache[i]=-1;hud_cache[0]=hud_cache[1]=-1;
 memset(object_color_cache,0,2048);object_color_count=16;object_palette_overflow=0;object_palette_rebuilds++;return 1;
}
static unsigned __attribute__((section(".iwram"),long_call,noinline)) object_color(unsigned color){
 unsigned first=(color*2654435761U)>>23,at=first,i,index;u32 key;
 /* This is a disposable lookup cache. A full 512-slot probe for every new
  * color made crowded scenes quadratic after more than 512 source colors.
  * Bounded probing only changes hit rate; misses still find the exact same
  * palette index or nearest color below. */
 for(i=0;i<16;i++,at=(at+1)&511){key=object_color_cache[at];if(!key)break;if((key&32767)==color)return(key>>16)&255;}
 if(i==16)at=first;
 for(index=1;index<(unsigned)object_color_count&&object_palette[index]!=color;index++){}
 if(index==(unsigned)object_color_count){
  if(object_color_count<256){object_palette[index]=color;object_color_count++;object_palette_dirty|=1U<<(index>>4);}
  else{int best=100000;unsigned c;index=1;object_palette_overflow=1;map_video_metrics[5]++;for(c=1;c<256;c++){unsigned old=object_palette[c];int r=(int)(old&31)-(int)(color&31),g=(int)((old>>5)&31)-(int)((color>>5)&31),b=(int)(old>>10)-(int)(color>>10),d=r*r+g*g+b*b;if(d<best){best=d;index=c;}}}
 }
 map_video_metrics[6]=object_color_count;
 object_color_cache[at]=0x80000000U|(index<<16)|color;return index;
}
static void map_inverse(int image){int i,count=images[image].color_count?images[image].color_count:16;image_line[768]=0;for(i=1;i<count;i++){if(!(i&15))audio_service();image_line[768+i]=object_color(images[image].colors?images[image].colors[i]:game_palette[images[image].palette[i]]);}}
static const CharacterRecord*character_record(int image,int index){
 const u32*h=(const u32*)original_characters_start;const CharacterRecord*r=(const CharacterRecord*)(original_characters_start+h[2]);int lo=0,hi=h[1],key=image*8+index;
 if(h[0]!=0x4a424f52||index<0||index>7)return 0;
 while(lo<hi){int mid=(lo+hi)/2;if(r[mid].image*8+r[mid].index<key)lo=mid+1;else hi=mid;}
 return lo<(int)h[1]&&r[lo].image==image&&r[lo].index==index?r+lo:0;
}
void video_map_actor(int image,int index,int direction,int x,int y){
 int slot,d=direction==8?0:direction==6?1:direction==2?2:3,key=image*128+index*4+d;const CharacterRecord*record;
 if(image<0||map_actor_count>=48||x<=-32||y<=-32||x>=240||y>=160)return;
 record=character_record(image,index);if(!record)return;
 /* Texture slots belong to graphics, not their order in the visible list.
  * An actor leaving the screen must not force every later actor to decode
  * again, or overwrite textures still used by the displayed object list. */
 for(slot=0;slot<24&&actor_cache[slot]!=key;slot++){}
 if(slot==24){
  for(slot=0;slot<24;slot++)if(!((actor_visible[slot>>5]|actor_pending[slot>>5])&(1U<<(slot&31))))break;
  if(slot==24)for(slot=0;slot<24;slot++)if(!(actor_pending[slot>>5]&(1U<<(slot&31))))break;
  if(slot==24)return;
 }
 if(actor_cache[slot]!=key){const u32*h=(const u32*)original_characters_start;const u16*colors=(const u16*)(original_characters_start+h[3]+record->palette);const u8*data=original_characters_start+h[4]+record->tiles+(d*3+1)*1024;int i,count=record->color_count?record->color_count:256,defer=!!(actor_visible[slot>>5]&(1U<<(slot&31)));u8*dst=(u8*)framebuffer+(defer?4096+slot*1024:0);
  (void)count;memset(image_line+768,0,256);
  /* Reserve colors used by this visible pose, not all twelve poses in the
   * original character. Zero remains the transparent sentinel. */
  for(i=0;i<1024;i++){unsigned c;if(!(i&31))audio_service();c=data[i];if(c&&!image_line[768+c])image_line[768+c]=object_color(colors[c]);dst[i]=image_line[768+c];}
  if(defer)actor_deferred_uploads|=1U<<slot;
  else{REG32(0x040000d4)=(u32)framebuffer;REG32(0x040000d8)=0x06010000+slot*1024;REG32(0x040000dc)=0x84000100;}
  actor_cache[slot]=key;map_video_metrics[4]++;
 }
 actor_pending[slot>>5]|=1U<<(slot&31);
 map_oam[map_actor_count+1][0]=(y&255)|0x2000;map_oam[map_actor_count+1][1]=(x&511)|0x8000;map_oam[map_actor_count+1][2]=slot*32;
 map_actor_count++;
}
void video_map_point(int x,int y,int selected,int reachable){
 if(x< -7||x>=240||y< -7||y>=160)return;
 if(map_point_count<71)map_obj(49+map_point_count++,x,y,0,reachable?784:788);
 if(selected){
  map_obj(120,x-4,y-4,1,808+((map_blink>>4)&1)*8);
  map_oam[0][0]=(clamp(y-19,0,144)&255)|0x6000;map_oam[0][1]=(clamp(x-12,0,208)&511)|0x8000;map_oam[0][2]=976+(reachable?0:16);
 }
}
void video_map_player(int x,int y){if(x> -8&&x<240&&y> -8&&y<160)map_obj(121,x,y,0,786);}
void video_map_hud(int image,int x,int y){
 int slot=hud_count,row,col;const Image*im=images+image;
 if(slot>=2||im->width>64||im->height>32)return;
 if(hud_cache[slot]!=image){
  map_inverse(image);
  for(row=0;row<32;row++){
   audio_service();
   if(row<im->height&&!decode_image_row(im,row,image_line,768))return;
   for(col=0;col<64;col+=2){int tile=(row/8)*8+col/8,at=(row%8)*8+col%8,k;u16 value=0;
    if(row<im->height)for(k=0;k<2&&col+k<im->width;k++)value|=image_line[768+image_line[col+k]]<<(k*8);
    ((u16*)framebuffer)[slot*1024+(tile*64+at)/2]=value;
   }
  }hud_cache[slot]=image;hud_pending_uploads|=1U<<slot;
 }
 map_oam[122+slot][0]=(y&255)|0x6000;map_oam[122+slot][1]=(x&511)|0xc000;map_oam[122+slot][2]=848+slot*64;
 hud_count++;
}
static unsigned __attribute__((section(".iwram"),long_call,noinline)) upload_native_textures(void){
 unsigned count=0;int d;
 if(map_hints_pending){
  const u32*source[3]={balanced_hint_directions,balanced_hint_selection,balanced_hint_labels};
  const unsigned destination[3]={0x06016000,0x06016500,0x06017a00},length[3]={176,128,256};
  for(d=0;d<3;d++){unsigned at;for(at=0;at<length[d];at+=64){unsigned words=length[d]-at;if(words>64)words=64;REG32(0x040000d4)=(u32)(source[d]+at);REG32(0x040000d8)=destination[d]+at*4;REG32(0x040000dc)=0x84000000|words;}}
  map_hints_pending=0;
 }
 for(d=0;d<24;d++)if(actor_deferred_uploads&(1U<<d)){unsigned at;count++;for(at=0;at<1024;at+=256){REG32(0x040000d4)=(u32)framebuffer+4096+d*1024+at;REG32(0x040000d8)=0x06010000+d*1024+at;REG32(0x040000dc)=0x84000040;}}
 for(d=0;d<2;d++)if(hud_pending_uploads&(1U<<d)){unsigned at;for(at=0;at<2048;at+=256){REG32(0x040000d4)=(u32)framebuffer+d*2048+at;REG32(0x040000d8)=0x06016a00+d*2048+at;REG32(0x040000dc)=0x84000040;}}
 actor_deferred_uploads=0;hud_pending_uploads=0;return count;
}
void video_map_present(int camera_x,int camera_y,int directions){
 static const short xy[4][2]={{116,2},{230,76},{116,150},{2,76}};int d;unsigned start,end,elapsed,texture_count;
 for(d=0;d<4;d++)map_obj(124+d,xy[d][0],xy[d][1],0,768+d*4+((directions&(1<<d))?0:2));
 /* Commit camera and complete object list together between visible frames.
  * Do not tick events here: preparing a view must not advance game rules. */
 audio_service();wait_commit_window();start=REG16(0x04000006);
 texture_count=upload_native_textures();video_native_texture_metrics[0]+=texture_count;if(texture_count>video_native_texture_metrics[1])video_native_texture_metrics[1]=texture_count;
 upload_background_palette();
 /* Actor/HUD remaps were prepared while old objects stayed visible. The
  * idle CPU framebuffer owns these two HUD staging tiles until this commit. */
 upload_object_palette();upload_object_list();
 actor_visible[0]=actor_pending[0];actor_visible[1]=actor_pending[1];
 REG16(0x04000008)=0x1e83;/* BG0, 8bpp, 32x32 map, screen block 30. */
 map_camera_x=camera_x&255;map_camera_y=camera_y&255;
 REG16(0x04000010)=map_camera_x;REG16(0x04000012)=map_camera_y;
 REG16(0x04000000)=0x1140;map_active=1;native_ui_map=game.map;map_video_metrics[2]++;ui_ready=1;
 end=REG16(0x04000006);elapsed=(end+228-start)%228;if(end<160)video_native_commit_metrics[0]++;if(elapsed>video_native_commit_metrics[1])video_native_commit_metrics[1]=elapsed;video_native_commit_metrics[2]++;
}
static void pixel(int x,int y,int c){if(bitmap_direct){rgb_pixel(x,y,game_palette[c]);return;}if(x>=clip_left&&x<clip_right&&y>=clip_top&&y<clip_bottom){if(native_ui){u32*dst=(u32*)framebuffer+y*30+x/8;unsigned shift=x%8*4;*dst=(*dst&~(15U<<shift))|((c&15U)<<shift);native_ui_damage(x,y,1,1);}else((u8*)framebuffer)[y*240+x]=c;}}
void box(int x,int y,int w,int h,int c){if(bitmap_direct){rgb_box(x,y,w,h,c);return;}int j,x1=clamp(x,clip_left,clip_right),x2=clamp(x+w,clip_left,clip_right),y1=clamp(y,clip_top,clip_bottom),y2=clamp(y+h,clip_top,clip_bottom);if(x2<=x1||y2<=y1)return;framebuffer_revision++;if(native_ui){native_ui_fill(x1,y1,x2,y2,c);return;}for(j=y1;j<y2;j++)memset((u8*)framebuffer+j*240+x1,c,x2-x1);}
void rect(int x,int y,int w,int h,int c){box(x,y,w,1,c);box(x,y+h-1,w,1,c);box(x,y,1,h,c);box(x+w-1,y,1,h,c);}
void picture(int id,int x,int y,int sx,int sy,int w,int h,int transparent){
    if(bitmap_direct){rgb_picture(id,x,y,sx,sy,w,h,w,h,transparent,0,0);return;}
    const Image *im=images+id;const u8*colors=image_color_map(im);int i,j,left=0,right=w,top=0,bottom=h;
    if(x<clip_left)left=clip_left-x;if(sx<0&&left<-sx)left=-sx;if(y<clip_top)top=clip_top-y;if(sy<0&&top<-sy)top=-sy;
    if(x+right>clip_right)right=clip_right-x;if(sx+right>im->width)right=im->width-sx;if(y+bottom>clip_bottom)bottom=clip_bottom-y;if(sy+bottom>im->height)bottom=im->height-sy;
    if(right<=left||bottom<=top)return;framebuffer_revision++;
    for(j=top;j<bottom;j++){if(!(j&7))audio_service();if(!decode_image_row(im,sy+j,image_line,sizeof(image_line)))return;for(i=left;i<right;i++){int c=image_line[sx+i];if(c||!transparent)pixel(x+i,y+j,colors[c]);}}
}
void picture_scaled(int id,int x,int y,int w,int h){const Image*im=images+id;picture_region_scaled(id,x,y,0,0,im->width,im->height,w,h,0,0,0);}
void picture_region_scaled(int id,int x,int y,int sx,int sy,int sw,int sh,int w,int h,int transparent,int opacity,const u8*tone){
 if(bitmap_direct){rgb_picture(id,x,y,sx,sy,sw,sh,w,h,transparent,opacity,tone);return;}
 const Image*im=images+id;static u8 adjusted[256],old_tone[4];static u16 toned_colors[256];static const u16*old_colors;static const ScenePalette*old_scene;static int tone_ready;const u8*colors;const u8*blend_rows[16];int blend_ready=0,i,j,tinted=tone&&(tone[0]!=100||tone[1]!=100||tone[2]!=100||tone[3]!=100);
 if(w<=0||h<=0||sw<=0||sh<=0||opacity>=100||x>=clip_right||y>=clip_bottom||x+w<=clip_left||y+h<=clip_top)return;
 if(transparent&&(im->transparent&128))return;
 colors=image_color_map(im);
 framebuffer_revision++;
 video_metrics[0]++;
 audio_service();
 /* Native map tiles need neither coordinate division nor a scaled span.
  * Keep the established reduced-size path for adapted non-map interfaces. */
 if((im->encoding==0||im->encoding==3)&&im->width==8&&im->height==8&&sx==0&&sy==0&&sw==8&&sh==8&&w==8&&h==8&&!opacity&&!tinted){
  int first=x<clip_left?clip_left-x:0,last=x+8>clip_right?clip_right-x:8;
  for(j=0;j<8;j++){int yy=y+j;if(yy<clip_top||yy>=clip_bottom)continue;
   for(i=first;i<last;i++){int at=j*8+i,c=im->encoding==3?im->palette[(im->pixels[at/2]>>(at&1?0:4))&15]:im->pixels[at];
    if(c||!transparent)((u8*)framebuffer)[yy*240+x+i]=colors[c];
   }
  }return;
 }
 if(!transparent&&!opacity&&!tinted&&w==sw&&h==sh&&(!im->stored_width||(im->stored_width==im->width&&im->stored_height==im->height))){
  int left=x<clip_left?clip_left-x:0,right=x+w>clip_right?clip_right-x:w;
  int top=y<clip_top?clip_top-y:0,bottom=y+h>clip_bottom?clip_bottom-y:h;
  if(sx+left<0)left=-sx;if(sx+right>im->width)right=im->width-sx;
  if(sy+top<0)top=-sy;if(sy+bottom>im->height)bottom=im->height-sy;
  if(right<=left||bottom<=top)return;
  video_metrics[1]+=(right-left)*(bottom-top);
  if(im->encoding==6&&!(((x+left)|(y+top)|(sx+left)|(sy+top)|(right-left)|(bottom-top))&7)){
   int tx,ty,rr,cc,direct=drawing_scene&&im->colors==drawing_scene->colors;native_whole_tile_metrics[0]++;
   for(ty=top;ty<bottom;ty+=8)for(tx=left;tx<right;tx+=8){const u8*tile;
    if(!((tx-left)&63))audio_service();tile=image_storage_tile(im,(sx+tx)/8,(sy+ty)/8);if(!tile)return;
    for(rr=0;rr<8;rr++){u8*dst=(u8*)framebuffer+(y+ty+rr)*240+x+tx;const u8*src=tile+rr*8;
     if(direct)memcpy(dst,src,8);else for(cc=0;cc<8;cc++)dst[cc]=colors[src[cc]];
    }native_whole_tile_metrics[1]++;
   }return;
  }
  for(j=top;j<bottom;j++){
   if(!(j&7))audio_service();
   if(!decode_image_storage_span(im,sy+j,sx+left,right-left,image_line,sizeof(image_line)))return;
   {u8*dst=(u8*)framebuffer+(y+j)*240+x+left;
    if(drawing_scene&&im->colors==drawing_scene->colors)memcpy(dst,image_line,right-left);
    else for(i=0;i<right-left;i++)dst[i]=colors[image_line[i]];
   }
  }return;
 }
 if((im->encoding==0||im->encoding==3)&&im->width==8&&im->height==8&&sx==0&&sy==0&&sw==8&&sh==8&&w==6&&(h==5||h==6)&&!opacity&&!tinted){
  static const u8 six[6]={0,1,2,4,5,6},five[5]={0,1,3,4,6};int first=x<clip_left?clip_left-x:0,last=x+6>clip_right?clip_right-x:6;
  for(j=0;j<h;j++){int yy=y+j,src=(h==5?five[j]:six[j])*8;if(yy<clip_top||yy>=clip_bottom)continue;for(i=first;i<last;i++){int at=src+six[i],c=im->encoding==3?im->palette[(im->pixels[at/2]>>(at&1?0:4))&15]:im->pixels[at];if(c||!transparent)((u8*)framebuffer)[yy*240+x+i]=colors[c];}}return;
 }

 if(tinted&&(!tone_ready||old_colors!=im->colors||old_scene!=drawing_scene||old_tone[0]!=tone[0]||old_tone[1]!=tone[1]||old_tone[2]!=tone[2]||old_tone[3]!=tone[3])){int count=im->color_count?im->color_count:im->colors&&im->encoding>=1&&im->encoding<=4?16:256;for(i=0;i<count;i++){unsigned color=im->colors?im->colors[i]:game_palette[i];int r=color&31,g=color>>5&31,b=color>>10&31,gray=(r*30+g*59+b*11)/100;
   if(!(i&7))audio_service();
   r=clamp((gray+(r-gray)*tone[3]/100)*tone[0]/100,0,31);g=clamp((gray+(g-gray)*tone[3]/100)*tone[1]/100,0,31);b=clamp((gray+(b-gray)*tone[3]/100)*tone[2]/100,0,31);
   toned_colors[i]=r|(g<<5)|(b<<10);adjusted[i]=background_nearest(toned_colors[i],1);
  }for(i=0;i<4;i++)old_tone[i]=tone[i];tone_ready=1;old_colors=im->colors;old_scene=drawing_scene;}
 if(opacity)blend_ready=prepare_blend_rows(im,tinted?toned_colors:0,opacity*32/100,blend_rows);
 /* Uniform full-screen masks contain no spatial information to decode or
  * scale. This is the original source color, including palette index zero
  * when RPG Maker's transparency switch is off. */
 if((im->color_count==1||im->encoding==7)&&sx>=0&&sy>=0&&sx+sw<=im->width&&sy+sh<=im->height){
  unsigned c=im->encoding==7?im->pixels[0]:0;
  int left=clamp(x,clip_left,clip_right),right=clamp(x+w,clip_left,clip_right),top=clamp(y,clip_top,clip_bottom),bottom=clamp(y+h,clip_top,clip_bottom);
  if(transparent&&!c)return;
  if(!opacity)box(left,top,right-left,bottom-top,tinted?adjusted[c]:colors[c]);
  else if(blend_ready)for(j=top;j<bottom;j++){u8*dst=(u8*)framebuffer+j*240+left;if(!(j&7))audio_service();for(i=left;i<right;i++,dst++)*dst=blend_rows[c][*dst];}
  else goto general_scaled_image;
  return;
 }
 if(w==sw&&h==sh&&(!im->stored_width||(im->stored_width==im->width&&im->stored_height==im->height))){
  int first=x<clip_left?clip_left-x:0,last=x+w>clip_right?clip_right-x:w,top=y<clip_top?clip_top-y:0,bottom=y+h>clip_bottom?clip_bottom-y:h,alpha=opacity*32/100;const u16*bg=background_colors();
  if(sx+first<0)first=-sx;if(sx+last>im->width)last=im->width-sx;if(sy+top<0)top=-sy;if(sy+bottom>im->height)bottom=im->height-sy;
  if(first>=last||top>=bottom)return;
  for(j=top;j<bottom;j++){u8*dst=(u8*)framebuffer+(y+j)*240+x+first;if(!(j&7))audio_service();if(!decode_image_storage_span(im,sy+j,sx+first,last-first,image_line,sizeof(image_line)))return;
   for(i=0;i<last-first;i++){unsigned c=image_line[i];if(transparent&&!c)continue;
    if(blend_ready)dst[i]=blend_rows[c][dst[i]];
    else if(opacity){unsigned src=tinted?toned_colors[c]:im->colors?im->colors[c]:game_palette[c],old=bg[dst[i]],rb=(((src&0x7c1f)*(32-alpha)+(old&0x7c1f)*alpha)>>5)&0x7c1f,green=(((src&0x03e0)*(32-alpha)+(old&0x03e0)*alpha)>>5)&0x03e0;dst[i]=background_nearest(rb|green,0);}
    else dst[i]=tinted?adjusted[c]:colors[c];
   }
  }return;
 }
general_scaled_image:;
 /* Clip once and fuse virtual-to-stored sampling with final screen sampling.
  * These two integer floors match the old two-stage nearest-neighbour result;
  * only decoded source rows and final visible pixels are visited. */
 static u16 columns[240];
 int first=x<clip_left?clip_left-x:0,last=x+w>clip_right?clip_right-x:w;
 int top=y<clip_top?clip_top-y:0,bottom=y+h>clip_bottom?clip_bottom-y:h;
 int stored_width=im->stored_width?im->stored_width:im->width;
 int stored_height=im->stored_height?im->stored_height:im->height;
 int previous_row=-1,span_left=stored_width,span_right=-1,alpha=opacity*32/100;
 if(first>=last||top>=bottom)return;
 video_metrics[1]+=(last-first)*(bottom-top);
 for(i=first;i<last;i++){
  int xx=sx+i*sw/w;
  columns[i-first]=(xx<0||xx>=im->width)?65535:(u32)xx*stored_width/im->width;
  if(columns[i-first]!=65535){int column=columns[i-first];if(column<span_left)span_left=column;if(column>span_right)span_right=column;}
 }
 if(span_right<span_left)return;
 for(j=top;j<bottom;j++){
  int yy=sy+j*sh/h,physical;
  u8*destination=(u8*)framebuffer+(y+j)*240+x+first;
  if(!(j&7))audio_service();
  if(yy<0||yy>=im->height)continue;
  physical=(u32)yy*stored_height/im->height;
  if(physical!=previous_row){video_metrics[2]++;video_metrics[3]+=span_right-span_left+1;if(!decode_image_storage_span(im,physical,span_left,span_right-span_left+1,image_line,sizeof(image_line)))return;previous_row=physical;}
  if(!transparent&&!opacity&&!tinted){for(i=0;i<last-first;i++)if(columns[i]!=65535)destination[i]=colors[image_line[columns[i]-span_left]];}
  else for(i=0;i<last-first;i++){
   int c;if(columns[i]==65535)continue;c=image_line[columns[i]-span_left];
   if(transparent&&!c)continue;
   if(blend_ready){destination[i]=blend_rows[c][destination[i]];continue;}
   if(opacity){
    /* Uniform palette alpha. A diagonal discard mask is visibly patterned
     * even after an animation ends, so it must not stand in for translucency.
     * Packed red/blue lanes stay separate with 0..32 coefficients. */
    const u16*bg=background_colors();unsigned src=tinted?toned_colors[c]:im->colors?im->colors[c]:game_palette[c],dst=bg[destination[i]];
    unsigned rb=(((src&0x7c1f)*(32-alpha)+(dst&0x7c1f)*alpha)>>5)&0x7c1f;
    unsigned green=(((src&0x03e0)*(32-alpha)+(dst&0x03e0)*alpha)>>5)&0x03e0;
    c=background_nearest(rb|green,0);
   }else c=tinted?adjusted[c]:colors[c];
   destination[i]=c;
  }
 }

}
static void __attribute__((section(".iwram"),long_call,noinline)) glyph_pixels(int x,int y,const u16*rows,int color){
    int left=clamp(x,clip_left,clip_right),right=clamp(x+12,clip_left,clip_right),top=clamp(y,clip_top,clip_bottom),bottom=clamp(y+12,clip_top,clip_bottom),xx,yy;
    if(left>=right||top>=bottom)return;
    if(native_ui){native_ui_glyph(x,y,rows,color,left,top,right,bottom);return;}
    if(bitmap_direct){u16 c=game_palette[color];rgb_damage(left,top,right-left,bottom-top);
        for(yy=top;yy<bottom;yy++){unsigned bits=rows[yy-y];u16*dst=framebuffer+yy*240+left;for(xx=left;xx<right;xx++,dst++)if(bits&(1U<<(11-(xx-x))))*dst=c;}
    }else{
        for(yy=top;yy<bottom;yy++){unsigned bits=rows[yy-y];u8*dst=(u8*)framebuffer+yy*240+left;for(xx=left;xx<right;xx++,dst++)if(bits&(1U<<(11-(xx-x))))*dst=color;}
    }
}
static void glyph(int x,int y,unsigned code,int color){
    int lo=0,hi=GLYPH_COUNT-1,mid;
    if(code>=0x10000&&code<0x10034){glyph_pixels(x,y,exfont_rows[code-0x10000],color);return;}
    while(lo<=hi){mid=(lo+hi)/2;if(glyph_codes[mid]<code)lo=mid+1;else if(glyph_codes[mid]>code)hi=mid-1;else{
        glyph_pixels(x,y,glyph_rows[mid],color);return;
    }}
    rect(x+1,y+1,9,10,color);
}
int draw_text(int x,int y,const char *s,int color,int width){
    int start=x;const u8*p=(const u8*)s;
    framebuffer_revision++;
    while(*p){unsigned c=*p++;int w=c<128?6:12;if(c>=128&&*p)c=(c<<8)|*p++;
        else if(c=='$'&&((*p>='A'&&*p<='Z')||(*p>='a'&&*p<='z'))){c=0x10000+(*p<='Z'?*p-'A':*p-'a'+26);p++;w=12;}
        if(c=='\n'){x=start;y+=14;continue;}if(x-start+w>width)break;
        glyph(x,y,c,color);x+=w;
    }return x;
}
void draw_num(int x,int y,int n,int color){char b[16];unsigned a=n<0?-(unsigned)n:(unsigned)n;int k=15;b[k]=0;do{b[--k]='0'+a%10;a/=10;}while(a);if(n<0)b[--k]='-';draw_text(x,y,b+k,color,200);}
void flip(void){
    if(native_ui){native_ui_flip();return;}
    if(bitmap_direct){rgb_flip();return;}
    /* A full-frame DMA blocks the ARM7 and its sound refill interrupt longer
     * than the FIFO can cover. Permit IRQ service between bounded transfers;
     * timer-driven redraws must not drop part of the original music. */
    unsigned done=0;int transition=map_active,shade=current_brightness;u32 destination=page?0x0600a000:0x06000000;
    if(map_active){int i;video_brightness(-16);map_active=0;for(i=0;i<128;i++)REG16(0x07000000+i*8)=0x0200;}
    while(done<9600){unsigned words=9600-done;if(!(done&1023))audio_service();if(words>64)words=64;REG32(0x040000d4)=(u32)framebuffer+done*4;REG32(0x040000d8)=destination+done*4;REG32(0x040000dc)=0x84000000|words;done+=words;}
    prepare_portraits();prepare_cursor();audio_service();
    wait_commit_window();
    upload_background_palette();
    upload_ui_objects();
    REG16(0x04000000)=0x0444|((portrait_count||cursor_visible)?0x1000:0)|(page?0x10:0);page^=1;
    if(transition)video_brightness(shade);
    ui_ready=1;
}

#include "rgb_surface.inc"
#include "native_ui.inc"
