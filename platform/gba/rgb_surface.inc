/* Bitmap/UI surface only. Native maps keep their indexed BG/OBJ cache. */
#include "title_rgb555.h"
static u8 rgb_left[160],rgb_right[160];
#define rgb_secondary animation_fast_memory.draw.secondary
#define rgb_second_row rgb_secondary.bytes
static u8 rgb_xweight[240];
#define rgb_x0 animation_fast_memory.draw.x0
#define rgb_toned animation_fast_memory.draw.toned
static const u16*rgb_old_colors;
static u8 rgb_old_tone[4];
static int animation_blend_alpha=-1;
static unsigned animation_palette_alpha,animation_palette_color,animation_palette_power;
static int animation_cached_target=-1;
static unsigned rgb_bulk_fill;
static u32 animation_opaque_tiles[3];
void balanced_animation_mask(const u32*mask){unsigned i;for(i=0;i<3;i++)animation_opaque_tiles[i]=mask?mask[i]:0;}
static u8*animation_target_pixels;
void balanced_animation_scratch_reset(void){animation_cached_target=-1;}
void balanced_animation_palette_flash(int r,int g,int b,int power){animation_palette_color=clamp(r,0,31)|(clamp(g,0,31)<<5)|(clamp(b,0,31)<<10);animation_palette_power=clamp(power,0,31);animation_palette_alpha=animation_palette_power*256/31;rgb_old_colors=0;}
void balanced_animation_palette_reset(void){animation_palette_alpha=0;rgb_old_colors=0;}
volatile u32 balanced_rgb_metrics[8];/* flips, copied pixels, late chunks,
 * palette builds, native blits, scaled blits, source rows, native faces */
volatile u32 balanced_faces[13];

