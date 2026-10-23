#include "engine.h"

/* GBA presentation policy: scene changes cut to black, prepare the new image
 * while hidden, then reveal it immediately. Map flash and shake use brief brightness cues; battle cells
 * have their own original-frame renderer; weather
 * uses a sparse static overlay. Event waits, picture coordinates, timers,
 * animation SFX and all gameplay calculations remain in their own systems.
 * Transient effects never enlarge or alter the ordinary SRAM save format. */
static int cut_active;
static int pulse_remaining,pulse_total,pulse_level;

static void apply_brightness(void){
    int level=0;
    if(cut_active)level=-16;
    else if(pulse_remaining&&pulse_total)
        level=pulse_level*pulse_remaining/pulse_total;
    video_brightness(level);
}

void presentation_reset(void){
    cut_active=pulse_remaining=pulse_total=pulse_level=0;
    video_brightness(0);
}
int presentation_busy(void){return cut_active!=0;}

void presentation_black_redraw(void){
    /* TintScreen and animated picture opacity are independent of Erase/Show.
     * Rebuild their endpoint behind black too. UI/background changes keep
     * their normal deferred draw so a parallel event cannot replace a menu. */
    if(battle_active||engine_ui_depth)return;
    pulse_remaining=0;cut_active=1;apply_brightness();
    world_redraw();
    cut_active=0;apply_brightness();
}

static int transition(int show,int type){
    /* Pinned Player ignores map transitions inside battle. The user requests
     * immediate black cuts for every map transition type, including type 19. */
    (void)type;
    if(battle_active)return 0;
    if(show==!game.screen_hidden)return 0;
    pulse_remaining=0;cut_active=1;
    /* Hide the old framebuffer immediately. The expensive new-image draw
     * happens behind black; no gradual brightness frames or extra waits. */
    apply_brightness();game.screen_hidden=!show;
    parallel_revision++;world_redraw();
    /* EraseScreen has now uploaded a real black framebuffer. Releasing the
     * hardware shade allows later dialogue over black to remain readable. */
    cut_active=0;apply_brightness();return 0;
}

void presentation_cue(int level,int frames){
    if(frames<=0||!level)return;
    pulse_level=clamp(level,-8,8);
    pulse_remaining=pulse_total=clamp(frames,1,12);
    apply_brightness();
}

int presentation_command(int code,const int*p){
    if(code==RM2K_EraseScreen)return transition(0,p[0]);
    if(code==RM2K_ShowScreen)return transition(1,p[0]);
    if(code==RM2K_FlashScreen){
        int duration=clamp(p[4]*6,0,65535);
        if(!duration)pulse_remaining=0;
        else presentation_cue((p[0]||p[1]||p[2]?1:-1)*clamp(p[3]*8/31,0,8),duration);
        apply_brightness();return p[5]?duration:0;
    }
    if(code==RM2K_ShakeScreen){
        int duration=clamp(p[2]*6,0,65535);
        if(duration)presentation_cue(-clamp(p[0],1,3),8);
        return p[3]?duration:0;
    }
    if(code==RM2K_WeatherEffects){
        game.weather=(p[0]>=1&&p[0]<=2)?p[0]|(clamp(p[1],0,2)<<2):0;
        parallel_revision++;
    }
    return 0;
}

void presentation_tick(void){
    if(pulse_remaining)pulse_remaining--;
    apply_brightness();
}

void presentation_weather(void){
    int i,type=game.weather&3,count=6+((game.weather>>2)&3)*3;
    if(!type||game.screen_hidden||battle_active)return;
    for(i=0;i<count;i++){
        int x=(i*53+17)%232,y=(i*37+9)%150;
        if(type==1){box(x,y,1,3,1);box(x-1,y+3,1,2,1);}
        else box(x,y,2,2,1);
    }
}
