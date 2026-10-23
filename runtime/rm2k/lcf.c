#include "lcf.h"

/* Immutable cartridge fields may be looked up many times in one frame. Cache
 * byte-transport results only; switch/variable/page-condition values are still
 * evaluated by the engine on every request. Mutable RAM spans never enter the
 * cartridge cache. The host switch is used only by the parity checker. */
typedef struct {const ru8*begin;ru32 advance;LcfCommand command;int values[16];} CachedCommand;
volatile ru32 lcf_cache_debug[8];
#ifdef RUINA_PREDECODE_COMMANDS
extern const ru8 original_lcf_start[],predecoded_commands_start[];
typedef struct {ru32 offset;unsigned short advance,code,indent,text_size;ru32 text_offset;unsigned short parameter_size,count;ru32 values[8];} RomCommand;
static inline __attribute__((always_inline)) int rom_command(LcfReader*r,LcfCommand*out,int*values,ru32 capacity){
 const ru32*h=(const ru32*)predecoded_commands_start;unsigned long address,base=(unsigned long)original_lcf_start;ru32 offset,slot,i;
 const unsigned short*table;const RomCommand*records,*record;
 if(r->error||r->pos>=r->span.size)return 0;
 address=(unsigned long)(r->span.data+r->pos);
 if(address<base||address-base>=h[2]||h[0]!=0x444d4350U)return 0;
 offset=address-base;slot=(offset*2654435761U)&h[3];table=(const unsigned short*)(predecoded_commands_start+h[4]);records=(const RomCommand*)(predecoded_commands_start+h[5]);
 while(table[slot]){
  record=records+table[slot]-1;
  if(record->offset==offset){
   if(record->advance>r->span.size-r->pos||(values&&record->count>capacity))return 0;
   out->code=record->code;out->indent=record->indent;out->parameter_count=record->count;
   out->text=(LcfSpan){original_lcf_start+record->text_offset,record->text_size};
   out->parameters=(LcfSpan){r->span.data+r->pos+record->advance-record->parameter_size,record->parameter_size};
   if(values)for(i=0;i<record->count;i++)values[i]=(int)record->values[i];
   r->pos+=record->advance;lcf_cache_debug[6]++;return 1;
  }
  slot=(slot+1)&h[3];
 }
 lcf_cache_debug[7]++;return 0;
}
#endif
#if defined(__arm__) || defined(__thumb__) || defined(LCF_TEST_ROM_CACHE)
#define LCF_HAS_ROM_CACHE 1
typedef struct {LcfSpan source,value;ru32 id;int result;} CachedField;
typedef struct {const ru8*begin,*end;LcfSpan value;ru32 id,next;} CachedEntry;

/* The ROM bank handles the hot parallel streams without RAM entries. Keep
 * the fallback caches in EWRAM, reserving fast instruction RAM for the VM. */
#define LCF_FAST_DATA
static CachedField cached_fields[128] LCF_FAST_DATA;
static CachedEntry cached_entries[64] LCF_FAST_DATA;
static CachedCommand cached_commands[16] LCF_FAST_DATA;
static int immutable_span(LcfSpan s){
#ifdef LCF_TEST_ROM_CACHE
    return s.data!=0;
#else
    ru32 address=(ru32)s.data;
    return address>=0x08000000U&&address<0x0a000000U&&s.size<=0x0a000000U-address;
#endif
}
#endif

static int fail(LcfReader *r) { r->error = 1; return 0; }

static inline int read_number(LcfReader *r, ru32 *out) {
    ru32 n = 0;
    unsigned i;
    ru32 pos = r->pos;
    if (r->error) return 0;
    if (pos < r->span.size && r->span.data[pos] < 128) {
        *out = r->span.data[pos]; r->pos = pos + 1; return 1;
    }
    for (i = 0; i != 5; ++i) {
        ru8 b;
        if (r->pos >= r->span.size) return fail(r);
        b = r->span.data[r->pos++];
        if (n > 0x01ffffffU) return fail(r);
        n = (n << 7) | (b & 127U);
        if (!(b & 128U)) { *out = n; return 1; }
    }
    return fail(r);
}
int lcf_number(LcfReader *r, ru32 *out) { return read_number(r,out); }

int lcf_bytes(LcfReader *r, ru32 length, LcfSpan *out) {
    if (r->error || r->pos > r->span.size || length > r->span.size - r->pos)
        return fail(r);
    out->data = r->span.data + r->pos;
    out->size = length;
    r->pos += length;
    return 1;
}

int lcf_string(LcfReader *r, LcfSpan *out) {
    ru32 size;
    return read_number(r, &size) && lcf_bytes(r, size, out);
}