static void rgb_damage(int x,int y,int w,int h){int row;for(row=y;row<y+h;row++){if(!rgb_right[row]){rgb_left[row]=x;rgb_right[row]=x+w;}else{if(x<rgb_left[row])rgb_left[row]=x;if(x+w>rgb_right[row])rgb_right[row]=x+w;}}}
static void rgb_pixel(int x,int y,u16 color){if(x>=clip_left&&x<clip_right&&y>=clip_top&&y<clip_bottom){u16*dst=framebuffer+y*240+x;if(*dst!=color){*dst=color;rgb_damage(x,y,1,1);}}}
static void __attribute__((target("arm"),optimize("O3"),section(".iwram"),long_call,noinline)) rgb_fill(int left,int top,int right,int bottom,u16 color){
    int y;unsigned bulk=rgb_bulk_fill;if(left>=right||top>=bottom)return;if(!bulk)rgb_damage(left,top,right-left,bottom-top);
    u32 packed=color|((u32)color<<16);
    for(y=top;y<bottom;y++){
        u16*dst=framebuffer+y*240+left;unsigned n=right-left;if(!bulk&&!(y&3))audio_service();
        if((unsigned)dst&2){*dst++=color;n--;}
        u32*words=(u32*)dst;
        while(n>=8){words[0]=packed;words[1]=packed;words[2]=packed;words[3]=packed;words+=4;n-=8;}
        while(n>=2){*words++=packed;n-=2;}if(n)*(u16*)words=color;
    }
}
static void rgb_clear(int color){ui_ready=0;portrait_count=cursor_visible=0;balanced_faces[0]=0;framebuffer_revision++;rgb_fill(clip_left,clip_top,clip_right,clip_bottom,game_palette[color&255]);}
static void rgb_box(int x,int y,int w,int h,int color){framebuffer_revision++;rgb_fill(clamp(x,clip_left,clip_right),clamp(y,clip_top,clip_bottom),clamp(x+w,clip_left,clip_right),clamp(y+h,clip_top,clip_bottom),game_palette[color&255]);}
static const u16*rgb_colors(const Image*im,const u8*tone){const u16*src=im->colors?im->colors:game_palette;unsigned i,count=im->color_count?im->color_count:256;
    if(!tone||(tone[0]==100&&tone[1]==100&&tone[2]==100&&tone[3]==100))return src;
    if(rgb_old_colors==src&&rgb_old_tone[0]==tone[0]&&rgb_old_tone[1]==tone[1]&&rgb_old_tone[2]==tone[2]&&rgb_old_tone[3]==tone[3])return rgb_toned;
    for(i=0;i<count;i++){unsigned c=src[i];int r=c&31,g=(c>>5)&31,b=c>>10,gray=(r*30+g*59+b*11)/100;
        rgb_toned[i]=clamp((gray+(r-gray)*tone[3]/100)*tone[0]/100,0,31)|(clamp((gray+(g-gray)*tone[3]/100)*tone[1]/100,0,31)<<5)|(clamp((gray+(b-gray)*tone[3]/100)*tone[2]/100,0,31)<<10);
    }rgb_old_colors=src;for(i=0;i<4;i++)rgb_old_tone[i]=tone[i];balanced_rgb_metrics[3]++;return rgb_toned;
}
static inline __attribute__((always_inline)) u16 rgb_mix(u16 color,u16 old,unsigned alpha){
    unsigned inv=256-alpha,rb=(((color&31)|((color&0x7c00)<<6))*alpha+((old&31)|((old&0x7c00)<<6))*inv+0x00800080U);
    unsigned g=((color&0x03e0)*alpha+(old&0x03e0)*inv+0x1000U)>>8;
    return ((rb>>8)&31)|((rb>>14)&0x7c00)|(g&0x03e0);
}
static void rgb_image(const Image*im,int id,int x,int y,int sx,int sy,int sw,int sh,int w,int h,int transparent,int opacity,const u8*tone){
    const u16*colors;int left,right,top,bottom,xx,yy;unsigned alpha;
    if(!im||w<=0||h<=0||sw<=0||sh<=0||opacity>=100)return;
    if(transparent&&(im->transparent&128))return;
    left=clamp(x,clip_left,clip_right);right=clamp(x+w,clip_left,clip_right);top=clamp(y,clip_top,clip_bottom);bottom=clamp(y+h,clip_top,clip_bottom);if(left>=right||top>=bottom)return;
    rgb_damage(left,top,right-left,bottom-top);framebuffer_revision++;video_metrics[0]++;video_metrics[1]+=(right-left)*(bottom-top);
    if(id==IMG_TITLE&&x==0&&y==0&&sx==0&&sy==0&&sw==240&&sh==160&&w==240&&h==160&&!transparent&&!opacity&&(!tone||(tone[0]==100&&tone[1]==100&&tone[2]==100&&tone[3]==100))){for(yy=top;yy<bottom;yy++){if(!(yy&3))audio_service();memcpy(framebuffer+yy*240+left,balanced_title_rgb555+yy*240+left,(right-left)*2);}return;}
    colors=rgb_colors(im,tone);alpha=(100-clamp(opacity,0,100))*256/100;
    if(im->encoding==7&&sx>=0&&sy>=0&&sx+sw<=im->width&&sy+sh<=im->height){unsigned index=im->pixels[0];u16 color=colors[index];if(transparent&&!index)return;
        if(alpha==256)rgb_fill(left,top,right,bottom,color);else for(yy=top;yy<bottom;yy++){u16*dst=framebuffer+yy*240+left;if(!(yy&3))audio_service();for(xx=left;xx<right;xx++,dst++)*dst=rgb_mix(color,*dst,alpha);}return;
    }
    if(w==sw&&h==sh){balanced_rgb_metrics[4]++;
        if(sx+left-x<0)left=x-sx;if(sx+right-x>im->width)right=x+im->width-sx;
        if(sy+top-y<0)top=y-sy;if(sy+bottom-y>im->height)bottom=y+im->height-sy;
        if(left>=right||top>=bottom)return;
        if(im->encoding==6&&alpha==256&&(!im->stored_width||(im->stored_width==im->width&&im->stored_height==im->height))){
            int tx,ty,row,col,source_left=sx+left-x,source_top=sy+top-y;
            int source_right=sx+right-x,source_bottom=sy+bottom-y;
            /* Decode each tile once, including partially clipped edge tiles.
             * This also serves narrow exposed strips between modal windows. */
            for(ty=source_top/8;ty<=(source_bottom-1)/8;ty++)for(tx=source_left/8;tx<=(source_right-1)/8;tx++){
                int l=source_left>tx*8?source_left:tx*8,r=source_right<(tx+1)*8?source_right:(tx+1)*8;
                int t=source_top>ty*8?source_top:ty*8,b=source_bottom<(ty+1)*8?source_bottom:(ty+1)*8;
                const u8*tile;audio_service();tile=image_storage_tile(im,tx,ty);if(!tile)return;
                for(row=t;row<b;row++){u16*dst=framebuffer+(y+row-sy)*240+x+l-sx;const u8*src=tile+(row-ty*8)*8+l-tx*8;
                    for(col=l;col<r;col++){unsigned c=*src++;if(c||!transparent)*dst=colors[c];dst++;}}
            }balanced_rgb_metrics[6]+=bottom-top;return;
        }
        for(yy=top;yy<bottom;yy++){u16*dst=framebuffer+yy*240+left;int length=right-left;
            if(!(yy&1))audio_service();if(!decode_image_storage_span(im,sy+yy-y,sx+left-x,length,image_line,sizeof(image_line)))return;balanced_rgb_metrics[6]++;
            if(!transparent&&alpha==256){for(xx=0;xx<length;xx++)dst[xx]=colors[image_line[xx]];}
            else for(xx=0;xx<length;xx++){unsigned index=image_line[xx];if(!index&&transparent)continue;dst[xx]=alpha==256?colors[index]:rgb_mix(colors[index],dst[xx],alpha);}
        }return;
    }
    /* Bilinear sampling has precomputed horizontal weights and no division
     * in its pixel loop. Alpha is premultiplied, preserving transparent edges. */
    animation_blend_alpha=-1;
    {int span_left=im->width,span_right=-1,row_keys[2]={-1,-1};u8*row_data[2]={image_line,rgb_second_row};
    balanced_rgb_metrics[5]++;
    for(xx=left;xx<right;xx++){int nearest=sx+(xx-x)*sw/w,fx,x0;
        if(nearest<0||nearest>=im->width){rgb_x0[xx-left]=65535;continue;}
        fx=((2*(xx-x)+1)*sw*128/w)-128+sx*256;x0=fx>>8;
        rgb_x0[xx-left]=clamp(x0,0,im->width-1);rgb_xweight[xx-left]=x0<0||x0>=im->width-1?0:fx&255;
        if(rgb_x0[xx-left]<span_left)span_left=rgb_x0[xx-left];
        x0=rgb_x0[xx-left]+(rgb_xweight[xx-left]!=0);if(x0>span_right)span_right=x0;
    }
    if(span_right<span_left)return;
    for(yy=top;yy<bottom;yy++){int fy=((2*(yy-y)+1)*sh*128/h)-128+sy*256,y0=fy>>8,y1,wy=fy&255;
        int nearest=sy+(yy-y)*sh/h,a,b;u8*row0,*row1;
        if(nearest<0||nearest>=im->height)continue;
        audio_service();if(y0<0){y0=0;wy=0;}if(y0>=im->height-1){y0=im->height-1;wy=0;}y1=y0+(wy!=0);
        a=row_keys[0]==y0?0:row_keys[1]==y0?1:-1;
        if(a<0){a=row_keys[0]==y1?1:0;if(!decode_image_storage_span(im,y0,span_left,span_right-span_left+1,row_data[a],1024))return;row_keys[a]=y0;balanced_rgb_metrics[6]++;}
        b=row_keys[0]==y1?0:row_keys[1]==y1?1:-1;
        if(b<0){b=1-a;if(!decode_image_storage_span(im,y1,span_left,span_right-span_left+1,row_data[b],1024))return;row_keys[b]=y1;balanced_rgb_metrics[6]++;}
        row0=row_data[a];row1=row_data[b];
        for(xx=left;xx<right;xx++){unsigned at=xx-left,x0=rgb_x0[at],wx=rgb_xweight[at],x1,indices[4],weights[4],r=0,g=0,b=0,sum=0,k;u16*dst=framebuffer+yy*240+xx;
            if(!(xx&63))audio_service();if(x0==65535)continue;x0-=span_left;x1=x0+(wx!=0);
            indices[0]=row0[x0];indices[1]=row0[x1];indices[2]=row1[x0];indices[3]=row1[x1];weights[0]=(256-wx)*(256-wy);weights[1]=wx*(256-wy);weights[2]=(256-wx)*wy;weights[3]=wx*wy;
            for(k=0;k<4;k++)if(!transparent||indices[k]){u16 c=colors[indices[k]];unsigned weight=weights[k];r+=(c&31)*weight;g+=((c>>5)&31)*weight;b+=(c>>10)*weight;sum+=weight;}
            if(sum==65536&&alpha==256)*dst=(r>>16)|((g>>16)<<5)|((b>>16)<<10);
            else if(sum){unsigned inv=16777216U-sum*alpha,old=*dst;*dst=((r*alpha+(old&31)*inv+8388608U)>>24)|(((g*alpha+((old>>5)&31)*inv+8388608U)>>24)<<5)|(((b*alpha+(old>>10)*inv+8388608U)>>24)<<10);}
        }
    }
    }
}
static void rgb_picture(int id,int x,int y,int sx,int sy,int sw,int sh,int w,int h,int transparent,int opacity,const u8*tone){
    if(id>=0)rgb_image(images+id,id,x,y,sx,sy,sw,sh,w,h,transparent,opacity,tone);
}
/* One shared 32x32 channel table gives the exact rounded RGB555 blend.
 * It borrows the bilinear row workspace only while drawing battle cells. */
