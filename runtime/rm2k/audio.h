#ifndef RUINA_AUDIO_H
#define RUINA_AUDIO_H
#include "types.h"
typedef struct {int id,volume,pitch,pan;} Music;
void audio_init(void);
void audio_reset(void);
void audio_restore(void);
void audio_command(int code,LcfSpan name,const int*p);
void audio_music(Music music,int fadein);
int audio_music_count(void);
int audio_music_id(int index);
unsigned audio_music_frames(int id);
void audio_pause_music(int paused);
int audio_music_paused(void);
int audio_music_finished(void);
void audio_music_quality(int appreciation);
int audio_current_quality(void);
void audio_music_position(unsigned position);
void audio_system(int which);
void audio_effect(int which);
void audio_default_sounds(void);
void audio_irq(void);
void audio_service(void);
int audio_midi_ticks(void);
int audio_played_once(void);
extern volatile u32 audio_debug[8];
#endif