int lcf_field(LcfSpan fields, ru32 id, LcfSpan *out) {
    if(!fields.size){out->data=0;out->size=0;return 0;}
    LcfReader r = { fields, 0, 0 };
    ru32 k;
    LcfSpan value;
#ifdef LCF_HAS_ROM_CACHE
    CachedField*cached=0;
    if(immutable_span(fields)){
        ru32 address=(ru32)(unsigned long)fields.data;
        cached=cached_fields+(((address>>2)^(address>>11)^id*13U)&127);
        if(cached->source.data==fields.data&&cached->source.size==fields.size&&cached->id==id){lcf_cache_debug[0]++;*out=cached->value;return cached->result;}
        lcf_cache_debug[1]++;
    }
#endif
    out->data = 0; out->size = 0;
    while (r.pos < fields.size) {
        if (!lcf_number(&r, &k)) return -1;
        if (k == 0) break;
        if (!lcf_string(&r, &value)) return -1;
        if (k == id) {
            *out = value;
#ifdef LCF_HAS_ROM_CACHE
            if(cached)*cached=(CachedField){fields,value,id,1};
#endif
            return 1;
        }
    }
#ifdef LCF_HAS_ROM_CACHE
    if(cached)*cached=(CachedField){fields,*out,id,0};
#endif
    return 0;
}

static int skip_fields(LcfReader *r) {
    ru32 k;
    LcfSpan value;
    for (;;) {
        if (!lcf_number(r, &k)) return 0;
        if (!k) return 1;
        if (!lcf_string(r, &value)) return 0;
    }
}

int lcf_next_entry(LcfReader *r, ru32 *id, LcfSpan *out) {
    ru32 start;
#ifdef LCF_HAS_ROM_CACHE
    CachedEntry*cached=0;const ru8*begin=0,*end=0;
    if(!r->error&&r->pos<r->span.size&&immutable_span(r->span)){
        ru32 address=(ru32)(unsigned long)(r->span.data+r->pos);
        begin=r->span.data+r->pos;end=r->span.data+r->span.size;
        cached=cached_entries+(((address>>2)^(address>>11))&63);
        if(cached->begin==begin&&cached->end==end){lcf_cache_debug[2]++;*id=cached->id;*out=cached->value;r->pos+=cached->next;return 1;}
        lcf_cache_debug[3]++;
    }
#endif
    if (!lcf_number(r, id)) return 0;
    start = r->pos;
    if (!skip_fields(r)) return 0;
    out->data = r->span.data + start;
    out->size = r->pos - start;
#ifdef LCF_HAS_ROM_CACHE
    if(cached)*cached=(CachedEntry){begin,end,*out,*id,r->pos-(ru32)(begin-r->span.data)};
#endif
    return 1;
}

int lcf_index(LcfSpan array, LcfSpan *slots, ru32 capacity) {
    LcfReader r = { array, 0, 0 };
    ru32 count, i, key;
    LcfSpan value;
    for (i = 0; i < capacity; ++i) { slots[i].data = 0; slots[i].size = 0; }
    if (!lcf_number(&r, &count)) return 0;
    for (i = 0; i < count; ++i) {
        if (!lcf_next_entry(&r, &key, &value) || key >= capacity) return 0;
        slots[key] = value;
    }
    return !r.error && r.pos == array.size;
}

int lcf_array(LcfSpan array, ru32 id, LcfSpan *out) {
    LcfReader r = { array, 0, 0 };
    ru32 count, i, key, start;
    out->data = 0; out->size = 0;
    if (!lcf_number(&r, &count)) return -1;
    if (count > array.size / 2U) return -1;
    for (i = 0; i < count; ++i) {
        if (!lcf_number(&r, &key)) return -1;
        start = r.pos;
        if (!skip_fields(&r)) return -1;
        if (key == id) {
            out->data = array.data + start;
            out->size = r.pos - start;
            return 1;
        }
    }
    return 0;
}

int lcf_integer(LcfSpan field, ru32 *out) {
    LcfReader r = { field, 0, 0 };
    return lcf_number(&r, out) && r.pos == field.size;
}

