#include "storage_codec.h"
/* Byte PackBits keeps the original state exact while allowing new persistent
 * features in 32 KiB SRAM. An incompressible state fails without overwriting. */
unsigned pack_state_serviced(const u8*in,unsigned length,u8*out,unsigned capacity,void(*service)(void)){
 unsigned at=0,x=0,next_service=0;
 while(at<length){unsigned n=1,start,i;if(service&&at>=next_service){service();next_service=at+512;}while(at+n<length&&in[at+n]==in[at]&&n<130)n++;
  if(n>=3){if(x+2>capacity)return 0;out[x++]=128+n-3;out[x++]=in[at];at+=n;continue;}
  start=at++;
  while(at<length&&at-start<128){if(at+2<length&&in[at]==in[at+1]&&in[at]==in[at+2])break;at++;}
  n=at-start;if(x+1+n>capacity)return 0;out[x++]=n-1;for(i=0;i<n;i++)out[x++]=in[start+i];
 }return x;
}
int unpack_state_serviced(const u8*in,unsigned length,u8*out,unsigned expected,void(*service)(void)){
 unsigned at=0,x=0,next_service=0;while(at<length){unsigned n=in[at++],i;if(service&&x>=next_service){service();next_service=x+512;}if(n&128){n=(n&127)+3;if(at>=length||n>expected-x)return 0;for(i=0;i<n;i++)out[x++]=in[at];at++;}else{n++;if(n>length-at||n>expected-x)return 0;for(i=0;i<n;i++)out[x++]=in[at++];}}return x==expected;
}

unsigned pack_state(const u8*in,unsigned length,u8*out,unsigned capacity){return pack_state_serviced(in,length,out,capacity,0);}
int unpack_state(const u8*in,unsigned length,u8*out,unsigned expected){return unpack_state_serviced(in,length,out,expected,0);}