static void animation_blend_table(unsigned alpha){
    unsigned source,dest,inv=256-alpha;if(animation_blend_alpha==(int)alpha)return;
    for(source=0;source<32;source++){unsigned value=source*alpha+128;for(dest=0;dest<32;dest++){rgb_second_row[source*32+dest]=value>>8;value+=inv;}}
    animation_blend_alpha=alpha;
}
static void __attribute__((target("arm"),optimize("O3"),section(".iwram"),long_call,noinline)) animation_span(u16*dst,const u8*src,const u16*xs,const u16*colors,int n,unsigned alpha){
    int i;if(alpha==256){for(i=0;i<n;i++){unsigned c=src[xs[i]];if(c)dst[i]=colors[c];}}
    else if(alpha==128){for(i=0;i<n;i++){unsigned c=src[xs[i]];if(c){unsigned color=colors[c],old=dst[i],different=color^old;
        dst[i]=(color&old)+((different&0x7bde)>>1)+(different&0x0421);
    }}}
    else for(i=0;i<n;i++){unsigned c=src[xs[i]];if(c){unsigned color=colors[c],old=dst[i];
        dst[i]=rgb_second_row[((color&31)<<5)|(old&31)]|(rgb_second_row[(color&0x3e0)|((old>>5)&31)]<<5)|(rgb_second_row[((color>>5)&0x3e0)|((old>>10)&31)]<<10);
    }}
}
/* Enlarged opaque pixels form long constant-color runs. Fill those runs with
 * aligned word stores instead of looking up the same source texel again for
 * every destination pixel. Zero remains transparent, including black art. */