static __attribute__((noinline)) int parse_command_values(LcfReader*r,LcfCommand*out,int*values,ru32 capacity,CachedCommand*cached,const ru8*begin){
    ru32 start,i,ignored;
#ifdef LCF_HAS_ROM_CACHE
    int decoded[16];
#else
    (void)cached;(void)begin;
#endif
    if (!read_number(r, &out->code) || !read_number(r, &out->indent)
        || !lcf_string(r, &out->text)
        || !read_number(r, &out->parameter_count)) return 0;
    if (out->parameter_count > r->span.size - r->pos) return fail(r);
    if (values && out->parameter_count > capacity) return fail(r);
    start = r->pos;
    for (i = 0; i < out->parameter_count; ++i) {
        if (!read_number(r, &ignored)) return 0;
        if (values) values[i] = (int)ignored;
#ifdef LCF_HAS_ROM_CACHE
        if(cached&&i<16)decoded[i]=(int)ignored;
#endif
    }
    out->parameters.data = r->span.data + start;
    out->parameters.size = r->pos - start;
#ifdef LCF_HAS_ROM_CACHE
    if(cached&&out->parameter_count<=16){
        cached->command=*out;cached->advance=r->pos-(ru32)(begin-r->span.data);
        for(i=0;i<out->parameter_count;i++)cached->values[i]=decoded[i];
        cached->begin=begin;
    }
#endif
    return 1;
}
int lcf_command_values(LcfReader *r, LcfCommand *out, int *values, ru32 capacity) {
    ru32 i;
#ifdef RUINA_PREDECODE_COMMANDS
    if(rom_command(r,out,values,capacity))return 1;
#endif
#ifdef LCF_HAS_ROM_CACHE
    CachedCommand*cached=0;const ru8*begin=0;
    if(!r->error&&r->pos<r->span.size&&immutable_span(r->span)){
        ru32 address=(ru32)(unsigned long)(r->span.data+r->pos);
        begin=r->span.data+r->pos;
        cached=cached_commands+(((address>>1)^(address>>9))&15);
        /* A shorter span or insufficient operand capacity must take the normal
         * parser path, preserving its exact error and partial-read behaviour. */
        if(cached->begin==begin&&cached->advance<=r->span.size-r->pos&&
           (!values||cached->command.parameter_count<=capacity)){
            lcf_cache_debug[4]++;*out=cached->command;
            if(values)for(i=0;i<out->parameter_count;i++)values[i]=cached->values[i];
            r->pos+=cached->advance;return 1;
        }
        lcf_cache_debug[5]++;
    }
    return parse_command_values(r,out,values,capacity,cached,begin);
#else
    (void)i;return parse_command_values(r,out,values,capacity,0,0);
#endif
}
int lcf_command(LcfReader *r, LcfCommand *out) { return lcf_command_values(r,out,0,0); }

int lcf_root(LcfSpan file, LcfSpan *header, LcfSpan *fields) {
    LcfReader r = { file, 0, 0 };
    if (!lcf_string(&r, header)) return 0;
    return lcf_bytes(&r, file.size - r.pos, fields);
}

static ru32 le32(const ru8 *p) {
    return (ru32)p[0] | (ru32)p[1] << 8 | (ru32)p[2] << 16 | (ru32)p[3] << 24;
}

int lcf_resource(LcfSpan pack, const char *filename, LcfSpan *out) {
    static const char magic[] = "RLCFORIG";
    ru32 i, count;
    unsigned k;
    out->data = 0; out->size = 0;
    if (pack.size < 12) return -1;
    for (k = 0; k != 8; ++k) if (pack.data[k] != magic[k]) return -1;
    count = le32(pack.data + 8);
    if (count > (pack.size - 12) / 48U) return -1;
    for (i = 0; i < count; ++i) {
        const ru8 *e = pack.data + 12 + i * 48;
        ru32 offset, size;
        for (k = 0; k < 32; ++k) {
            if ((ru8)filename[k] != e[k]) break;
            if (!filename[k]) {
                offset = le32(e + 32); size = le32(e + 36);
                if (offset > pack.size || size > pack.size - offset) return -1;
                out->data = pack.data + offset; out->size = size;
                return 1;
            }
        }
    }
    return 0;
}

#ifdef RUINA_BORROW_COMMANDS
#include "borrowed_commands.h"
extern const ru8 original_lcf_start[],original_lcf_end[];
volatile ru32 borrowed_command_debug[3];
volatile ru32 borrowed_prediction_hits;
static const BorrowedCommand*previous_borrowed;
const BorrowedCommand*lcf_borrow_command(LcfReader*r){
 static const BorrowedCommand nop={{10,0,0,{0,0},{0,0}},0,4,{0}};
 unsigned long address,base=(unsigned long)original_lcf_start;ru32 offset,slot;
 if(r->error||r->pos>=r->span.size)return 0;address=(unsigned long)(r->span.data+r->pos);
 if(address<base||address>=(unsigned long)original_lcf_end||r->span.size-r->pos>(unsigned long)original_lcf_end-address)return 0;
 /* Literal empty no-ops still consume one original VM budget slot. */
 if(r->span.size-r->pos>=4&&r->span.data[r->pos]==10&&r->span.data[r->pos+1]<128&&!r->span.data[r->pos+2]&&!r->span.data[r->pos+3]){r->pos+=4;borrowed_command_debug[0]++;return &nop;}
 offset=address-base;
 /* Most arithmetic/control instructions proceed sequentially. A sentinel
  * after the linked table bounds this one-record prediction; branches and
  * nested calls retain the ordinary immutable lookup. */
 if(previous_borrowed){const BorrowedCommand*next=previous_borrowed+1;if(next->original_offset==offset&&next->advance<=r->span.size-r->pos){previous_borrowed=next;r->pos+=next->advance;borrowed_command_debug[1]++;borrowed_prediction_hits++;return next;}}
 slot=(offset*2654435761U)&borrowed_command_hash_mask;
 while(borrowed_command_index[slot]){const BorrowedCommand*c=borrowed_commands+borrowed_command_index[slot]-1;
  if(c->original_offset==offset){if(c->advance>r->span.size-r->pos)return 0;r->pos+=c->advance;previous_borrowed=c;borrowed_command_debug[1]++;return c;}slot=(slot+1)&borrowed_command_hash_mask;
 }borrowed_command_debug[2]++;return 0;
}
#endif
