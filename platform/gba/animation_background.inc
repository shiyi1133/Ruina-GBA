/* Lossless battle underlay in the unused Mode-3 VRAM tail. Eight RGB555 rows
 * per block need only the existing 4 KiB decoder workspace. A scene that does
 * not fit falls back to clipped source drawing; no quality is sacrificed. */
static u16 animation_background_offsets[21];
static u32 animation_background_stamp;
static int animation_background_valid;
static unsigned animation_pack_at,animation_pack_half;
static int animation_pack_failed;
#define ANIMATION_CACHE ((volatile u16*)0x06012c00)
#define ANIMATION_CACHE_BYTES (0x17f00-0x12c00)
static inline __attribute__((target("arm"),always_inline)) void animation_emit(unsigned byte){
    if(animation_pack_at>=ANIMATION_CACHE_BYTES){animation_pack_failed=1;return;}
    if(!(animation_pack_at&1))animation_pack_half=byte;
    else ANIMATION_CACHE[animation_pack_at/2]=animation_pack_half|(byte<<8);
    animation_pack_at++;
}
static inline __attribute__((target("arm"),always_inline)) void animation_length(unsigned n){while(n>=255){animation_emit(255);n-=255;}animation_emit(n);}
static inline __attribute__((target("arm"),always_inline)) unsigned animation_hash(const u8*p){return ((p[0]|p[1]<<8|p[2]<<16|(u32)p[3]<<24)*2654435761U)>>21;}
static void __attribute__((target("arm"),optimize("O3"),noinline)) animation_pack(const u8*src,unsigned length,u16*table){
    unsigned anchor=0,at=0,i,next_service=0;memset(table,0,4096);
    while(at+12<=length){if(at>=next_service){audio_service();next_service=at+512;}unsigned hash=animation_hash(src+at),old=table[hash],count=4,literal,match;table[hash]=at+1;
        if(!old){at++;continue;}old--;
        if(src[old]!=src[at]||src[old+1]!=src[at+1]||src[old+2]!=src[at+2]||src[old+3]!=src[at+3]){at++;continue;}
        while(at+count<length-5&&src[old+count]==src[at+count])count++;
        literal=at-anchor;match=count-4;animation_emit((literal<15?literal:15)*16+(match<15?match:15));if(literal>=15)animation_length(literal-15);
        for(i=anchor;i<at;i++)animation_emit(src[i]);animation_emit(at-old);animation_emit((at-old)>>8);if(match>=15)animation_length(match-15);
        for(i=at+1;i<at+count&&i+4<=length;i++)table[animation_hash(src+i)]=i+1;
        at+=count;anchor=at;
    }
    i=length-anchor;animation_emit((i<15?i:15)*16);if(i>=15)animation_length(i-15);for(i=anchor;i<length;i++)animation_emit(src[i]);
}
void balanced_animation_background_store(void){
    unsigned row;u16*table;animation_background_valid=0;if(!bitmap_direct)return;
    cached_portrait_sheet=-1;for(row=0;row<7;row++)cached_portraits[row]=-1;
    table=image_decode_scratch();animation_pack_at=animation_pack_failed=0;
    for(row=0;row<20;row++){audio_service();animation_background_offsets[row]=animation_pack_at;animation_pack((const u8*)(framebuffer+row*8*240),3840,table);if(animation_pack_failed)return;}
    animation_background_offsets[20]=animation_pack_at;if(animation_pack_at&1)ANIMATION_CACHE[animation_pack_at/2]=animation_pack_half;
    animation_background_stamp=battle_render_stamp();animation_background_valid=1;
    image_decode_scratch();
}
int balanced_animation_background_restore(int x,int y,int w,int h){
    unsigned block,start=y/8,end=(y+h-1)/8,row;u8*scratch;
    if(!bitmap_direct||!animation_background_valid||animation_background_stamp!=battle_render_stamp())return 0;
    scratch=image_decode_scratch();
    for(block=start;block<=end;block++){unsigned top=block*8,bottom=top+8,left=animation_background_offsets[block],right=animation_background_offsets[block+1];audio_service();
        if(image_unpack_block((const u8*)ANIMATION_CACHE+left,right-left,scratch,4096)!=3840){animation_background_valid=0;return 0;}
        if(top<(unsigned)y)top=y;if(bottom>(unsigned)(y+h))bottom=y+h;
        for(row=top;row<bottom;row++)memcpy(framebuffer+row*240+x,scratch+(row-block*8)*480+x*2,w*2);
    }
    rgb_damage(x,y,w,h);framebuffer_revision++;image_decode_scratch();return 1;
}
