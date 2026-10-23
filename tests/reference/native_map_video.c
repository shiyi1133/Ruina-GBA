#include "gba_hw.h"
#include "types.h"
#include "assets.h"
#include "audio.h"
extern void engine_tick(void);
static u16 framebuffer[240*160/2] __attribute__((aligned(4)));
static int clip_left,clip_top,clip_right=240,clip_bottom=160;
static unsigned framebuffer_revision;
static int page;
typedef struct {u16 image,sheet;u32 tiles;} PortraitRecord;
typedef struct {const PortraitRecord*record;short x,y;} PendingPortrait;
extern const u8 original_portraits_start[];
extern const u8 palette_rgb555_start[];
static PendingPortrait pending_portraits[4];
static int portrait_count,cached_portraits[4],cached_portrait_sheet=-1;
static int cursor_x,cursor_y,cursor_visible;
static int map_active,map_actor_count,map_point_count,map_blink;
static int actor_cache[48];
static int hud_count,hud_cache[2],actor_banks[9];
volatile u32 map_video_metrics[8];
static u8 image_line[1024];
static unsigned old_keys, repeats;
volatile unsigned input_latched,input_sampled;
volatile unsigned input_triggered,input_frame_keys;
volatile unsigned ui_ready;
volatile u32 video_metrics[8];
unsigned video_ticks(void){return REG16(0x04000108);}
unsigned video_revision(void){return framebuffer_revision;}
void video_clip(int x,int y,int width,int height){
    clip_left=clamp(x,0,240);clip_top=clamp(y,0,160);
    clip_right=clamp(x+width,clip_left,240);clip_bottom=clamp(y+height,clip_top,160);
}
void *memcpy(void *d,const void *s,unsigned int n) { u8 *a=d; const u8*b=s;if((((unsigned)a|(unsigned)b)&3)==0){while(n>=4){*(u32*)a=*(const u32*)b;a+=4;b+=4;n-=4;}}while(n--)*a++=*b++;return d; }
void *memset(void *d,int v,unsigned int n) { u8 *a=d;u32 word=(v&255)*0x01010101U;while(n&&((unsigned)a&3)){*a++=v;n--;}while(n>=4){*(u32*)a=word;a+=4;n-=4;}while(n--)*a++=v;return d; }
int clamp(int n,int lo,int hi) {return n<lo?lo:n>hi?hi:n;}
void video_init(void) {
    volatile u16 *p=(volatile u16*)0x05000000;int i;
    for(i=0;i<256;i++)p[i]=game_palette[i];
    /* Standard cartridge 3/1 ROM timing and instruction prefetch; SRAM timing
     * stays at its default four cycles. */
    REG16(0x04000204)=0x4014;REG16(0x04000000)=0x0404;
    for(i=0;i<128;i++)REG16(0x07000000+i*8)=0x0200;
    for(i=0;i<4;i++)cached_portraits[i]=-1;
    /* A separate 16x16, 4-bit OBJ. Its tile is beyond all four portrait
     * slots, so moving the cursor never rewrites background bitmap pixels. */
    for(i=0;i<64;i++){
        int tile=i/16,row=(i%16)/2,half=i&1,k;u16 packed=0;
        for(k=0;k<4;k++){int x=tile%2*8+half*4+k,y=tile/2*8+row;
            if(x<14&&y<13&&(!x||x==13||!y||y==12))packed|=1U<<(k*4);
        }REG16(0x06016400+i*2)=packed;
    }
    video_brightness(0);
}
void video_brightness(int level){
    level=clamp(level,-16,16);
    REG16(0x04000050)=level?(level>0?0x00b5:0x00f5):0;
    REG16(0x04000054)=level<0?-level:level;
}
int face_image(LcfSpan name,int index){u32 h=2166136261U;unsigned i;for(i=0;i<name.size;i++){h^=name.data[i];h*=16777619U;}if(index<0||index>=16)return -1;for(i=0;i<FACE_SHEET_COUNT;i++)if(face_name_hashes[i]==h)return face_image_ids[i][index];return -1;}
int story_image(LcfSpan name){u32 h=2166136261U;unsigned i;for(i=0;i<name.size;i++){h^=name.data[i];h*=16777619U;}for(i=0;i<STORY_IMAGE_COUNT;i++)if(story_name_hashes[i]==h)return story_image_ids[i];return -1;}
unsigned wait_frame(void) {
    unsigned keys,result,ime;
    while(REG16(0x04000006)>=160){audio_service();}
    while(REG16(0x04000006)<160){audio_service();}
    ime=REG16(0x04000208);REG16(0x04000208)=0;
    keys=(~REG16(0x04000130))&1023;result=input_latched|(keys&~input_sampled);input_latched=0;input_sampled=keys;REG16(0x04000208)=ime;
    if(keys==old_keys&&keys) {repeats++;if(repeats>24&&repeats%6==0)result|=keys&(KEY_UP|KEY_DOWN|KEY_LEFT|KEY_RIGHT);}
    else repeats=0;
    old_keys=keys;input_frame_keys=keys|result;input_triggered=result;ui_ready=0;engine_tick();
    if(map_active){map_blink++;REG16(0x07000000+120*8+4)=808+((map_blink>>4)&1)*8;}
    ui_ready=1;return result;
}
void clear(int c){ui_ready=0;portrait_count=0;cursor_visible=0;framebuffer_revision++;if(!clip_left&&!clip_top&&clip_right==240&&clip_bottom==160)memset(framebuffer,c,sizeof(framebuffer));else box(clip_left,clip_top,clip_right-clip_left,clip_bottom-clip_top,c);}
void video_map_cursor(int x,int y,int visible){cursor_x=x;cursor_y=y;cursor_visible=visible&&x> -16&&x<240&&y> -16&&y<160;}
void portrait(int id,int x,int y){
    const u32*h=(const u32*)original_portraits_start;unsigned i;
    const PortraitRecord*r=(const PortraitRecord*)(original_portraits_start+h[2]);
    if(portrait_count>=4||h[0]!=0x43414652)return;
    for(i=0;i<h[1];i++)if(r[i].image==id){
        pending_portraits[portrait_count++]=(PendingPortrait){r+i,x,y};return;
    }
}
static void upload_portraits(void){
    const u32*h=(const u32*)original_portraits_start;int i,j;
    for(i=0;i<36;i++)REG16(0x07000000+i*8)=0x0200;
    if(!portrait_count)return;
    if(cached_portrait_sheet!=pending_portraits[0].record->sheet){
        const u16*colors=(const u16*)(original_portraits_start+h[3])+pending_portraits[0].record->sheet*256;
        for(i=0;i<256;i++)REG16(0x05000200+i*2)=colors[i];
        cached_portrait_sheet=pending_portraits[0].record->sheet;
    }
    for(i=0;i<portrait_count;i++){
        PendingPortrait*p=pending_portraits+i;
        if(cached_portraits[i]!=p->record->image){
            unsigned at;const u8*data=original_portraits_start+h[4]+p->record->tiles;
            for(at=0;at<2304;at+=256){
                audio_service();REG32(0x040000d4)=(u32)(data+at);
                REG32(0x040000d8)=0x06014000+i*2304+at;REG32(0x040000dc)=0x84000040;
            }
            cached_portraits[i]=p->record->image;
        }
        for(j=0;j<9;j++){
            unsigned oam=0x07000000+(i*9+j)*8;
            REG16(oam)=((p->y+j/3*16)&255)|0x2000;
            REG16(oam+2)=((p->x+j%3*16)&511)|0x4000;
            REG16(oam+4)=512+i*72+j*8;
        }
    }
}
static void upload_cursor(void){
    unsigned oam=0x07000000+36*8;
    REG16(oam)=0x0200;
    if(!cursor_visible)return;
    /* Map cursors and portrait dialogues are separate surfaces. A later
     * dialogue must restore its original full OBJ palette after this color. */
    REG16(0x05000202)=game_palette[5];cached_portrait_sheet=-1;
    REG16(oam)=cursor_y&255;REG16(oam+2)=(cursor_x&511)|0x4000;REG16(oam+4)=800;
}
void video_overlays_present(void){
    upload_portraits();upload_cursor();
    REG16(0x04000000)=(REG16(0x04000000)&~0x1000)|((portrait_count||cursor_visible)?0x1000:0);
    video_metrics[4]++;ui_ready=1;
}
/* Mode 0 background cache: 32 columns x 24 rows of 8bpp tiles (48 KiB).
 * The 32x32 screen map points into this ring. Scrolling changes HOFS/VOFS;
 * only newly exposed edge tiles are uploaded, never a scrolled framebuffer.
 * Mode 4 dialogue/menu flips invalidate VRAM ownership explicitly. */