static void __attribute__((target("arm"),optimize("O3"),noinline)) animation_opaque_runs(u16*dst,const u8*src,const u16*ends,const u16*colors,int count){
 int i=0,at=0;
 while(i<count){unsigned index=src[i];int end=i+1,n;u16*out;
  while(end<count&&src[end]==index)end++;
  n=ends[end-1]-at;out=dst+at;at=ends[end-1];i=end;if(!index||!n)continue;
  {u16 color=colors[index];u32 word=color|((u32)color<<16);
   if((unsigned long)out&2){*out++=color;n--;}
   while(n>=4){*(u32*)out=word;*(u32*)(out+2)=word;out+=4;n-=4;}
   if(n>=2){*(u32*)out=word;out+=2;n-=2;}if(n)*out=color;
  }
 }
}
static void __attribute__((target("arm"),optimize("O3"),section(".iwram"),long_call,noinline)) animation_restore_indexed(u16*dst,const u8*src,const u16*colors,unsigned n){
 if((unsigned long)dst&2){*dst++=colors[*src++];n--;}
 while(n>=2){*(u32*)dst=colors[src[0]]|((u32)colors[src[1]]<<16);dst+=2;src+=2;n-=2;}
 if(n)*dst=colors[*src];
}
/* Pixel-art effects use one original source sample per GBA pixel. Unlike
 * illustrations they do not need four-sample filtering on every frame. */
