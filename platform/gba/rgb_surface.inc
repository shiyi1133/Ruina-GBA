/* Bitmap/UI surface only. Native maps keep their indexed BG/OBJ cache. */
#include "title_rgb555.h"
static u8 rgb_left[160],rgb_right[160];
static u8 rgb_second_row[1024],rgb_xweight[240];
static u16 rgb_x0[240],rgb_toned[256];
static const u16*rgb_old_colors;
static u8 rgb_old_tone[4];
volatile u32 balanced_rgb_metrics[8];/* flips, copied pixels, late chunks,
 * palette builds, native blits, scaled blits, source rows, native faces */
volatile u32 balanced_faces[13];

static void rgb_damage(int x,int y,int w,int h){int row;for(row=y;row<y+h;row++){if(!rgb_right[row]){rgb_left[row]=x;rgb_right[row]=x+w;}else{if(x<rgb_left[row])rgb_left[row]=x;if(x+w>rgb_right[row])rgb_right[row]=x+w;}}}
static void rgb_pixel(int x,int y,u16 color){if(x>=clip_left&&x<clip_right&&y>=clip_top&&y<clip_bottom){u16*dst=framebuffer+y*240+x;if(*dst!=color){*dst=color;rgb_damage(x,y,1,1);}}}
static void __attribute__((section(".iwram"),long_call,noinline)) rgb_fill(int left,int top,int right,int bottom,u16 color){
    int y;if(left>=right||top>=bottom)return;rgb_damage(left,top,right-left,bottom-top);
    u32 packed=color|((u32)color<<16);
    for(y=top;y<bottom;y++){
        u16*dst=framebuffer+y*240+left;unsigned n=right-left;if(!(y&3))audio_service();
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
static u16 rgb_mix(u16 color,u16 old,unsigned alpha){unsigned inv=256-alpha;return(((color&31)*alpha+(old&31)*inv+128)>>8)|(((((color>>5)&31)*alpha+((old>>5)&31)*inv+128)>>8)<<5)|((((color>>10)*alpha+(old>>10)*inv+128)>>8)<<10);}
static void rgb_picture(int id,int x,int y,int sx,int sy,int sw,int sh,int w,int h,int transparent,int opacity,const u8*tone){
    const Image*im;const u16*colors;int left,right,top,bottom,xx,yy;unsigned alpha;
    if(id<0||w<=0||h<=0||sw<=0||sh<=0||opacity>=100)return;im=images+id;
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
static void rgb_portrait(int id,int x,int y){const u32*h=(const u32*)original_portraits_start;const PortraitRecord*r=(const PortraitRecord*)(original_portraits_start+h[2]);unsigned i,n=balanced_faces[0];int xx,yy;
    if(h[0]!=0x43414652)return;for(i=0;i<h[1];i++)if(r[i].image==id){const u16*colors=(const u16*)(original_portraits_start+h[3])+r[i].sheet*256;const u8*data=original_portraits_start+h[4]+r[i].tiles;
        if(n<4){balanced_faces[1+n*3]=id;balanced_faces[2+n*3]=x;balanced_faces[3+n*3]=y;balanced_faces[0]=n+1;}
        for(yy=0;yy<48;yy++){if(!(yy&3))audio_service();for(xx=0;xx<48;xx++){int tile=(yy/16*3+xx/16)*4+(yy%16/8)*2+xx%16/8,at=tile*64+yy%8*8+xx%8,c=data[at];if(c)rgb_pixel(x+xx,y+yy,colors[c]);}}balanced_rgb_metrics[7]++;return;
    }
}
/* Mode 3 leaves 21 KiB beyond the displayed bitmap. A 144x72 RGB555
 * battle patch fits there without touching the cursor tile at 0x17f00.
 * Maps/portraits own this region again after leaving battle; the dialog
 * owner invalidates this cache whenever another scene is drawn. */
int balanced_battle_cache_store(void){
    int y;if(!bitmap_direct)return 0;
    for(y=24;y<96;y++){if(!(y&3))audio_service();memcpy((void*)(0x06012c00+(y-24)*288),framebuffer+y*240+96,288);}
    cached_portrait_sheet=-1;for(y=0;y<7;y++)cached_portraits[y]=-1;
    return 1;
}
void balanced_battle_cache_restore(int x,int y,int width,int height){
    int row;ui_ready=0;framebuffer_revision++;rgb_damage(x,y,width,height);
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
