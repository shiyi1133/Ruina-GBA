#ifndef RM2K_NATIVE_MIDI_H
#define RM2K_NATIVE_MIDI_H
#include "types.h"
#ifdef RUINA_LIGHT_MUSIC
#define NATIVE_MIDI_BLOCK 128
#else
#define NATIVE_MIDI_BLOCK 64
#endif
/* ROM format written by native_music_assets.py. All offsets are relative to
 * their bank; no pointers or host-size-dependent objects are serialized. */
typedef struct {u32 delay,attack,hold,decay,release,sustain,decay_coeff,release_coeff,decay_length;} NativeEnvelope;
typedef struct {
 u32 offset,end,loop_start,loop_end,step,gain;int pan;u16 group,preset;
 short lfo_pitch,lfo_volume,env_pitch,pad;u32 lfo_delay,lfo_delta;
 NativeEnvelope amp,mod;
} NativeTone;
typedef struct {u32 magic,version,tones,tone_count,lists,samples,sample_count,pitches,volumes,pans,loop_pairs;} NativeSoundFont;
void native_midi_init(const void*bank);
void native_midi_quality(int appreciation);
void native_midi_start(const void*sequence);
void native_midi_stop(void);
void native_midi_render(short*stereo,unsigned frames);
void native_midi_seek(u32 source_sample);
u32 native_midi_position(void);
extern volatile u32 native_midi_debug[8];
#endif
