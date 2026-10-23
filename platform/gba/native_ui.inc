/* Native-map text windows live in BG1. BG0 retains its decoded map tiles.
 * The idle tail of the CPU surface owns disposable UI tiles and lookups;
 * no extra full-screen buffer and no save-format change are required.
 * BG0: 24*32 8bpp tiles [0,c000), screen 30. BG1: 384 4bpp
 * tiles [c000,f000), screen 31. Tile 0 is always transparent. */
#define UI_TILES 384
static u32 (*const ui_tiles)[8]=(u32(*)[8])((u8*)framebuffer+49152);
static u32*const ui_hashes=(u32*)((u8*)framebuffer+61440);
static u8*const ui_visible=(u8*)framebuffer+62976;
static u8*const ui_pending=(u8*)framebuffer+63024;
static u16*const ui_screen=(u16*)((u8*)framebuffer+63072);
static u16*const ui_lookup=(u16*)((u8*)framebuffer+65120);
static u8*const ui_changed=(u8*)framebuffer+67168;
static u32*const ui_dirty=(u32*)((u8*)framebuffer+67216);
static u16*const ui_saved_object_palette=(u16*)((u8*)framebuffer+67296);
volatile u32 balanced_native_ui_metrics[8];/* windows, presents, tile writes,
 * tiles reused, capacity faults, max used tiles, late commits, reserved */

