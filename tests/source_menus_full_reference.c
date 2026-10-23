/* Ruina's original custom menus are map events. This replaces their graphical
 * cursor with a list; checks, deductions, confirmation and effects are executed
 * by the same LCF interpreter as the rest of the game. No recipe rules here. */
#include "game.h"
#include "source_menus.h"
static const char*label(int event){unsigned i;for(i=0;i<source_menu_label_count;i++)if(source_menu_labels[i].map==game.map&&source_menu_labels[i].event==event)return source_menu_labels[i].label;return 0;}
static int text_length(const char*s){int n=0;while(s[n])n++;return n;}
int source_menu_active(void){return game.map==13||game.map==14||game.map==15||game.map==18||game.map==19||game.map==22;}
static const char*heading(void){switch(game.map){case 13:return "烹调";case 14:return "制作武器";case 15:return "制作防具";case 18:return "选择料理";case 19:return "调和";default:return "称号";}}
void source_menu_screen(void){
    u16 ids[MAX_EVENT];int count=0,sel=0,top=0,i,dirty=1,exit_id=game.map==13?2:3;
    for(i=1;i<MAX_EVENT;i++){int pid;LcfSpan p=event_page(i,0,&pid);
        if(p.data&&val(p,33,0)==0&&label(i)){if(i==game.selected)sel=count;ids[count++]=i;}}
    if(!count){fault(9320);return;}
    debug_state[15]=14;
    for(;;){unsigned k;debug_state[11]=ids[sel];debug_state[17]=count;debug_state[18]=sel;
        if(dirty){
            clear(11);draw_text(8,3,heading(),2,145);draw_num(167,3,sel+1,6);draw_text(191,3,"/",6,6);draw_num(201,3,count,6);
            if(game.map==22){draw_text(8,21,"所持SP",6,78);draw_num(92,21,variable(26),1);draw_text(139,21,"称号之证",6,72);draw_num(216,21,game.items[201],1);}
            else {draw_text(8,21,"金钱",6,48);draw_num(62,21,game.gold,1);}
            if(sel<top)top=sel;if(sel>=top+6)top=sel-5;
            for(i=top;i<count&&i<top+6;i++){
                int y=42+(i-top)*18;const char*s=label(ids[i]);
                if(i==sel)box(5,y-1,230,16,8);
                draw_text(10,y,format_text((LcfSpan){(const u8*)s,text_length(s)}),i==sel?2:1,219);
            }
            flip();dirty=0;
        }
        k=wait_frame();
        if(k&KEY_UP){sel=(sel+count-1)%count;dirty=1;}
        if(k&KEY_DOWN){sel=(sel+1)%count;dirty=1;}
        if(k&KEY_L){sel=clamp(sel-6,0,count-1);dirty=1;}
        if(k&KEY_R){sel=clamp(sel+6,0,count-1);dirty=1;}
        if(k&(KEY_A|KEY_B)){
            int event=k&KEY_B?exit_id:ids[sel];LcfSpan e=map_event(event);
            game.x=val(e,2,0);game.y=val(e,3,0);game.selected=event;
            push_event(event,0);debug_state[15]=0;return;
        }
    }
}
