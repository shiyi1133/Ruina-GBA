#include "types.h"
static u8 block_pixels[4096] __attribute__((aligned(4)));
static const u8*last_pixels;
static int last_block=-1;
static const u8*tile_keys[64];
static int tile_mode;
void *image_decode_scratch(void){tile_mode=0;last_pixels=0;last_block=-1;return block_pixels;}
static u8 stored_row[1024];
static int lz4(const u8*in,unsigned size,u8*out,unsigned capacity){unsigned at=0,x=0;while(at<size){unsigned token=in[at++],n=token>>4,m=(token&15)+4,i,off;if(n==15){unsigned v;do{if(at>=size)return 0;v=in[at++];n+=v;}while(v==255);}if(n>size-at||n>capacity-x)return 0;for(i=0;i<n;i++)out[x++]=in[at++];if(at==size)return x;if(at+2>size)return 0;off=in[at]|in[at+1]<<8;at+=2;if(!off||off>x)return 0;if((token&15)==15){unsigned v;do{if(at>=size)return 0;v=in[at++];m+=v;}while(v==255);}if(m>capacity-x)return 0;for(i=0;i<m;i++){out[x]=out[x-off];x++;}}return x;}
int image_unpack_block(const u8*in,unsigned size,u8*out,unsigned capacity){return lz4(in,size,out,capacity);}
int resource_image(int kind,LcfSpan name){unsigned h=2166136261U,i;if(!name.size)return -1;for(i=0;i<name.size;i++){h^=name.data[i];h*=16777619U;}for(i=0;i<resource_image_count;i++)if(resource_images[i].kind==kind&&resource_images[i].hash==h)return resource_images[i].image;return -1;}
static void legacy_blocks(void){if(tile_mode){tile_mode=0;last_pixels=0;last_block=-1;}}
const u8*image_portrait_pixels(const u8*packed){
 unsigned size=packed[0]|packed[1]<<8;legacy_blocks();
 if(last_pixels!=packed||last_block!=-2){last_pixels=0;last_block=-1;
  if(lz4(packed+2,size,block_pixels,2304)!=2304)return 0;last_pixels=packed;last_block=-2;
 }return block_pixels;
}
/* Borrow a whole decoded 8x8 tile until the next decoder call. Native tiled
 * backgrounds can then visit each source tile once, rather than requesting
 * eight separate row spans that collide in the small direct-mapped cache. */
