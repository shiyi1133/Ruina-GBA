#ifndef RUINA_LCF_H
#define RUINA_LCF_H
/* Allocation-free LCF access. Buffers may point directly into GBA cartridge ROM.
 * Missing fields are distinct from zero-valued fields. Engine defaults belong
 * in the typed schema layer, not this byte-transport layer.
 */
typedef unsigned char ru8;
typedef unsigned int ru32;
typedef struct { const ru8 *data; ru32 size; } LcfSpan;
typedef struct { LcfSpan span; ru32 pos; int error; } LcfReader;
typedef struct {
    ru32 code, indent, parameter_count;
    LcfSpan text, parameters;
} LcfCommand;

#if defined(__arm__) || defined(__thumb__)
#define LCF_HOT __attribute__((section(".iwram"),long_call))
#else
#define LCF_HOT
#endif

int LCF_HOT lcf_number(LcfReader *r, ru32 *out);
int lcf_bytes(LcfReader *r, ru32 length, LcfSpan *out);
int LCF_HOT lcf_string(LcfReader *r, LcfSpan *out);
int LCF_HOT lcf_field(LcfSpan fields, ru32 id, LcfSpan *out);
int lcf_array(LcfSpan array, ru32 id, LcfSpan *out);
int lcf_next_entry(LcfReader *r, ru32 *id, LcfSpan *out);
int lcf_index(LcfSpan array, LcfSpan *slots, ru32 capacity);
int lcf_integer(LcfSpan field, ru32 *out);
int lcf_command(LcfReader *r, LcfCommand *out);
/* Parse and decode operands once; values may be null for boundary scans. */
int LCF_HOT lcf_command_values(LcfReader *r, LcfCommand *out, int *values, ru32 capacity);
int lcf_root(LcfSpan file, LcfSpan *header, LcfSpan *fields);
int lcf_resource(LcfSpan pack, const char *filename, LcfSpan *out);
#endif
