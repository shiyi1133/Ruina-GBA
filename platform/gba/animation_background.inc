/* Lossless battle underlay in the unused Mode-3 VRAM tail. Eight RGB555 rows
 * per block need only the existing 4 KiB decoder workspace. A scene that does
 * not fit falls back to clipped source drawing; no quality is sacrificed. */
static u16 animation_background_offsets[21];
static u16 animation_background_sizes[20];
static u8 animation_background_kinds[20];
static u16 animation_tile_offsets[80],animation_tile_sizes[80],animation_strip_palettes[10];
static u32 animation_tile_hashes[80];
static u8 animation_strip_wide[10];
static int animation_background_tiled;
volatile u32 animation_cache_layout[4];/* layout, palette maximum, unique tiles, bytes */
volatile u32 animation_cache_reuse_debug[4];/* complete hits, art hits, art builds, modal shares */
volatile u32 animation_tile_attempt[4];/* failure reason, last stripe/tile, bytes, colors */
static u32 animation_background_stamp;
static u32 animation_background_epoch,animation_art_stamp;
static unsigned animation_art_end;
static int animation_background_valid;
void balanced_animation_background_forget(void){animation_background_valid=0;}
static unsigned animation_pack_at,animation_pack_half;
static int animation_pack_failed;
volatile u32 animation_cache_debug[8];/* stores, valid, bytes, overflow,
 * successful restores, fallback restores, last build ticks, reserved */
#define ANIMATION_CACHE ((volatile u16*)0x06012c00)
#define ANIMATION_CACHE_BYTES (0x17f00-0x12c00)
/* Preparation and restoration share one instruction slot. Neither routine
 * can run while the other owns this slot; audio has independent fast RAM. */
static unsigned animation_codec_owner;
static void animation_codec_load(unsigned owner){
 extern u8 __animation_codec_start[];extern const u8 __load_start_animation_encoder[],__load_stop_animation_encoder[],__load_start_animation_restore[],__load_stop_animation_restore[];
 const u8*source=owner==1?__load_start_animation_encoder:__load_start_animation_restore;unsigned bytes=owner==1?__load_stop_animation_encoder-source:__load_stop_animation_restore-source;
 if(animation_codec_owner!=owner){memcpy(__animation_codec_start,source,bytes);animation_codec_owner=owner;}
}
static inline __attribute__((target("arm"),always_inline)) void animation_emit(unsigned byte){
    if(animation_pack_at>=ANIMATION_CACHE_BYTES){animation_pack_failed=1;return;}
    byte&=255;
    if(!(animation_pack_at&1))animation_pack_half=byte;
    else ANIMATION_CACHE[animation_pack_at/2]=animation_pack_half|(byte<<8);
    animation_pack_at++;
}
static inline __attribute__((target("arm"),always_inline)) void animation_length(unsigned n){while(n>=255){animation_emit(255);n-=255;}animation_emit(n);}
/* Four recent matches per bucket fit the same 4 KiB workspace. A single
 * collision used to discard useful horizontal/vertical matches, overflow
 * VRAM and force the entire battle scene to be redrawn on every frame. */
static inline __attribute__((target("arm"),always_inline)) unsigned animation_hash(const u8*p){return (((p[0]|p[1]<<8|p[2]<<16|(u32)p[3]<<24)*2654435761U)>>23)*4;}
static inline __attribute__((target("arm"),always_inline)) void animation_remember(u16*table,unsigned hash,unsigned value){table[hash+3]=table[hash+2];table[hash+2]=table[hash+1];table[hash+1]=table[hash];table[hash]=value;}
/* An exact per-strip palette makes RGB555 underlays cheaper to reconstruct.
 * Index zero is reserved so the existing opaque-run painter can restore
 * visible black without confusing it with transparent effect pixels. */