const u8*image_storage_tile(const Image*im,int x,int y){
 unsigned width=im->stored_width?im->stored_width:im->width,height=im->stored_height?im->stored_height:im->height,cols=(width+7)/8,packed,size;
 const u8*source;
 if(im->encoding!=6||!im->rows||x<0||y<0||(unsigned)x>=cols||(unsigned)y>=(height+7)/8)return 0;
 if(!tile_mode){unsigned i;for(i=0;i<64;i++)tile_keys[i]=0;tile_mode=1;last_pixels=0;last_block=-1;}
 packed=im->rows[(unsigned)y*cols+(unsigned)x];size=packed>>24;source=im->pixels+(packed&0xffffffU);
 if(size){unsigned slot=(((unsigned long)source>>2)^((unsigned long)source>>11))&63;u8*data=block_pixels+slot*64;
  if(tile_keys[slot]!=source){if(lz4(source,size,data,64)!=64)return 0;tile_keys[slot]=source;}
  source=data;
 }return source;
}
static int tiled_span(const Image*im,unsigned y,unsigned x,unsigned length,u8*row){
 unsigned width=im->stored_width?im->stored_width:im->width,cols=(width+7)/8,done=0;
 if(!im->rows)return 0;
 if(!tile_mode){unsigned i;for(i=0;i<64;i++)tile_keys[i]=0;tile_mode=1;last_pixels=0;last_block=-1;}
 while(done<length){
  unsigned xx=x+done,packed=im->rows[(y/8)*cols+xx/8],size=packed>>24,count=8-(xx&7),i;
  const u8*src=im->pixels+(packed&0xffffffU);if(count>length-done)count=length-done;
  if(size){unsigned slot=(((unsigned long)src>>2)^((unsigned long)src>>11))&63;u8*data=block_pixels+slot*64;
   if(tile_keys[slot]!=src){if(lz4(src,size,data,64)!=64)return 0;tile_keys[slot]=src;}src=data;
  }
  src+=(y&7)*8+(xx&7);for(i=0;i<count;i++)row[done+i]=src[i];done+=count;
 }return length;
}
/* Bounded row decoder. No heap, whole-panorama buffer or writable ROM needed. */
static int decode_stored_row(const Image*im,int y,u8*row,unsigned capacity){
 unsigned x=0,at,end;if(y<0||y>=im->height||im->width>capacity)return 0;
 if(im->encoding==7){for(x=0;x<im->width;x++)row[x]=im->pixels[0];return im->width;}
 if(im->encoding==6)return tiled_span(im,y,0,im->width,row);
 if(im->encoding==9){const u8*data=image_portrait_pixels(im->pixels);const u16*source=(const u16*)im->rows;static const u8 nearest36[36]={0,2,3,4,5,7,8,10,11,12,14,15,16,18,19,20,21,23,24,25,27,28,29,31,32,33,35,36,38,39,40,42,43,44,46,47};int sy=nearest36[y];if(!data)return 0;
  for(x=0;x<im->width;x++){unsigned sx=nearest36[x],tile=(sy/16*3+sx/16)*4+(sy%16/8)*2+sx%16/8,color=source[data[tile*64+sy%8*8+sx%8]],lo=0,hi=im->color_count;
   while(lo<hi){unsigned mid=(lo+hi)/2;if(im->colors[mid]<color)lo=mid+1;else hi=mid;}row[x]=lo;
  }return im->width;
 }
 if(im->encoding==8){unsigned bh=4096/im->width,block=(unsigned)y/bh,lines=im->height-block*bh,expected;if(lines>bh)lines=bh;expected=lines*im->width;
  legacy_blocks();if(!im->rows)return 0;
  if(last_pixels!=im->pixels||last_block!=(int)block){last_pixels=0;last_block=-1;if((unsigned)lz4(im->pixels+im->rows[block],im->rows[block+1]-im->rows[block],block_pixels,expected)!=expected)return 0;last_pixels=im->pixels;last_block=block;}
  memcpy(row,block_pixels+((unsigned)y%bh)*im->width,im->width);return im->width;
 }
 if(!im->encoding){unsigned i;for(i=0;i<im->width;i++)row[i]=im->pixels[y*im->width+i];return im->width;}
 if(im->encoding==3){unsigned stride=(im->width+1)/2;for(x=0;x<im->width;x++)row[x]=im->palette[(im->pixels[y*stride+x/2]>>(x&1?0:4))&15];return im->width;}
 if(!im->rows||!im->palette)return 0;
 if(im->encoding==2||im->encoding==4){unsigned stride=(im->width+1)/2,bh=im->encoding==4?4096/stride:8,block=y/bh,lines=im->height-block*bh,expected;if(lines>bh)lines=bh;expected=stride*lines;if(expected>sizeof(block_pixels))return 0;
  legacy_blocks();
  if(last_pixels!=im->pixels||last_block!=(int)block){last_pixels=0;last_block=-1;if((unsigned)lz4(im->pixels+im->rows[block],im->rows[block+1]-im->rows[block],block_pixels,expected)!=expected)return 0;last_pixels=im->pixels;last_block=block;}
  at=(y%bh)*stride;for(x=0;x<im->width;x++)row[x]=im->palette[(block_pixels[at+x/2]>>(x&1?0:4))&15];return im->width;
 }
 if(im->encoding!=1)return 0;
 at=im->rows[y];end=im->rows[y+1];
 while(at<end&&x<im->width){unsigned c=im->pixels[at++],n,i;
  if(c&128){n=(c&127)+2;if(at>=end||x+n>im->width)return 0;c=im->pixels[at++];if(c>=16)return 0;for(i=0;i<n;i++)row[x++]=im->palette[c];}
  else {n=c+1;if(at+(n+1)/2>end||x+n>im->width)return 0;for(i=0;i<n;i++){c=im->pixels[at+i/2];row[x++]=im->palette[(c>>(i&1?0:4))&15];}at+=(n+1)/2;}
 }
 return x==im->width&&at==end?x:0;
}
int decode_image_row(const Image*im,int y,u8*row,unsigned capacity){unsigned x;if(y<0||y>=im->height||im->width>capacity)return 0;if(im->stored_width&&im->stored_height){Image stored=*im;stored.width=im->stored_width;stored.height=im->stored_height;if(!decode_stored_row(&stored,y*stored.height/im->height,stored_row,sizeof(stored_row)))return 0;{unsigned sx=0,acc=0;for(x=0;x<im->width;x++){row[x]=stored_row[sx];acc+=stored.width;while(acc>=im->width){acc-=im->width;sx++;}}}return im->width;}return decode_stored_row(im,y,row,capacity);}
/* The GBA compositor samples directly from stored pixels. Expanding a reduced
 * image back to its virtual width before shrinking it again costs CPU for
 * pixels that never reach the screen. The old decoders remain for callers
 * that explicitly need the full virtual row. */
int decode_image_storage_row(const Image*im,int y,u8*row,unsigned capacity){
 Image stored=*im;
 if(im->stored_width&&im->stored_height){stored.width=im->stored_width;stored.height=im->stored_height;}
 return decode_stored_row(&stored,y,row,capacity);
}
/* Expand only the stored columns that reach the changed screen rectangle.
 * LZ4 still reconstructs its bounded eight-line block, but unrelated columns
 * are not unpacked through the palette into the row buffer. */