void balanced_animation_cell(const Image*im,int x,int y,int w,int h,int opacity,const u8*tone){
    int left=clamp(x,clip_left,clip_right),right=clamp(x+w,clip_left,clip_right),top=clamp(y,clip_top,clip_bottom),bottom=clamp(y+h,clip_top,clip_bottom),xx,yy,first,last,old_y=-1;
    const u16*colors;unsigned alpha,sx,xrem,xstep,xsub,sy,yrem,ystep,ysub,numerator;int runs;
    if(!bitmap_direct||w<=0||h<=0||opacity>=100||left>=right||top>=bottom)return;
    colors=rgb_colors(im,tone);
    if(colors!=rgb_toned){unsigned k,count=im->color_count?im->color_count:256;
        if(rgb_old_colors!=colors||rgb_old_tone[0]!=100||rgb_old_tone[1]!=100||rgb_old_tone[2]!=100||rgb_old_tone[3]!=100){
            memcpy(rgb_toned,colors,count*2);rgb_old_colors=colors;for(k=0;k<4;k++)rgb_old_tone[k]=100;
        }colors=rgb_toned;
    }
    if(animation_palette_alpha){unsigned k,count=im->color_count?im->color_count:256;for(k=0;k<count;k++)rgb_toned[k]=rgb_mix(animation_palette_color,colors[k],animation_palette_alpha);colors=rgb_toned;rgb_old_colors=0;}
    alpha=(100-clamp(opacity,0,100))*256/100;if(alpha!=128&&alpha!=256)animation_blend_table(alpha);
    numerator=(left-x)*im->width;sx=numerator/w;xrem=numerator%w;xstep=im->width/w;xsub=im->width%w;
    for(xx=left;xx<right;xx++){rgb_x0[xx-left]=sx;sx+=xstep;xrem+=xsub;if(xrem>=(unsigned)w){xrem-=w;sx++;}}
    first=rgb_x0[0];last=rgb_x0[right-left-1];for(xx=0;xx<right-left;xx++)rgb_x0[xx]-=first;rgb_damage(left,top,right-left,bottom-top);
    runs=alpha==256&&w>=im->width&&last-first<512;
    if(runs){animation_blend_alpha=-1;for(xx=first;xx<=last;xx++)rgb_secondary.ends[xx-first]=clamp(((xx+1)*w+im->width-1)/im->width+x-left,0,right-left);}
    numerator=(top-y)*im->height;sy=numerator/h;yrem=numerator%h;ystep=im->height/h;ysub=im->height%h;
    for(yy=top;yy<bottom;yy++){u16*dst=framebuffer+yy*240+left;audio_service();
        if((int)sy!=old_y){if(!decode_image_storage_span(im,sy,first,last-first+1,image_line,sizeof(image_line)))return;old_y=sy;}
        if(runs)animation_opaque_runs(dst,image_line,rgb_secondary.ends,colors,last-first+1);else animation_span(dst,image_line,rgb_x0,colors,right-left,alpha);sy+=ystep;yrem+=ysub;if(yrem>=(unsigned)h){yrem-=h;sy++;}
    }
}
/* Constant source flashes need only the two destination multiplications.
 * Keep this hot loop in fast RAM; the complete color operation is unchanged. */