int video_map_active(void){return map_active;}
void *video_map_scratch(void){return framebuffer;}
void video_map_upload(int x,int y,int width,int height,int camera_x,int camera_y){
 int xx,yy,row;
 for(yy=y;yy<y+height;yy+=8)for(xx=x;xx<x+width;xx+=8){
  int tx=(xx+camera_x)/8,ty=(yy+camera_y)/8,slot=(ty%24)*32+(tx&31);
  volatile u16*dst=(volatile u16*)(0x06000000+slot*64);
  for(row=0;row<8;row++){const u16*src=framebuffer+(yy+row)*120+xx/2;int k;for(k=0;k<4;k++)*dst++=src[k];}
  REG16(0x0600e000+(((ty&31)*32+(tx&31))*2))=slot;
  map_video_metrics[0]++;map_video_metrics[1]+=64;
 }
}
static void map_obj(int id,int x,int y,int size,int tile){
 unsigned at=0x07000000+id*8;
 REG16(at)=(y&255)|0x2000;REG16(at+2)=(x&511)|(size<<14);REG16(at+4)=tile;
}
static void map_hint_tiles(void){
 int t,y,x;/* Tiles 768..807: four directions, lit/gray, then two point icons. */
 for(t=0;t<11;t++)for(y=0;y<8;y++)for(x=0;x<8;x+=2){
  int k;u16 packed=0;
  for(k=0;k<2;k++){int px=x+k,color=0;
   if(t<8){int d=t/2,a=d==1?7-px:d==3?px:y,b=d==1||d==3?y:px;if(d==2)a=7-y;
    if(a>=1&&a<=6&&b>=3-a/2&&b<=4+a/2)color=t&1?12:2;
   }else{int dx=px<4?3-px:px-4,dy=y<4?3-y:y-4;
    if(dx+dy<=3)color=dx+dy==3?14:t==8?2:t==9?5:12;
    if(dx+dy<1)color=13;
   }packed|=color<<(k*8);
  }REG16(0x06016000+t*64+y*8+x)=packed;
 }
 /* A high contrast selection frame never vanishes: yellow/white alternate. */
 for(t=0;t<2;t++)for(y=0;y<16;y++)for(x=0;x<16;x+=2){int k;u16 packed=0;
  for(k=0;k<2;k++){int px=x+k,c=0;if((px==0||px==15||y==0||y==15))c=14;
   else if((px==1||px==14||y==1||y==14))c=t?13:2;packed|=c<<(k*8);}
  {int tile=(y/8)*2+x/8,at=(y%8)*8+x%8;REG16(0x06016500+t*256+tile*64+at)=packed;}
 }
 /* The selected marker says what can happen there, rather than relying on
  * a tiny blinking border whose meaning the opening tutorial must explain. */
 {static const char labels[2][5]={"调查","受阻"};int state,row,col;
  for(state=0;state<2;state++)for(row=0;row<16;row++)for(col=0;col<32;col+=2){int k;u16 packed=0;
   for(k=0;k<2;k++){int px=col+k,color=11,character=(px-4)/12,gx=(px-4)%12;
    if(!px||px==31||!row||row==15)color=state?12:2;
    else if(px>=4&&px<28&&row>=2&&row<14){unsigned code=(u8)labels[state][character*2]*256+(u8)labels[state][character*2+1];int lo=0,hi=GLYPH_COUNT;
     while(lo<hi){int mid=(lo+hi)/2;if(glyph_codes[mid]<code)lo=mid+1;else hi=mid;}
     if(lo<GLYPH_COUNT&&glyph_codes[lo]==code&&(glyph_rows[lo][row-2]&(1<<(11-gx))))color=state?12:1;
    }packed|=color<<(k*8);
   }{int tile=(row/8)*4+col/8,at=(row%8)*8+col%8;REG16(0x06017a00+state*512+tile*64+at)=packed;}
  }
 }
}
void video_map_objects_begin(void){
 int i;map_actor_count=map_point_count=hud_count=0;cursor_visible=0;portrait_count=0;
 for(i=0;i<128;i++)REG16(0x07000000+i*8)=0x0200;
 if(!map_active){
  for(i=0;i<256;i++)REG16(0x05000200+i*2)=game_palette[i];
  for(i=0;i<48;i++)actor_cache[i]=-1;for(i=0;i<9;i++)actor_banks[i]=-1;
  hud_cache[0]=hud_cache[1]=-1;
  for(i=0;i<4;i++)cached_portraits[i]=-1;cached_portrait_sheet=-1;
  map_hint_tiles();
 }
}
static void map_palette(int image,int bank){int i;for(i=0;i<16;i++)REG16(0x05000200+(bank*16+i)*2)=game_palette[images[image].palette[i]];}
static void map_inverse(int image){int i;memset(image_line+768,0,256);for(i=0;i<16;i++)image_line[768+images[image].palette[i]]=i;image_line[768]=0;}
void video_map_actor(int image,int index,int direction,int x,int y){
 int slot=map_actor_count,d=direction==8?0:direction==6?1:direction==2?2:3,key=image*128+index*4+d,bank;
 if(image<0||slot>=48||x<=-32||y<=-32||x>=240||y>=160)return;
 for(bank=0;bank<9&&actor_banks[bank]!=image;bank++)if(actor_banks[bank]<0){actor_banks[bank]=image;map_palette(image,bank+1);break;}
 if(bank==9)return;
 if(actor_cache[slot]!=key){int row,col,sx=index%4*72+24,sy=(index/4*4+d)*32;
  map_inverse(image);
  for(row=0;row<32;row++){
   if(!decode_image_span(images+image,sy+row,sx,24,image_line,768))return;
   for(col=0;col<32;col+=4){int tile=(row/8)*4+col/8,offset=(row%8)*4+(col%8)/2,k;u16 value=0;
    if(col<24)for(k=0;k<4;k++)value|=image_line[768+image_line[col+k]]<<(k*4);
    REG16(0x06010000+slot*512+tile*32+offset)=value;
   }if(!(row&7))audio_service();
  }actor_cache[slot]=key;map_video_metrics[4]++;
 }
 {unsigned at=0x07000000+(slot+1)*8;REG16(at)=y&255;REG16(at+2)=(x&511)|0x8000;REG16(at+4)=slot*16|((bank+1)<<12);}
 map_actor_count++;
}
void video_map_point(int x,int y,int selected,int reachable){
 if(x< -7||x>=240||y< -7||y>=160)return;
 if(map_point_count<71)map_obj(49+map_point_count++,x,y,0,reachable?784:788);
 if(selected){unsigned at=0x07000000;
  map_obj(120,x-4,y-4,1,808+((map_blink>>4)&1)*8);
  REG16(at)=(clamp(y-19,0,144)&255)|0x6000;REG16(at+2)=(clamp(x-12,0,208)&511)|0x8000;REG16(at+4)=976+(reachable?0:16);
 }
}
void video_map_player(int x,int y){if(x> -8&&x<240&&y> -8&&y<160)map_obj(121,x,y,0,786);}
void video_map_hud(int image,int x,int y){
 int slot=hud_count,row,col;const Image*im=images+image;
 if(slot>=2||im->width>64||im->height>32)return;
 if(hud_cache[slot]!=image){
  map_palette(image,10+slot);map_inverse(image);
  for(row=0;row<32;row++){
   if(row<im->height&&!decode_image_row(im,row,image_line,768))return;
   for(col=0;col<64;col+=4){int tile=(row/8)*8+col/8,at=(row%8)*4+(col%8)/2,k;u16 value=0;
    if(row<im->height)for(k=0;k<4&&col+k<im->width;k++)value|=image_line[768+image_line[col+k]]<<(k*4);
    REG16(0x06016a00+slot*2048+tile*32+at)=value;
   }
  }hud_cache[slot]=image;
 }
 {unsigned at=0x07000000+(122+slot)*8;REG16(at)=(y&255)|0x4000;REG16(at+2)=(x&511)|0xc000;REG16(at+4)=(848+slot*64)|((10+slot)<<12);}
 hud_count++;
}
void video_map_present(int camera_x,int camera_y,int directions){
 static const short xy[4][2]={{116,2},{230,76},{116,150},{2,76}};int d;
 for(d=0;d<4;d++)map_obj(124+d,xy[d][0],xy[d][1],0,768+d*4+((directions&(1<<d))?0:2));
 REG16(0x04000008)=0x1c83;/* BG0, 8bpp, char base 0, screen base 28. */
 REG16(0x04000010)=camera_x&255;REG16(0x04000012)=camera_y&255;
 REG16(0x04000000)=0x1140;map_active=1;map_video_metrics[2]++;ui_ready=1;
}
static void pixel(int x,int y,int c){if(x>=clip_left&&x<clip_right&&y>=clip_top&&y<clip_bottom)((u8*)framebuffer)[y*240+x]=c;}
void box(int x,int y,int w,int h,int c){int j,x1=clamp(x,clip_left,clip_right),x2=clamp(x+w,clip_left,clip_right),y1=clamp(y,clip_top,clip_bottom),y2=clamp(y+h,clip_top,clip_bottom);if(x2<=x1||y2<=y1)return;framebuffer_revision++;for(j=y1;j<y2;j++)memset((u8*)framebuffer+j*240+x1,c,x2-x1);}
void rect(int x,int y,int w,int h,int c){box(x,y,w,1,c);box(x,y+h-1,w,1,c);box(x,y,1,h,c);box(x+w-1,y,1,h,c);}
void picture(int id,int x,int y,int sx,int sy,int w,int h,int transparent){
    const Image *im=images+id;int i,j,left=0,right=w,top=0,bottom=h;
    if(x<clip_left)left=clip_left-x;if(sx<0&&left<-sx)left=-sx;if(y<clip_top)top=clip_top-y;if(sy<0&&top<-sy)top=-sy;
    if(x+right>clip_right)right=clip_right-x;if(sx+right>im->width)right=im->width-sx;if(y+bottom>clip_bottom)bottom=clip_bottom-y;if(sy+bottom>im->height)bottom=im->height-sy;
    if(right<=left||bottom<=top)return;framebuffer_revision++;
    for(j=top;j<bottom;j++){if(!(j&7))audio_service();if(!decode_image_row(im,sy+j,image_line,sizeof(image_line)))return;if(!transparent)memcpy((u8*)framebuffer+(y+j)*240+x+left,image_line+sx+left,right-left);else for(i=left;i<right;i++){int c=image_line[sx+i];if(c)pixel(x+i,y+j,c);}}
}
void picture_scaled(int id,int x,int y,int w,int h){const Image*im=images+id;picture_region_scaled(id,x,y,0,0,im->width,im->height,w,h,0,0,0);}
void picture_region_scaled(int id,int x,int y,int sx,int sy,int sw,int sh,int w,int h,int transparent,int opacity,const u8*tone){
 const Image*im=images+id;static u8 adjusted[256],old_tone[4];static int tone_ready;int i,j,tinted=tone&&(tone[0]!=100||tone[1]!=100||tone[2]!=100||tone[3]!=100);
 if(w<=0||h<=0||sw<=0||sh<=0||opacity>=100||x>=clip_right||y>=clip_bottom||x+w<=clip_left||y+h<=clip_top)return;
 framebuffer_revision++;
 video_metrics[0]++;
 audio_service();
 if((im->encoding==0||im->encoding==3)&&im->width==8&&im->height==8&&sx==0&&sy==0&&sw==8&&sh==8&&w==6&&(h==5||h==6)&&!opacity&&!tinted){
  static const u8 six[6]={0,1,2,4,5,6},five[5]={0,1,3,4,6};int first=x<clip_left?clip_left-x:0,last=x+6>clip_right?clip_right-x:6;
  for(j=0;j<h;j++){int yy=y+j,src=(h==5?five[j]:six[j])*8;if(yy<clip_top||yy>=clip_bottom)continue;for(i=first;i<last;i++){int at=src+six[i],c=im->encoding==3?im->palette[(im->pixels[at/2]>>(at&1?0:4))&15]:im->pixels[at];if(c||!transparent)((u8*)framebuffer)[yy*240+x+i]=c;}}return;
 }

 if(tinted&&(!tone_ready||old_tone[0]!=tone[0]||old_tone[1]!=tone[1]||old_tone[2]!=tone[2]||old_tone[3]!=tone[3])){for(i=0;i<256;i++){unsigned color=game_palette[i];int r=color&31,g=color>>5&31,b=color>>10&31,gray=(r*30+g*59+b*11)/100;
   if(!(i&7))audio_service();
   r=clamp((gray+(r-gray)*tone[3]/100)*tone[0]/100,0,31);g=clamp((gray+(g-gray)*tone[3]/100)*tone[1]/100,0,31);b=clamp((gray+(b-gray)*tone[3]/100)*tone[2]/100,0,31);
   adjusted[i]=palette_rgb555_start[r|(g<<5)|(b<<10)];
  }for(i=0;i<4;i++)old_tone[i]=tone[i];tone_ready=1;}
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
  if(!transparent&&!opacity&&!tinted){for(i=0;i<last-first;i++)if(columns[i]!=65535)destination[i]=image_line[columns[i]-span_left];}
  else for(i=0;i<last-first;i++){
   int c;if(columns[i]==65535)continue;c=image_line[columns[i]-span_left];
   if(transparent&&!c)continue;
   if(tinted)c=adjusted[c];
   if(opacity){
    /* Uniform palette alpha. A diagonal discard mask is visibly patterned
     * even after an animation ends, so it must not stand in for translucency.
     * Packed red/blue lanes stay separate with 0..32 coefficients. */
    unsigned src=game_palette[c],dst=game_palette[destination[i]];
    unsigned rb=(((src&0x7c1f)*(32-alpha)+(dst&0x7c1f)*alpha)>>5)&0x7c1f;
    unsigned green=(((src&0x03e0)*(32-alpha)+(dst&0x03e0)*alpha)>>5)&0x03e0;
    c=palette_rgb555_start[rb|green];
   }
   destination[i]=c;
  }
 }

}
static void glyph(int x,int y,unsigned code,int color){
    int lo=0,hi=GLYPH_COUNT-1,mid,i,j;
    if(code>=0x10000&&code<0x10034){for(j=0;j<12;j++){u16 row=exfont_rows[code-0x10000][j];for(i=0;i<12;i++)if(row&(1<<(11-i)))pixel(x+i,y+j,color);}return;}
    while(lo<=hi){mid=(lo+hi)/2;if(glyph_codes[mid]<code)lo=mid+1;else if(glyph_codes[mid]>code)hi=mid-1;else{
        for(j=0;j<12;j++){u16 row=glyph_rows[mid][j];for(i=0;i<12;i++)if(row&(1<<(11-i)))pixel(x+i,y+j,color);}return;
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
    /* A full-frame DMA blocks the ARM7 and its sound refill interrupt longer
     * than the FIFO can cover. Permit IRQ service between bounded transfers;
     * timer-driven redraws must not drop part of the original music. */
    unsigned done=0;u32 destination=page?0x0600a000:0x06000000;
    if(map_active){int i;map_active=0;for(i=0;i<128;i++)REG16(0x07000000+i*8)=0x0200;}
    while(done<9600){unsigned words=9600-done;if(!(done&1023))audio_service();if(words>64)words=64;REG32(0x040000d4)=(u32)framebuffer+done*4;REG32(0x040000d8)=destination+done*4;REG32(0x040000dc)=0x84000000|words;done+=words;}
    upload_portraits();upload_cursor();
    REG16(0x04000000)=0x0444|((portrait_count||cursor_visible)?0x1000:0)|(page?0x10:0);page^=1;
    ui_ready=1;
}
