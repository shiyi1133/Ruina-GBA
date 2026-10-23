#ifndef RUINA_STORAGE_CODEC_H
#define RUINA_STORAGE_CODEC_H
#include "types.h"
unsigned pack_state(const u8*source,unsigned length,u8*target,unsigned capacity);
int unpack_state(const u8*source,unsigned length,u8*target,unsigned expected);
/* Optional bounded packet-boundary service. The callback must not mutate
 * source/target buffers or recursively enter this codec. Plain APIs retain
 * exactly the same encoded bytes and do not call a service. */
unsigned pack_state_serviced(const u8*source,unsigned length,u8*target,unsigned capacity,void(*service)(void));
int unpack_state_serviced(const u8*source,unsigned length,u8*target,unsigned expected,void(*service)(void));
#endif