static void __attribute__((target("arm"),optimize("O3"),section(".iwram"),long_call,noinline)) animation_flash_span(u16*dst,int n,unsigned source_rb,unsigned source_g,unsigned inv){
    int i;for(i=0;i<n;i++){unsigned old=dst[i],rb=source_rb+((old&31)|((old&0x7c00)<<6))*inv,g=source_g+((old>>5)&31)*inv;
        dst[i]=((rb>>8)&31)|((rb>>14)&0x7c00)|((g>>3)&0x03e0);
    }
}
void __attribute__((target("arm"),optimize("O3"))) balanced_animation_flash(int x,int y,int w,int h,int r,int g,int b,int power){
    int yy,left=clamp(x,0,240),right=clamp(x+w,0,240),top=clamp(y,0,160),bottom=clamp(y+h,0,160);
    u16 color=clamp(r,0,31)|(clamp(g,0,31)<<5)|(clamp(b,0,31)<<10);unsigned alpha=clamp(power,0,31)*256/31;
    if(!bitmap_direct||!alpha||left>=right||top>=bottom)return;rgb_damage(left,top,right-left,bottom-top);
    if(alpha==256){rgb_fill(left,top,right,bottom,color);return;}
    {unsigned rb=((color&31)|((color&0x7c00)<<6))*alpha+0x00800080U,g=((color>>5)&31)*alpha+128,inv=256-alpha;
     for(yy=top;yy<bottom;yy++){if(!(yy&3))audio_service();animation_flash_span(framebuffer+yy*240+left,right-left,rb,g,inv);}
    }
}
void balanced_animation_target_flash(int id,int x,int y,int w,int h,int r,int g,int b,int power){
    {unsigned row,col,covered=1;int left=clamp(x,0,240),right=clamp(x+w,0,240),top=clamp(y,0,160),bottom=clamp(y+h,0,160);
     if(left<right&&top<bottom){for(row=top/16;row<=(unsigned)(bottom-1)/16&&covered;row++)for(col=left/32;col<=(unsigned)(right-1)/32;col++){unsigned key=row*8+col;if(!(animation_opaque_tiles[key>>5]&(1U<<(key&31)))){covered=0;break;}}if(covered)return;}
    }
    if(id<0){
        if(animation_palette_alpha){unsigned color=animation_palette_color,alpha=animation_palette_alpha,screen_power=animation_palette_power;
            animation_palette_alpha=0;
            if(!balanced_animation_background_restore(x,y,w,h)){video_clip(x,y,w,h);draw_battle();video_clip(0,0,240,160);}
            balanced_animation_flash(x,y,w,h,r,g,b,power);
            balanced_animation_flash(x,y,w,h,color&31,(color>>5)&31,color>>10,screen_power);
            animation_palette_color=color;animation_palette_alpha=alpha;animation_palette_power=screen_power;
        }else balanced_animation_flash(x,y,w,h,r,g,b,power);
        return;
    }
    {Image im=images[id];unsigned i,alpha=clamp(power,0,31)*256/31;u16 color=clamp(r,0,31)|(clamp(g,0,31)<<5)|(clamp(b,0,31)<<10);
     for(i=0;i<im.color_count;i++){u16 c=rgb_mix(color,im.colors[i],alpha);rgb_toned[i]=animation_palette_alpha?rgb_mix(animation_palette_color,c,animation_palette_alpha):c;}
     if(w==im.width&&h==im.height&&(!im.stored_width||im.stored_width==im.width)&&(!im.stored_height||im.stored_height==im.height)&&(unsigned)w*h<=8192){
        int row,left=clamp(x,clip_left,clip_right),right=clamp(x+w,clip_left,clip_right),top=clamp(y,clip_top,clip_bottom),bottom=clamp(y+h,clip_top,clip_bottom);rgb_old_colors=0;
        if(left>=right||top>=bottom)return;
        if(animation_cached_target!=id){animation_target_pixels=balanced_animation_workspace();
            for(row=0;row<h;row++){audio_service();if(!decode_image_storage_span(&im,row,0,w,animation_target_pixels+row*w,8192-row*w))return;}
            animation_cached_target=id;
        }
        for(i=0;i<(unsigned)(right-left);i++)rgb_x0[i]=i;
        for(row=top;row<bottom;row++){if(!(row&3))audio_service();animation_span(framebuffer+row*240+left,animation_target_pixels+(row-y)*w+left-x,rgb_x0,rgb_toned,right-left,256);}
        rgb_damage(left,top,right-left,bottom-top);framebuffer_revision++;return;
     }
     im.colors=rgb_toned;rgb_old_colors=0;rgb_image(&im,-1,x,y,0,0,im.width,im.height,w,h,1,0,0);rgb_old_colors=0;
    }
}
void __attribute__((target("arm"),optimize("O3"))) balanced_animation_rectangles(const u8*rectangles,unsigned count,const u16*colors,unsigned color_count,const u8*bounds){
 unsigned i;int full=!clip_left&&!clip_top&&clip_right==240&&clip_bottom==160;if(!bitmap_direct)return;rgb_old_colors=0;
 for(i=0;i<color_count;i++)rgb_toned[i]=animation_palette_alpha?rgb_mix(animation_palette_color,colors[i],animation_palette_alpha):colors[i];
 if(count&32768){
  unsigned y=bounds[1],width=bounds[2],left=clamp(bounds[0],clip_left,clip_right),right=clamp(bounds[0]+width,clip_left,clip_right);count&=32767;
  while(count){unsigned bytes=rectangles[0]|rectangles[1]<<8,n=rectangles[2]|rectangles[3]<<8,raw=rectangles[4]|rectangles[5]<<8,row;const u8*data=image_line;
   if(!n||n>count||raw>sizeof(image_line)||image_unpack_block(rectangles+6,bytes,image_line,sizeof(image_line))!=(int)raw){fault(9034);return;}
   for(row=0;row<n;row++,y++){unsigned spans=*data++;audio_service();while(spans--){unsigned x=bounds[0]+data[0],length=data[1];data+=2;
    if(y>=(unsigned)clip_top&&y<(unsigned)clip_bottom){int l=clamp(x,left,right),r=clamp(x+length,left,right);if(l<r)animation_restore_indexed(framebuffer+y*240+l,data+l-x,rgb_toned,r-l);}data+=length;
   }}
   if(data!=image_line+raw){fault(9034);return;}count-=n;rectangles+=6+bytes;
  }
  {int top=clamp(bounds[1],clip_top,clip_bottom),bottom=clamp(bounds[1]+bounds[3],clip_top,clip_bottom);if(left<right&&top<bottom)rgb_damage(left,top,right-left,bottom-top);}
  framebuffer_revision++;return;
 }
 rgb_bulk_fill=1;
 while(count){unsigned bytes=rectangles[0]|rectangles[1]<<8,n=rectangles[2]|rectangles[3]<<8;const u8*data=image_line;
  if(!n||n>200||n>count||image_unpack_block(rectangles+4,bytes,image_line,sizeof(image_line))!=(int)(n*5)){rgb_bulk_fill=0;fault(9034);return;}
  for(i=0;i<n;i++,data+=5){int x=data[0],y=data[1];if(!(i&31))audio_service();if(full)rgb_fill(x,y,x+data[2],y+data[3],rgb_toned[data[4]]);else rgb_fill(clamp(x,clip_left,clip_right),clamp(y,clip_top,clip_bottom),clamp(x+data[2],clip_left,clip_right),clamp(y+data[3],clip_top,clip_bottom),rgb_toned[data[4]]);}
  count-=n;rectangles+=4+bytes;
 }
 rgb_bulk_fill=0;
 {int left=clamp(bounds[0],clip_left,clip_right),right=clamp(bounds[0]+bounds[2],clip_left,clip_right),top=clamp(bounds[1],clip_top,clip_bottom),bottom=clamp(bounds[1]+bounds[3],clip_top,clip_bottom);if(left<right&&top<bottom)rgb_damage(left,top,right-left,bottom-top);}
 framebuffer_revision++;
}
static void rgb_portrait(int id,int x,int y){const u32*h=(const u32*)original_portraits_start;const PortraitRecord*r=(const PortraitRecord*)(original_portraits_start+h[2]);unsigned i,n=balanced_faces[0];int xx,yy;
    if(h[0]!=0x43414652)return;for(i=0;i<h[1];i++)if(r[i].image==id){const u16*colors=(const u16*)(original_portraits_start+h[3])+r[i].sheet*256;const u8*data=image_portrait_pixels(original_portraits_start+h[4]+r[i].tiles);if(!data)return;
        if(n<4){balanced_faces[1+n*3]=id;balanced_faces[2+n*3]=x;balanced_faces[3+n*3]=y;balanced_faces[0]=n+1;}
        for(yy=0;yy<48;yy++){if(!(yy&3))audio_service();for(xx=0;xx<48;xx++){int tile=(yy/16*3+xx/16)*4+(yy%16/8)*2+xx%16/8,at=tile*64+yy%8*8+xx%8,c=data[at];if(c)rgb_pixel(x+xx,y+yy,colors[c]);}}balanced_rgb_metrics[7]++;return;
    }
}
#include "animation_background.inc"
/* Mode 3 leaves 21 KiB beyond the displayed bitmap. A 144x72 RGB555
 * battle patch fits there without touching the cursor tile at 0x17f00.
 * Maps/portraits own this region again after leaving battle; the dialog
 * owner invalidates this cache whenever another scene is drawn. */