static unsigned __attribute__((target("arm"),optimize("O3"))) animation_index_strip(const u16*source,u16*indices,u16*colors,u32*table){
 unsigned i,count=1;memset(table,0,4096);colors[0]=0;
 for(i=0;i<1920;i++){
  unsigned color=source[i],slot=(color*2654435761U)>>22,entry;
  if(!(i&255))audio_service();
  while((entry=table[slot])&&(entry&65535)!=color)slot=(slot+1)&1023;
  if(!entry){if(count==512)return 0;colors[count]=color;entry=color|(count++<<16);table[slot]=entry;}
  indices[i]=entry>>16;
 }
 return count-1;
}
static void __attribute__((target("arm"),optimize("O3"),section(".animation_encoder"),long_call,noinline)) animation_pack(const u8*src,unsigned length,u16*table){
    unsigned anchor=0,at=0,i,next_service=0;memset(table,0,4096);
    while(at+12<=length){if(at>=next_service){audio_service();next_service=at+512;}unsigned hash=animation_hash(src+at),old=0,count=3,literal,match,k;
        for(k=0;k<4;k++){unsigned candidate=table[hash+k],n=4;if(!candidate)break;candidate--;
            if(count>=4){if(at+count>=length-5)break;if(src[candidate+count]!=src[at+count])continue;}
            if(src[candidate]!=src[at]||src[candidate+1]!=src[at+1]||src[candidate+2]!=src[at+2]||src[candidate+3]!=src[at+3])continue;
            while(at+n<length-5&&src[candidate+n]==src[at+n])n++;
            if(n>count){count=n;old=candidate;}
        }
        animation_remember(table,hash,at+1);if(count<4){at++;continue;}
        literal=at-anchor;match=count-4;animation_emit((literal<15?literal:15)*16+(match<15?match:15));if(literal>=15)animation_length(literal-15);
        for(i=anchor;i<at;i++)animation_emit(src[i]);animation_emit(at-old);animation_emit((at-old)>>8);if(match>=15)animation_length(match-15);
        /* Sampling a completed match is sufficient for future references.
         * Rehashing every byte of a solid UI strip dominated preparation. */
        for(i=at+1;i<at+count&&i+4<=length;i+=4)animation_remember(table,animation_hash(src+i),i+1);
        at+=count;anchor=at;
    }
    i=length-anchor;animation_emit((i<15?i:15)*16);if(i>=15)animation_length(i-15);for(i=anchor;i<length;i++)animation_emit(src[i]);
}
static int __attribute__((target("arm"),optimize("O3"),section(".animation_prepare"),long_call,noinline)) animation_store_tiles(u16*encoder,int reuse_art){
 u8*workspace=balanced_animation_workspace();u32*lookup=(u32*)workspace;u16*colors=(u16*)(workspace+4096),*indices=(u16*)(workspace+5120);unsigned stripe,tile,step,unique=0,maximum=0;
 animation_pack_at=reuse_art?animation_art_end:0;animation_pack_failed=0;
 animation_tile_attempt[0]=0;
 /* Store static battlefield art first. Turn, focus, HP and MP only change
  * the header/status stripes, so consecutive actions reuse the art pool. */
 for(step=reuse_art?5:0;step<10;step++){stripe=step<5?step+1:step==5?0:step;
  unsigned i,n=1;const u16*source=framebuffer+stripe*16*240;memset(lookup,0,4096);
  for(i=0;i<3840;i++){
   unsigned color=source[i],slot=(color*2654435761U)>>22,entry;if(!(i&255))audio_service();
   if(i&&color==source[i-1])continue;
   while((entry=lookup[slot])&&(entry&65535)!=color)slot=(slot+1)&1023;
   if(!entry){if(n==512){animation_tile_attempt[0]=1;animation_tile_attempt[1]=stripe;return 0;}colors[n]=color;lookup[slot]=color|(n++<<16);}
  }
  n--;if(n>maximum)maximum=n;animation_strip_wide[stripe]=n>255;
  if(animation_pack_at&1)animation_emit(0);animation_strip_palettes[stripe]=animation_pack_at;animation_emit(n);animation_emit(n>>8);
  for(i=1;i<=n;i++){animation_emit(colors[i]);animation_emit(colors[i]>>8);}
  for(tile=0;tile<8;tile++){
   unsigned width=tile==7?16:32,at=0,row,col,hash=2166136261U,key=stripe*8+tile,bytes=width*16*(n>255?2:1),same=0,last_color=65536,last_index=0;
   for(row=0;row<16;row++)for(col=0;col<width;col++){
    unsigned color=source[row*240+tile*32+col],slot=(color*2654435761U)>>22;
    if(color!=last_color){while((lookup[slot]&65535)!=color)slot=(slot+1)&1023;last_color=color;last_index=lookup[slot]>>16;}
    indices[at++]=last_index;hash=(hash^last_index)*16777619U;
   }
   if(n<=255)for(i=0;i<at;i++)((u8*)indices)[i]=indices[i];
   /* Identical font/blank tiles share bytes only after exact reconstruction;
    * the hash is a filter rather than a correctness assumption. */
   for(i=stripe*8;i<key;i++)if(animation_tile_hashes[i]==hash&&(i%8==7)==(tile==7)){
    unsigned j;if(image_unpack_block((const u8*)ANIMATION_CACHE+animation_tile_offsets[i],animation_tile_sizes[i],(u8*)encoder,4096)!=(int)bytes)continue;
    for(j=0;j<bytes&&((u8*)encoder)[j]==((u8*)indices)[j];j++){}
    if(j==bytes){animation_tile_offsets[key]=animation_tile_offsets[i];animation_tile_sizes[key]=animation_tile_sizes[i];same=1;break;}
   }
   animation_tile_hashes[key]=hash;if(same)continue;
   animation_tile_offsets[key]=animation_pack_at;animation_pack((const u8*)indices,bytes,encoder);animation_tile_sizes[key]=animation_pack_at-animation_tile_offsets[key];unique++;
   animation_tile_attempt[1]=key;animation_tile_attempt[2]=animation_pack_at;animation_tile_attempt[3]=n;
   if(animation_pack_failed){animation_tile_attempt[0]=2;return 0;}
  }
  if(step==4){if(animation_pack_at&1)animation_emit(0);animation_art_end=animation_pack_at;}
 }
 if(animation_pack_at&1)ANIMATION_CACHE[animation_pack_at/2]=animation_pack_half;
 animation_cache_layout[0]=2;animation_cache_layout[1]=maximum;animation_cache_layout[2]=unique;animation_cache_layout[3]=animation_pack_at;return 1;
}
static int __attribute__((target("arm"),optimize("O3"),section(".animation_restore"),long_call,noinline)) animation_restore_tiles(int x,int y,int w,int h){
 unsigned stripe,first=y/16,last=(y+h-1)/16;
 for(stripe=first;stripe<=last;stripe++){
  const u16*source=(const u16*)((const u8*)ANIMATION_CACHE+animation_strip_palettes[stripe]);unsigned n=*source++,i,tile,top=stripe*16,bottom=top+16;
  if(x==0&&w==240&&((animation_opaque_tiles[stripe>>2]>>((stripe&3)*8))&255)==255)continue;
  if(!n||n>=512)return 0;animation_blend_alpha=-1;rgb_secondary.ends[0]=0;
  for(i=0;i<n;i++){u16 c=source[i];rgb_secondary.ends[i+1]=animation_palette_alpha?rgb_mix(animation_palette_color,c,animation_palette_alpha):c;}
  if(top<(unsigned)y)top=y;if(bottom>(unsigned)(y+h))bottom=y+h;
  for(tile=x/32;tile<=(unsigned)(x+w-1)/32;tile++){
   unsigned width=tile==7?16:32,key=stripe*8+tile,left=tile*32,right=left+width,row,size=width*16*(animation_strip_wide[stripe]?2:1);audio_service();
   if(animation_opaque_tiles[key>>5]&(1U<<(key&31)))continue;
   if(image_unpack_block((const u8*)ANIMATION_CACHE+animation_tile_offsets[key],animation_tile_sizes[key],image_line,sizeof(image_line))!=(int)size)return 0;
   if(left<(unsigned)x)left=x;if(right>(unsigned)(x+w))right=x+w;
   for(row=top;row<bottom;row++){
    unsigned at=(row-stripe*16)*width+left-tile*32;u16*dest=framebuffer+row*240+left;
    if(animation_strip_wide[stripe]){const u16*indices=(const u16*)image_line+at;for(i=0;i<right-left;i++)dest[i]=rgb_secondary.ends[indices[i]];}
    else animation_restore_indexed(dest,image_line+at,rgb_secondary.ends,right-left);
   }
  }
 }
 rgb_damage(x,y,w,h);framebuffer_revision++;return 1;
}
void balanced_animation_background_store(void){
    unsigned row,start=video_ticks();u32 stamp=battle_render_stamp(),art=battle_art_stamp();int reuse_art=animation_background_valid&&animation_background_tiled&&animation_background_epoch==balanced_surface_epoch&&animation_art_stamp==art;u16*table,*work,*palette;animation_cache_debug[0]++;
    if(bitmap_direct&&animation_background_valid&&animation_background_epoch==balanced_surface_epoch&&animation_background_stamp==stamp){animation_cache_reuse_debug[0]++;animation_cache_debug[6]=0;return;}
    work=balanced_animation_workspace();palette=work+2048;animation_cache_debug[1]=0;animation_background_valid=0;if(!bitmap_direct)return;
    cached_portrait_sheet=-1;for(row=0;row<7;row++)cached_portraits[row]=-1;
    table=image_decode_scratch();animation_background_tiled=0;animation_codec_load(1);
    {extern const u8 __load_start_animation_prepare[],__load_stop_animation_prepare[];unsigned bytes=__load_stop_animation_prepare-__load_start_animation_prepare;
     if(bytes>sizeof(animation_fast_memory)){fault(9035);return;}
     memcpy(&animation_fast_memory,__load_start_animation_prepare,bytes);rgb_old_colors=0;animation_blend_alpha=-1;
    }
    if(animation_store_tiles(table,reuse_art)){animation_cache_reuse_debug[reuse_art?1:2]++;animation_background_tiled=1;animation_background_stamp=stamp;animation_background_epoch=balanced_surface_epoch;animation_art_stamp=art;animation_background_valid=1;animation_cache_debug[1]=1;animation_cache_debug[2]=animation_pack_at;animation_cache_debug[6]=(u16)(video_ticks()-start);image_decode_scratch();return;}
    animation_cache_layout[0]=1;animation_pack_at=animation_pack_failed=0;
    for(row=0;row<20;row++){
        unsigned n,i;const u8*source=(const u8*)(framebuffer+row*8*240);audio_service();if(animation_pack_at&1)animation_emit(0);animation_background_offsets[row]=animation_pack_at;
        n=animation_index_strip((const u16*)source,work,palette,(u32*)table);animation_background_kinds[row]=n?(n<=255?1:2):0;
        if(n){animation_emit(n);animation_emit(n>>8);for(i=1;i<=n;i++){animation_emit(palette[i]);animation_emit(palette[i]>>8);}
            if(n<=255)for(i=0;i<1920;i++)((u8*)work)[i]=work[i];
            animation_pack((const u8*)work,n<=255?1920:3840,table);
        }else animation_pack(source,3840,table);
        animation_background_sizes[row]=animation_pack_at-animation_background_offsets[row];
        if(animation_pack_failed){animation_cache_debug[3]++;animation_cache_debug[2]=animation_pack_at;return;}
    }
    animation_background_offsets[20]=animation_pack_at;if(animation_pack_at&1)ANIMATION_CACHE[animation_pack_at/2]=animation_pack_half;
    animation_background_stamp=stamp;animation_background_epoch=balanced_surface_epoch;animation_background_valid=1;
    animation_cache_debug[1]=1;animation_cache_debug[2]=animation_pack_at;animation_cache_debug[6]=(u16)(video_ticks()-start);image_decode_scratch();
}
int __attribute__((target("arm"),optimize("O3"))) balanced_animation_background_restore(int x,int y,int w,int h){
    unsigned block,start=y/8,end=(y+h-1)/8,row;u8*scratch=0;
    if(!bitmap_direct||!animation_background_valid||animation_background_epoch!=balanced_surface_epoch||animation_background_stamp!=battle_render_stamp()){animation_cache_debug[5]++;return 0;}
    if(animation_background_tiled){int ok;animation_codec_load(2);ok=animation_restore_tiles(x,y,w,h);if(ok)animation_cache_debug[4]++;else animation_background_valid=0;return ok;}
    for(block=start;block<=end;block++){unsigned top=block*8,bottom=top+8,left=animation_background_offsets[block],right=left+animation_background_sizes[block];audio_service();
        {unsigned tx,covered=1;for(tx=x/32;tx<=(unsigned)(x+w-1)/32;tx++){unsigned key=(block/2)*8+tx;if(!(animation_opaque_tiles[key>>5]&(1U<<(key&31)))){covered=0;break;}}if(covered)continue;}
        if(animation_background_kinds[block]){
            const u8*source=(const u8*)ANIMATION_CACHE+left;unsigned n=source[0]|source[1]<<8,i,wide=animation_background_kinds[block]==2,size=wide?3840:1920;
            if(!n||n>=512||right-left<2+n*2){animation_background_valid=0;return 0;}
            animation_blend_alpha=-1;rgb_secondary.ends[0]=0;for(i=0;i<n;i++){u16 color=((const u16*)(source+2))[i];rgb_secondary.ends[i+1]=animation_palette_alpha?rgb_mix(animation_palette_color,color,animation_palette_alpha):color;}
            if(!scratch)scratch=image_decode_scratch();
            if(image_unpack_block(source+2+n*2,right-left-2-n*2,scratch,4096)!=(int)size){animation_background_valid=0;return 0;}
            if(top<(unsigned)y)top=y;if(bottom>(unsigned)(y+h))bottom=y+h;
            for(row=top;row<bottom;row++){
                unsigned at=(row-block*8)*240+x;u16*dest=framebuffer+row*240+x;
                if(wide){const u16*indices=(const u16*)scratch+at;for(i=0;i<(unsigned)w;i++)dest[i]=rgb_secondary.ends[indices[i]];}
                else animation_restore_indexed(dest,scratch+at,rgb_secondary.ends,w);
            }
            continue;
        }
        /* A complete damaged eight-row strip can be reconstructed directly.
         * This avoids a second 3,840-byte scratch-to-framebuffer copy and
         * leaves the original cell decoder's shared cache intact. */
        if(x==0&&w==240&&top>=(unsigned)y&&bottom<=(unsigned)(y+h)){
            if(image_unpack_block((const u8*)ANIMATION_CACHE+left,right-left,(u8*)(framebuffer+top*240),3840)!=3840){animation_background_valid=0;return 0;}
            if(animation_palette_alpha)balanced_animation_flash(0,top,240,8,animation_palette_color&31,(animation_palette_color>>5)&31,animation_palette_color>>10,animation_palette_power);
            animation_cache_debug[7]++;continue;
        }
        if(!scratch)scratch=image_decode_scratch();
        if(image_unpack_block((const u8*)ANIMATION_CACHE+left,right-left,scratch,4096)!=3840){animation_background_valid=0;return 0;}
        if(top<(unsigned)y)top=y;if(bottom>(unsigned)(y+h))bottom=y+h;
        for(row=top;row<bottom;row++)memcpy(framebuffer+row*240+x,scratch+(row-block*8)*480+x*2,w*2);
        if(animation_palette_alpha)balanced_animation_flash(x,top,w,bottom-top,animation_palette_color&31,(animation_palette_color>>5)&31,animation_palette_color>>10,animation_palette_power);
    }
    animation_cache_debug[4]++;rgb_damage(x,y,w,h);framebuffer_revision++;if(scratch)image_decode_scratch();return 1;
}
