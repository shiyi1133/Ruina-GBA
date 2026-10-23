/* Cooperative RM2000 background interpreters. Each event owns its call stack
 * and wait position; main dialogue/input stacks are suspended, never consumed.
 * Original RPG_RT saves restart parallel stacks (see pinned game_event.cpp and
 * game_commonevent.cpp); saved variables, timers and event positions persist. */
#include "engine.h"
typedef struct {int map,event,page,common,depth,wait,running;Frame frames[32];} Parallel;
static Parallel contexts[MAX_PARALLEL];
static Frame suspended[2][32];
static u32 suspended_debug[2][24];
static int scheduler_depth;
int engine_ui_depth,vm_background,vm_wait_frames,vm_background_map;
unsigned parallel_revision;
unsigned ui_generation;
volatile u32 parallel_trace[8];
void parallel_reset(void){memset(contexts,0,sizeof(contexts));scheduler_depth=engine_ui_depth=vm_background=vm_wait_frames=vm_background_map=0;parallel_revision=0;memset((void*)parallel_trace,0,sizeof(parallel_trace));}
static int source_ready(Parallel*p){
    if(p->common){LcfSpan c=common_data[p->common];return c.data&&val(c,11,5)==4&&(!val(c,12,0)||sw(val(c,13,1)));}
    if(p->map!=game.map||source_menu_active())return 0;
    {int pid;LcfSpan page=event_page(p->event,0,&pid);return page.data&&pid==p->page&&val(page,33,0)==4;}
}
static Parallel*find_context(int common,int event,int page){
    int i,empty=-1;for(i=0;i<MAX_PARALLEL;i++){
        Parallel*p=contexts+i;if(!p->common&&!p->event){if(empty<0)empty=i;continue;}
        if(p->common==common&&p->event==event&&(common||(p->page==page&&p->map==game.map)))return p;
    }
    if(empty<0){fault(9090);return 0;}
    {Parallel*p=contexts+empty;memset(p,0,sizeof(*p));p->map=game.map;p->event=event;p->page=page;p->common=common;return p;}
}
int parallel_active(void){int i;for(i=0;i<MAX_PARALLEL;i++)if((contexts[i].common||contexts[i].event)&&source_ready(contexts+i))return 1;return 0;}
void parallel_tick(void){
    int slot,i,n,main_depth,main_background,main_background_map,main_wait,main_face,main_map;unsigned before;const u16*ids;
    if(scheduler_depth>=2||battle_active||engine_clock_paused||halt_code||game.map<1||game.map>=RM2K_MAP_COUNT)return;
    parallel_trace[4]++;
    /* A common event pauses when its switch is off; its program counter is
     * retained. A removed map page loses its interpreter, as in RPG_RT. */
    for(i=0;i<MAX_PARALLEL;i++)if(!contexts[i].running&&contexts[i].event&&!source_ready(contexts+i))memset(contexts+i,0,sizeof(contexts[i]));
    ids=parallel_common_events(&n);for(i=0;i<n;i++){int id=ids[i];LcfSpan c=common_data[id];if(!val(c,12,0)||sw(val(c,13,1)))find_context(id,0,0);}
    if(!source_menu_active()){ids=parallel_map_events(&n);for(i=0;i<n;i++){int pid,id=ids[i];LcfSpan p=event_page(id,0,&pid);if(p.data&&val(p,33,0)==4)find_context(0,id,pid);}}
    if(!parallel_active())return;
    slot=scheduler_depth++;main_depth=depth;main_background=vm_background;main_background_map=vm_background_map;main_wait=vm_wait_frames;main_face=current_face;main_map=game.map;
    memcpy(suspended[slot],stack,main_depth*sizeof(Frame));memcpy(suspended_debug[slot],(const void*)debug_state,sizeof(debug_state));before=parallel_revision;
    for(i=0;i<MAX_PARALLEL&&!halt_code&&main_map==game.map;i++){
        Parallel*p=contexts+i;if(p->running||(!p->common&&!p->event)||!source_ready(p))continue;
        if(p->wait>0){p->wait--;if(p->wait)continue;}
        depth=p->depth;memcpy(stack,p->frames,depth*sizeof(Frame));
        if(!depth){if(p->common)push_common(p->common);else push_event(p->event,p->page);}
        p->running=1;vm_background=1;vm_background_map=p->event?p->map:0;vm_wait_frames=0;parallel_trace[0]++;parallel_trace[1]=p->common;parallel_trace[2]=p->event;
        run_events_until(0);p->running=0;p->depth=depth;p->wait=vm_wait_frames;memcpy(p->frames,stack,depth*sizeof(Frame));
    }
    depth=main_depth;vm_background=main_background;vm_background_map=main_background_map;vm_wait_frames=main_wait;memcpy(stack,suspended[slot],main_depth*sizeof(Frame));current_face=main_face;
    if(!halt_code)memcpy((void*)debug_state,suspended_debug[slot],sizeof(debug_state));
    scheduler_depth--;if(parallel_revision!=before)parallel_trace[3]++;
}