int decode_image_storage_span(const Image*im,int y,int x,int length,u8*row,unsigned capacity){
 unsigned i,width=im->stored_width?im->stored_width:im->width,height=im->stored_height?im->stored_height:im->height;
 const u8*src;
 if(y<0||(unsigned)y>=height||x<0||length<1||(unsigned)x>width||(unsigned)length>width-(unsigned)x||(unsigned)length>capacity)return 0;
 if(im->encoding==7){for(i=0;i<(unsigned)length;i++)row[i]=im->pixels[0];return length;}
 if(im->encoding==6)return tiled_span(im,y,x,length,row);
 if(!im->encoding){src=im->pixels+(unsigned)y*width+x;for(i=0;i<(unsigned)length;i++)row[i]=src[i];return length;}
 if(im->encoding==2||im->encoding==4){
  legacy_blocks();
  unsigned stride=(width+1)/2,bh=im->encoding==4?4096/stride:8,block=(unsigned)y/bh,lines=height-block*bh,expected;if(lines>bh)lines=bh;expected=stride*lines;
  if(expected>sizeof(block_pixels)||!im->rows||!im->palette)return 0;
  if(last_pixels!=im->pixels||last_block!=(int)block){last_pixels=0;last_block=-1;if((unsigned)lz4(im->pixels+im->rows[block],im->rows[block+1]-im->rows[block],block_pixels,expected)!=expected)return 0;last_pixels=im->pixels;last_block=block;}
  src=block_pixels+((unsigned)y%bh)*stride;
 }else if(im->encoding==3){if(!im->palette)return 0;src=im->pixels+(unsigned)y*((width+1)/2);}
 else {
  if(!decode_image_storage_row(im,y,stored_row,sizeof(stored_row)))return 0;
  for(i=0;i<(unsigned)length;i++)row[i]=stored_row[x+i];return length;
 }
 for(i=0;i<(unsigned)length;i++){unsigned xx=(unsigned)x+i;row[i]=im->palette[(src[xx/2]>>(xx&1?0:4))&15];}
 return length;
}

/* Draw small chipset regions without expanding hundreds of unrelated pixels.
 * This is the same nearest-neighbour mapping as decode_image_row. */
int decode_image_span(const Image*im,int y,int x,int length,u8*row,unsigned capacity){
 unsigned i,width=im->stored_width?im->stored_width:im->width,height=im->stored_height?im->stored_height:im->height,yy,xx,acc;
 if(y<0||y>=im->height||x<0||length<1||x+length>im->width||(unsigned)length>capacity)return 0;
 if(im->encoding==7){for(i=0;i<(unsigned)length;i++)row[i]=im->pixels[0];return length;}
 yy=(unsigned)y*height/im->height;
 if(im->encoding==6&&width==im->width)return tiled_span(im,yy,x,length,row);
 if(im->encoding==2||im->encoding==4){unsigned stride=(width+1)/2,bh=im->encoding==4?4096/stride:8,block=yy/bh,lines=height-block*bh,expected,at;if(lines>bh)lines=bh;expected=stride*lines;if(expected>sizeof(block_pixels))return 0;
  legacy_blocks();
  if(last_pixels!=im->pixels||last_block!=(int)block){last_pixels=0;last_block=-1;if((unsigned)lz4(im->pixels+im->rows[block],im->rows[block+1]-im->rows[block],block_pixels,expected)!=expected)return 0;last_pixels=im->pixels;last_block=block;}
  xx=(unsigned)x*width/im->width;acc=(unsigned)x*width%im->width;at=(yy%bh)*stride;
  for(i=0;i<(unsigned)length;i++){row[i]=im->palette[(block_pixels[at+xx/2]>>(xx&1?0:4))&15];acc+=width;while(acc>=im->width){acc-=im->width;xx++;}}return length;
 }
 {Image stored=*im;stored.width=width;stored.height=height;if(!decode_stored_row(&stored,yy,stored_row,sizeof(stored_row)))return 0;xx=(unsigned)x*width/im->width;acc=(unsigned)x*width%im->width;
  for(i=0;i<(unsigned)length;i++){row[i]=stored_row[xx];acc+=width;while(acc>=im->width){acc-=im->width;xx++;}}return length;}
}

extern const short chip_image_ids[];
extern const unsigned short chip_quad_image_ids[][1920];
extern const unsigned chip_image_count;
int chipset_quadrant(int atlas,int x,int y){unsigned i;if(x<0||x>=60||y<0||y>=32)return -1;for(i=0;i<chip_image_count;i++)if(chip_image_ids[i]==atlas){int id=chip_quad_image_ids[i][x+y*60];const Image*im=images+id;if(im->transparent&128)return -1;/* Legacy global-palette transparent quadrants. */if(im->encoding==3&&!im->colors&&!im->palette[0]&&!im->palette[1])return -1;return id;}return -1;}
