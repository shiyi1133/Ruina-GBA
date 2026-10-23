/* Original forced movement bytecode; tile positions and timing are executed,
 * while the GBA node view omits pixel interpolation and sprite animation.
 * Parameter decoding and timing follow pinned game_interpreter_shared.cpp,
 * game_character.cpp/.h. GPL-3.0-or-later. */
#include "engine.h"
extern const u8 original_lcf_start[],original_lcf_end[];
static const int directions[4]={8,6,2,4};
static int number(LcfReader*r){ru32 n;if(!lcf_number(r,&n)){fault(9092);return 0;}return n;}
static int embedded_int(LcfReader*r){unsigned n=0;int i;for(i=0;i<5;i++){int b=number(r);n=(n<<7)|(b&127);if(!(b&128))return n;}fault(9093);return 0;}
static LcfSpan embedded_string(LcfReader*r,u8*text){int length=embedded_int(r),i;if(length<0||length>255){fault(9094);return (LcfSpan){0,0};}for(i=0;i<length;i++)text[i]=number(r);return (LcfSpan){text,length};}
void movement_reset(void){memset(game.routes,0,sizeof(game.routes));}
int movement_active(void){int i;for(i=0;i<MAX_MOVE_ROUTE;i++)if(game.routes[i].active)return 1;return 0;}
void movement_start(const LcfCommand*c){
    LcfReader r={c->parameters,0,0};int id=number(&r),frequency=number(&r),repeat=number(&r),skip=number(&r),i,empty=-1,flags;MotionRoute*m;
    if(id==10005)id=depth?stack[depth-1].event_id:0;
    if(id!=10001&&(id<=0||id>=MAX_EVENT||!map_event(id).data))return;
    if(c->parameters.size>65535||c->parameters.data<original_lcf_start||c->parameters.data+c->parameters.size>original_lcf_end){fault(9095);return;}
    for(i=0;i<MAX_MOVE_ROUTE;i++){if(game.routes[i].active&&game.routes[i].target==id){empty=i;break;}if(!game.routes[i].active&&empty<0)empty=i;}
    if(empty<0){fault(9096);return;}m=game.routes+empty;flags=event_motion_flags(id);
    *m=(MotionRoute){c->parameters.data-original_lcf_start,c->parameters.size,r.pos,id,0,frequency>=1&&frequency<=8?frequency:6,(repeat?1:0)|(skip?2:0),(flags>>4)&7,1};
    if(!m->speed){if(id==10001)m->speed=4;else{int pid;LcfSpan page=event_page(id,0,&pid);m->speed=clamp(val(page,37,4),1,6);}}
}
static int toward(int id,int away){int dx=game.x-event_coordinate(id,0),dy=game.y-event_coordinate(id,1),d;if(!dx&&!dy)return event_direction(id);if((dx<0?-dx:dx)>(dy<0?-dy:dy))d=dx>0?6:4;else d=dy>0?2:8;return away?10-d:d;}
void movement_tick(void){
    int slot;if(battle_active||engine_clock_paused||halt_code)return;
    for(slot=0;slot<MAX_MOVE_ROUTE&&!halt_code;slot++){
        MotionRoute*m=game.routes+slot;LcfReader r;int limit=128;if(!m->active)continue;if(m->wait){m->wait--;if(m->wait)continue;}
        if(m->offset+m->size>(unsigned)(original_lcf_end-original_lcf_start)||m->position>m->size){fault(9097);return;}
        r=(LcfReader){{original_lcf_start+m->offset,m->size},m->position,0};
        while(limit--&&!halt_code){
            int op,flags=event_motion_flags(m->target),d=event_direction(m->target),start=r.pos;
            if(r.pos>=r.span.size){if(!(m->flags&1)){m->active=0;break;}r.pos=0;number(&r);number(&r);number(&r);number(&r);m->position=r.pos;if(r.pos>=r.span.size)m->active=0;break;}
            op=number(&r);
            if(op<=11){
                int dx=0,dy=0,x=event_coordinate(m->target,0),y=event_coordinate(m->target,1),nx,ny;
                if(op<4)d=directions[op];else if(op==8)d=directions[random_n(4)];else if(op==9||op==10)d=toward(m->target,op==10);
                if(op>=4&&op<=7){dx=op==4||op==5?1:-1;dy=op==4||op==7?-1:1;if(!(flags&1))d=dy>0?2:8;}else {dx=d==6?1:d==4?-1:0;dy=d==2?1:d==8?-1:0;}
                nx=x+dx;ny=y+dy;
                if(map_step_allowed(m->target,x,y,nx,ny,flags&2)){event_relocate(m->target,map_round_x(nx),map_round_y(ny));if(!(flags&1)&&op!=11)event_set_direction(m->target,d);m->wait=(256>>(1+m->speed))+(m->frequency>=8?0:1<<(9-m->frequency));if(!m->wait)m->wait=1;}
                else {if(m->target!=10001&&map_round_x(nx)==game.x&&map_round_y(ny)==game.y){int pid;LcfSpan p=event_page(m->target,0,&pid);if(p.data&&val(p,33,0)==2)world_queue_touch(m->target);}if(!(m->flags&2)){r.pos=start;m->wait=1;}}
                m->position=r.pos;break;
            }
            if(op>=12&&op<=22){int index=0;for(;index<4;index++)if(directions[index]==d)break;if(index==4)index=2;
                if(op<=15)d=directions[op-12];else if(op==16)d=directions[(index+1)%4];else if(op==17)d=directions[(index+3)%4];else if(op==18)d=10-d;else if(op==19)d=directions[(index+(random_n(2)?1:3))%4];else if(op==20)d=directions[random_n(4)];else d=toward(m->target,op==22);
                event_set_direction(m->target,d);m->wait=m->frequency>=8?0:1<<(8-m->frequency);m->position=r.pos;if(m->wait)break;else continue;
            }
            switch(op){
            case 23:m->wait=20+(m->frequency>=8?0:1<<(8-m->frequency));break;
            case 26:flags|=1;break;case 27:flags&=~1;break;
            case 28:m->speed=clamp(m->speed+1,1,6);flags=(flags&~112)|(m->speed<<4);break;
            case 29:m->speed=clamp(m->speed-1,1,6);flags=(flags&~112)|(m->speed<<4);break;
            case 30:m->frequency=clamp(m->frequency+1,1,8);break;case 31:m->frequency=clamp(m->frequency-1,1,8);break;
            case 32:case 33:{int id=embedded_int(&r);if(id<1||id>MAX_SWITCH){fault(9098);break;}if(game.switches[id]!=(op==32)&&map_watches_switch(id))parallel_revision++;game.switches[id]=op==32;break;}
            case 34:{u8 name[256];LcfSpan text=embedded_string(&r,name);int image=resource_image(3,text),index=embedded_int(&r);if(m->target==10001){game.player_sprite=image<0?65535:image;game.player_sprite_index=index;}else if(m->target<MAX_EVENT){game.event_sprite[m->target]=image<0?65535:image;game.event_sprite_index[m->target]=index;}parallel_revision++;break;}
            case 35:{u8 name[256];LcfSpan text=embedded_string(&r,name);int p[3];p[0]=embedded_int(&r);p[1]=embedded_int(&r);p[2]=embedded_int(&r);audio_command(RM2K_PlaySound,text,p);break;}
            case 36:flags|=2;break;case 37:flags&=~2;break;
            case 38:case 39:case 40:case 41:break; /* Sprite-only effects. */
            default:fault(9099);break; /* Unused jump commands are not silently skipped. */
            }
            event_set_motion_flags(m->target,flags);m->position=r.pos;if(m->wait)break;
        }
    }
}