void balanced_native_ui_end(void){
    int i;
    native_ui_blocked_map=-1;
    if(!native_ui)return;
    native_ui=0;framebuffer_revision=native_ui_revision;
    if(native_ui_objects_changed){
        /* A text-only menu never changes actor textures or colors. For an
         * actual portrait, restore the saved actor palette and invalidate
         * only texture slots overlapping the portrait area [14000,18000). */
        memcpy(object_palette,ui_saved_object_palette,512);object_palette_dirty=65535;
        for(i=16;i<24;i++)actor_cache[i]=-1;
        hud_cache[0]=hud_cache[1]=-1;map_hints_pending=1;
    }
    portrait_count=0;portrait_visible=0;cursor_visible=0;native_ui_entering=0;
    balanced_surface_epoch++;
}
int balanced_native_ui_begin(void){
    int i;u32 stamp;
    if(world_cached_background()||battle_active||source_menu_active()||
       !world_native_map()||game.screen_hidden||scene_image>=0){balanced_native_ui_end();return 0;}
    if(native_ui_blocked_map==game.map&&native_ui_blocked_mode==(int)debug_state[15]&&native_ui_blocked_generation==ui_generation)return 0;
    stamp=balanced_scene_stamp();
    if(!native_ui||native_ui_stamp!=stamp){
        balanced_native_ui_end();world_redraw();
        if(!map_active||native_ui_map!=game.map)return 0;
        native_ui_revision=framebuffer_revision;native_ui=1;bitmap_direct=0;native_ui_entering=1;native_ui_objects_changed=0;
        memcpy(ui_saved_object_palette,object_palette,512);
        for(i=0;i<7;i++)cached_portraits[i]=-1;cached_portrait_sheet=-1;portrait_visible=0;
        balanced_surface_epoch++;native_ui_stamp=balanced_scene_stamp();
        memset(ui_hashes,0,UI_TILES*4);memset(ui_visible,0,UI_TILES/8);memset(ui_screen,0,2048);
        memset(ui_tiles[0],0,32);ui_visible[0]=1;
        for(i=0;i<16;i++)REG16(0x0600c000+i*2)=0;
        balanced_native_ui_metrics[0]++;
    }
    /* Zero is transparent only on this independent UI layer. Filled windows
     * use the original reserved system palette, including their black text. */
    clear(0);return 1;
}
static void native_ui_damage(int x,int y,int w,int h){
    unsigned mask;int row,last;if(w<=0||h<=0)return;
    mask=((1U<<((x+w+7)/8))-1)^((1U<<(x/8))-1);last=(y+h+7)/8;
    for(row=y/8;row<last;row++)ui_dirty[row]|=mask;
}
static void native_ui_fill(int left,int top,int right,int bottom,int color){
    unsigned value=(color&15U)*0x11111111U;int xx,yy,first,last;
    if(left>=right||top>=bottom)return;
    native_ui_damage(left,top,right-left,bottom-top);
    if(!left&&right==240){memset((u8*)framebuffer+top*120,(color&15)*17,(bottom-top)*120);return;}
    first=left/8;last=(right-1)/8;
    for(yy=top;yy<bottom;yy++){u32*dst=(u32*)framebuffer+yy*30;
        for(xx=first;xx<=last;xx++){unsigned mask=0xffffffffU;
            if(xx==first)mask<<=(left&7)*4;
            if(xx==last&&(right&7))mask&=(1U<<((right&7)*4))-1;
            dst[xx]=(dst[xx]&~mask)|(value&mask);
        }
    }
}
static void __attribute__((section(".iwram"),long_call,noinline)) native_ui_glyph(int x,int y,const u16*rows,int color,int left,int top,int right,int bottom){
    static const u16 spread[16]={0,61440,3840,65280,240,61680,4080,65520,15,61455,3855,65295,255,61695,4095,65535};
    unsigned value=(color&15U)*0x11111111U;int xx,yy,first=left/8,last=(right-1)/8;
    native_ui_damage(left,top,right-left,bottom-top);
    for(yy=top;yy<bottom;yy++){u32*dst=(u32*)framebuffer+yy*30;unsigned row=rows[yy-y];
        for(xx=first;xx<=last;xx++){int shift=4-(xx*8-x);unsigned bits=shift>=0?row>>shift:row<<-shift,mask=spread[(bits>>4)&15]|((u32)spread[bits&15]<<16);
            if(xx==first)mask&=0xffffffffU<<((left&7)*4);
            if(xx==last&&(right&7))mask&=(1U<<((right&7)*4))-1;
            dst[xx]=(dst[xx]&~mask)|(value&mask);
        }
    }
}
static unsigned __attribute__((section(".iwram"),long_call,noinline)) ui_pack(unsigned row,unsigned col,u32*tile){
    unsigned y,h=2166136261U,nonzero=0;
    for(y=0;y<8;y++){u32 word=((const u32*)framebuffer)[(row*8+y)*30+col];
        tile[y]=word;nonzero|=word;h=(h^word)*16777619U;
    }
    return nonzero?(h?h:1):0;
}
static int ui_equal(const u32*a,const u32*b){int k;for(k=0;k<8;k++)if(a[k]!=b[k])return 0;return 1;}
static void ui_insert(unsigned hash,unsigned tile){
    unsigned at=(hash^(hash>>16))&1023,n;
    for(n=0;n<1024;n++,at=(at+1)&1023)if(!ui_lookup[at]){ui_lookup[at]=tile;return;}
}
static unsigned ui_find(unsigned hash,const u32*tile){
    unsigned at=(hash^(hash>>16))&1023,n,id;
    for(n=0;n<1024;n++,at=(at+1)&1023){id=ui_lookup[at];if(!id)break;if(ui_hashes[id]==hash&&ui_equal(tile,ui_tiles[id]))return id;}
    return 0;
}
static void native_ui_fallback(void){
    PendingPortrait faces[4];int count=portrait_count,i,pixel;
    /* BG scroll registers are write-only on GBA; use the values committed
     * with the retained background, never an open-bus register read. */
    unsigned ox=map_camera_x,oy=map_camera_y;
    for(i=0;i<count;i++)faces[i]=pending_portraits[i];
    balanced_native_ui_end();
    /* A deliberately dense custom window may exceed the 384-tile layer.
     * Expand it backwards in the same surface. Transparent cells read the
     * retained map directly; no incomplete window is ever presented. */
    for(pixel=38399;pixel>=0;pixel--){unsigned packed=((u8*)framebuffer)[pixel/2],c=(packed>>((pixel&1)*4))&15,color;
        if(c)color=game_palette[c];
        else{unsigned x=(pixel%240+ox)&255,y=(pixel/240+oy)&255;
            unsigned tile=REG16(0x0600f000+((y/8*32+x/8)*2))&1023;
            unsigned index=*(volatile u8*)(0x06000000+tile*64+(y&7)*8+(x&7));
            color=REG16(0x05000000+index*2);
        }
        framebuffer[pixel]=color;if(!(pixel&1023))audio_service();
    }
    bitmap_direct=1;framebuffer_revision++;balanced_surface_epoch++;world_render_invalidate();
    native_ui_blocked_map=game.map;native_ui_blocked_mode=debug_state[15];native_ui_blocked_generation=ui_generation;
    balanced_faces[0]=0;for(i=0;i<count;i++)rgb_portrait(faces[i].record->image,faces[i].x,faces[i].y);
    rgb_damage(0,0,240,160);rgb_flip();
}
static void __attribute__((section(".iwram"),long_call,noinline)) native_ui_commit(void){
    unsigned start,end;
    unsigned i;
    audio_service();wait_commit_window();start=REG16(0x04000006);
    for(i=1;i<UI_TILES;i++)if(ui_changed[i>>3]&(1U<<(i&7))){REG32(0x040000d4)=(u32)ui_tiles[i];REG32(0x040000d8)=0x0600c000+i*32;REG32(0x040000dc)=0x84000008;}
    REG32(0x040000d4)=(u32)ui_screen;REG32(0x040000d8)=0x0600f800;REG32(0x040000dc)=0x84000200;
    upload_ui_objects();REG16(0x0400000a)=0x1f0c;/* BG1, 4bpp, charbase 3. */
    REG16(0x04000014)=0;REG16(0x04000016)=0;
    REG16(0x04000000)=0x0340|((portrait_count||cursor_visible)?0x1000:0);
    end=REG16(0x04000006);if(end<160)balanced_native_ui_metrics[6]++;
    (void)start;
}
static void native_ui_flip(void){
    unsigned i,row,col,used=1,free_at=1;
    if(portrait_count||cursor_visible)native_ui_objects_changed=1;
    prepare_portraits();prepare_cursor();
    memset(ui_lookup,0,2048);memset(ui_pending,0,UI_TILES/8);memset(ui_changed,0,UI_TILES/8);ui_pending[0]=1;
    /* Protect tiles referenced by unchanged cells before reclaiming slots.
     * A moved highlight therefore repacks only its two small row regions. */
    for(row=0;row<20;row++)for(col=0;col<30;col++)if(!(ui_dirty[row]&(1U<<col))){i=ui_screen[row*32+col];ui_pending[i>>3]|=1U<<(i&7);}
    for(i=1;i<UI_TILES;i++)if(ui_hashes[i])ui_insert(ui_hashes[i],i);
    for(row=0;row<20;row++)for(col=0;col<30;col++){
        u32 tile[8];unsigned hash,id;
        if(!(ui_dirty[row]&(1U<<col)))continue;
        audio_service();
        hash=ui_pack(row,col,tile);if(!hash){ui_screen[row*32+col]=0;continue;}
        id=ui_find(hash,tile);
        if(!id){
            while(free_at<UI_TILES&&(ui_pending[free_at>>3]&(1U<<(free_at&7))))free_at++;
            if(free_at>=UI_TILES){balanced_native_ui_metrics[4]++;native_ui_fallback();return;}
            id=free_at++;memcpy(ui_tiles[id],tile,32);ui_hashes[id]=hash;ui_insert(hash,id);
            /* The CPU copy can reclaim an old slot. Its VRAM texture is
             * replaced only at the same VBlank as the new screen map. */
            ui_changed[id>>3]|=1U<<(id&7);
            balanced_native_ui_metrics[2]++;
        }else balanced_native_ui_metrics[3]++;
        ui_pending[id>>3]|=1U<<(id&7);ui_screen[row*32+col]=id;
    }
    used=0;for(i=0;i<UI_TILES;i++)if(ui_pending[i>>3]&(1U<<(i&7)))used++;
    if(used>balanced_native_ui_metrics[5])balanced_native_ui_metrics[5]=used;
    native_ui_commit();memcpy(ui_visible,ui_pending,UI_TILES/8);
    native_ui_entering=0;
    memset(ui_dirty,0,80);
    balanced_native_ui_metrics[1]++;video_metrics[4]++;ui_ready=1;
}