static int battle_patch_tiled;
int balanced_battle_cache_store(void){
    int y;battle_patch_tiled=0;if(!bitmap_direct)return 0;
    /* The animation art pool also contains this complete modal underlay.
     * Share its ownership rather than overwriting it with a second cache. */
    if(animation_background_valid&&animation_background_tiled&&animation_background_epoch==balanced_surface_epoch&&animation_art_stamp==battle_art_stamp()){animation_cache_reuse_debug[3]++;battle_patch_tiled=1;return 1;}
    animation_background_valid=0;
    for(y=24;y<96;y++){if(!(y&3))audio_service();memcpy((void*)(0x06012c00+(y-24)*288),framebuffer+y*240+96,288);}
    cached_portrait_sheet=-1;for(y=0;y<7;y++)cached_portraits[y]=-1;
    return 1;
}
void balanced_battle_cache_restore(int x,int y,int width,int height){
    int row;ui_ready=0;framebuffer_revision++;rgb_damage(x,y,width,height);
    if(battle_patch_tiled){animation_codec_load(2);if(!animation_restore_tiles(x,y,width,height)){animation_background_valid=0;video_clip(x,y,width,height);draw_battle();}return;}
    for(row=y;row<y+height;row++){if(!(row&3))audio_service();memcpy(framebuffer+row*240+x,(const void*)(0x06012c00+(row-24)*288+(x-96)*2),width*2);}
}
static void rgb_trim_to_vram(void){
    const u32*source=(const u32*)framebuffer;volatile const u32*shown=(volatile const u32*)0x06000000;unsigned row;
    for(row=0;row<160;row++)if(rgb_right[row]){
        unsigned left=row*120+rgb_left[row]/2,right=row*120+(rgb_right[row]+1)/2;
        if(!(row&3))audio_service();
        while(left<right&&source[left]==shown[left])left++;
        while(left<right&&source[right-1]==shown[right-1])right--;
        if(left==right)rgb_right[row]=0;
        else{rgb_left[row]=(left-row*120)*2;rgb_right[row]=(right-row*120)*2;}
    }
}
static void __attribute__((section(".iwram"),long_call,noinline)) rgb_flip(void){unsigned row=0,start,copy_budget=0;int transition=(REG16(0x04000000)&7)!=3,shade=current_brightness;audio_service();prepare_portraits();prepare_cursor();
    if(!transition)rgb_trim_to_vram();
    for(row=0;row<160&&!rgb_right[row];row++){}if(row==160){video_overlays_present();return;}
    for(;;){unsigned line=REG16(0x04000006);if(line>=160&&line<=170){start=line;break;}if(line<152||line>170)audio_service();}
    (void)start;if(transition)video_brightness(-16);upload_ui_objects();REG16(0x04000000)=0x0443|(cursor_visible?0x1000:0);map_active=0;map_objects_valid=0;display_scene=0;
    while(row<160){unsigned at,limit,next=row+1;if(!rgb_right[row]){row++;continue;}
        at=row*120+rgb_left[row]/2;limit=row*120+(rgb_right[row]+1)/2;
        if(!rgb_left[row]&&rgb_right[row]==240){while(next<160&&!rgb_left[next]&&rgb_right[next]==240)next++;limit=next*120;}
        while(at<limit){unsigned words=limit-at,line=REG16(0x04000006);if(words>256)words=256;
            if(!transition&&shade>-16&&line<160&&at/120<=line+1)balanced_rgb_metrics[2]++;
            REG32(0x040000d4)=(u32)framebuffer+at*4;REG32(0x040000d8)=0x06000000+at*4;REG32(0x040000dc)=0x84000000|words;at+=words;balanced_rgb_metrics[1]+=words*2;copy_budget+=words;
            /* Visible DMA commits have a prefilled 125 ms audio ring. Do not
             * start a synthesis block in their raster-critical interval.
             * Hidden scene cuts can refill at bounded, alignment-independent
             * word intervals while their complete new picture is prepared. */
            if((transition||shade<=-16)&&copy_budget>=256){audio_service();copy_budget=0;}
        }while(row<next)rgb_right[row++]=0;
    }if(transition){wait_commit_window();video_brightness(shade);}balanced_rgb_metrics[0]++;video_metrics[4]++;ui_ready=1;
}
