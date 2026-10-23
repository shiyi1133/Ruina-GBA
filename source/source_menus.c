/* Original event selection and effects are unchanged. Only the list display
 * retains unchanged rows, header fields and its opaque background. */
#include "game.h"
#include "source_menus.h"
volatile u32 source_menu_video_metrics[4];/* full frames, lists, rows, headers */
static const char*label(int event){unsigned i;for(i=0;i<source_menu_label_count;i++)if(source_menu_labels[i].map==game.map&&source_menu_labels[i].event==event)return source_menu_labels[i].label;return 0;}
static int text_length(const char*s){int n=0;while(s[n])n++;return n;}
int source_menu_active(void){return game.map==13||game.map==14||game.map==15||game.map==18||game.map==19||game.map==22;}
static const char*heading(void){switch(game.map){case 13:return "烹调";case 14:return "制作武器";case 15:return "制作防具";case 18:return "选择料理";case 19:return "调和";default:return "称号";}}
static void row(const u16*ids,int index,int selected,int top){
    int y=42+(index-top)*18;const char*s=label(ids[index]);
    box(5,y-1,230,16,index==selected?8:11);
    draw_text(10,y,format_text((LcfSpan){(const u8*)s,text_length(s)}),index==selected?2:1,219);source_menu_video_metrics[2]++;
}
static void header(int selected,int count){
    box(7,2,225,31,11);draw_text(8,3,heading(),2,145);draw_num(167,3,selected+1,6);draw_text(191,3,"/",6,6);draw_num(201,3,count,6);
    if(game.map==22){draw_text(8,21,"所持SP",6,78);draw_num(92,21,variable(26),1);draw_text(139,21,"称号之证",6,72);draw_num(216,21,game.items[201],1);}
    else{draw_text(8,21,"金钱",6,48);draw_num(62,21,game.gold,1);}source_menu_video_metrics[3]++;
}
void source_menu_screen(void){
    u16 ids[MAX_EVENT];int count=0,sel=0,top=0,i,dirty=1,exit_id=game.map==13?2:3,first=1,previous=-1,previous_top=-1;
    unsigned rendered_revision=0,previous_labels=0;
    for(i=1;i<MAX_EVENT;i++){int pid;LcfSpan p=event_page(i,0,&pid);if(p.data&&val(p,33,0)==0&&label(i)){if(i==game.selected)sel=count;ids[count++]=i;}}
    if(!count){fault(9320);return;}debug_state[15]=14;
    for(;;){unsigned k;debug_state[11]=ids[sel];debug_state[17]=count;debug_state[18]=sel;
        if(dirty){unsigned hash=2166136261U;int complex=0,full=first||rendered_revision!=video_revision();
            if(sel<top)top=sel;if(sel>=top+6)top=sel-5;
            for(i=top;i<count&&i<top+6;i++){const char*s=label(ids[i]);const u8*p=(const u8*)format_text((LcfSpan){(const u8*)s,text_length(s)});while(*p){if(*p=='\n')complex=1;hash=(hash^*p++)*16777619U;}}
            if(full){video_scene_palette(-1);clear(11);source_menu_video_metrics[0]++;}
            header(sel,count);
            if(full||complex||top!=previous_top||hash!=previous_labels){
                box(5,41,230,119,11);for(i=top;i<count&&i<top+6;i++)row(ids,i,sel,top);source_menu_video_metrics[1]++;
            }else if(sel!=previous){row(ids,previous,sel,top);row(ids,sel,sel,top);}
            flip();first=dirty=0;previous=sel;previous_top=top;previous_labels=hash;rendered_revision=video_revision();
        }
        k=wait_frame();
        if(k&KEY_UP){sel=(sel+count-1)%count;dirty=1;}
        if(k&KEY_DOWN){sel=(sel+1)%count;dirty=1;}
        if(k&KEY_L){sel=clamp(sel-6,0,count-1);dirty=1;}
        if(k&KEY_R){sel=clamp(sel+6,0,count-1);dirty=1;}
        if(k&(KEY_A|KEY_B)){int event=k&KEY_B?exit_id:ids[sel];LcfSpan e=map_event(event);game.x=val(e,2,0);game.y=val(e,3,0);game.selected=event;push_event(event,0);debug_state[15]=0;return;}
    }
}
