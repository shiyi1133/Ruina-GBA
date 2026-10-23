#include "game.h"
#include "assets.h"
extern volatile u32 audio_stream_debug[4];
volatile u32 portrait_pipeline_diagnostic[10];
static void diagnostic_clear(int color){portrait_pipeline_diagnostic[0]=audio_stream_debug[0];portrait_pipeline_diagnostic[1]=video_ticks();portrait_pipeline_diagnostic[6]=audio_stream_debug[2];clear(color);}
static void diagnostic_flip(void){portrait_pipeline_diagnostic[2]=audio_stream_debug[0];portrait_pipeline_diagnostic[3]=video_ticks();portrait_pipeline_diagnostic[7]=audio_stream_debug[2];flip();portrait_pipeline_diagnostic[4]=audio_stream_debug[0];portrait_pipeline_diagnostic[5]=video_ticks();portrait_pipeline_diagnostic[8]=audio_stream_debug[2];}
#define clear diagnostic_clear
#define flip diagnostic_flip
#include "portrait_matrix_gba.c"
