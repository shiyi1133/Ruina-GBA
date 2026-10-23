#include "balanced.h"
#include "engine.h"
static char formatted[8192],dialog[8192];
static int formatted_pos,automatic_message;
/* The original data includes ten-enemy encounters. Target menus therefore
 * need more than eight choices. This non-nested UI buffer stays off the stack. */
/* Message text and choice text are mutually exclusive UI states. Parallel
 * UI commands are deferred while either is open. Reuse the message workspace
 * for the same sixteen 512-byte choices instead of reserving another 8 KiB. */
static char*options[16];
static int length(const char*s){int n=0;while(s[n])n++;return n;}
static void copy_text(char*d,int limit,LcfSpan s){unsigned n=s.size;if(n>=(unsigned)limit)n=limit-1;memcpy(d,s.data,n);d[n]=0;}
static void append(char c){if(formatted_pos<8190)formatted[formatted_pos++]=c;else fault(9050);}
static void append_num(int n){char b[16];unsigned a=n<0?-(unsigned)n:(unsigned)n;int k=15;b[k]=0;do{b[--k]='0'+a%10;a/=10;}while(a);if(n<0)b[--k]='-';while(b[k])append(b[k++]);}
static int bracket(const u8**p,const u8*end,int recurse){int n=0;if(*p>=end||**p!='[')return 0;(*p)++;if(*p+2<end&&(*p)[0]=='\\'&&((*p)[1]=='V'||(*p)[1]=='v')){*p+=2;n=variable(bracket(p,end,recurse+1));}else while(*p<end&&**p>='0'&&**p<='9'){n=n*10+*(*p)++-'0';}if(*p<end&&**p==']')(*p)++;return n;}
static void expand(LcfSpan s,int recurse){
    const u8*p=s.data,*end=p+s.size;if(recurse>8){fault(9051);return;}
    while(p<end&&*p){
        if(*p=='\r'){p++;continue;}
        if(*p=='\\'&&p+1<end){int op=p[1],n;p+=2;
            if(op=='N'||op=='n'){n=bracket(&p,end,recurse);if(n>0&&n<=MAX_ACTOR){LcfSpan q={(const u8*)game.actors[n].name,length(game.actors[n].name)};expand(q,recurse+1);}continue;}
            if(op=='V'||op=='v'){append_num(variable(bracket(&p,end,recurse)));continue;}
            if(op=='C'||op=='c'||op=='S'||op=='s'){(void)bracket(&p,end,recurse);continue;}
            if(op=='\\'){append('\\');continue;}
            if(op=='^'){automatic_message=1;continue;}
            if(op=='>'||op=='<'||op=='!'||op=='.'||op=='|'||op=='$'||op=='_')continue;
            append('\\');append(op);continue;
        }
        append(*p++);
    }
}
static const char*format(LcfSpan s){formatted_pos=0;automatic_message=0;expand(s,0);formatted[formatted_pos]=0;return formatted;}
const char*format_text(LcfSpan s){return format(s);}
static int page_text(const char*str,int offset,int face){
    const u8*p=(const u8*)str+offset;int x=face>=0?64:8,start=x,y=62,width=232-start;
    box(3,55,234,103,11);rect(3,55,234,103,6);
    if(face>=0)portrait(face,8,62);
    while(*p&&y<145){char b[3];unsigned c=*p;int step=c<128?1:2,w=c<128?6:12;if(c=='$'&&((p[1]>='A'&&p[1]<='Z')||(p[1]>='a'&&p[1]<='z'))){step=2;w=12;}
        if(c=='\n'){p++;x=start;y+=14;continue;}
        if(x-start+w>width){x=start;y+=14;if(y>=145)break;}
        b[0]=*p++;b[1]=step==2?*p++:0;b[2]=0;draw_text(x,y,b,1,w);x+=w;
    }
    draw_text(170,145,*p?"A 翻页":"A 继续",2,64);return (const char*)p-str;
}
void message(LcfSpan text){
    static const char old_hint[]="※请将光标移至右下角闪烁的位置";
    static const char new_hint[]="黄标可调查，灰标暂不可达，蓝标是当前位置。\n短按 L/R 选点，A 前往调查。\n按住 R+方向键查看地图；三角箭头提示边界。";
    int off=0,next,i;const char *rendered=format(text);int automatic=automatic_message;
    for(i=0;old_hint[i]&&rendered[i]==old_hint[i];i++){}
    if(game.map==23&&!old_hint[i])rendered=new_hint;
    copy_text(dialog,sizeof(dialog),(LcfSpan){(const u8*)rendered,length(rendered)});
    if(!dialog[0])return;
    engine_ui_depth++;ui_generation++;
    debug_state[15]=1;debug_state[21]++;
    do{debug_state[16]=off;draw_scene();next=page_text(dialog,off,current_face);flip();if(automatic){int i;for(i=0;i<2&&!halt_code;i++)wait_frame();}else while(!(wait_frame()&(KEY_A|(battle_active?KEY_B:0)))&&!halt_code){}off=next;}while(dialog[off]&&!halt_code);debug_state[15]=0;engine_ui_depth--;
}
void describe(const char*s){message((LcfSpan){(const u8*)s,length(s)});}
int balanced_original_choices(LcfSpan text,int cancel){
    int count=0,i,sel=0,top=0,dirty=1;unsigned start=0,pos;
    memset(dialog,0,sizeof(dialog));for(pos=0;pos<=text.size;pos++)if(pos==text.size||text.data[pos]=='/'){
        const char*s;int at=0;if(count>=16){fault(9052);return 0;}options[count]=dialog+count*512;s=format((LcfSpan){text.data+start,pos-start});while(*s&&at<510)options[count][at++]=*s++;count++;start=pos+1;
    }
    debug_state[15]=2;debug_state[17]=count;debug_state[22]++;engine_ui_depth++;ui_generation++;
    for(;;){unsigned k;if(dirty){draw_scene();
        if(battle_active){
            /* Keep the combatant and HP/MP rows visible while choosing. */
            int height=(count<5?count:5)*14+7;
            box(3,19,92,height,11);rect(3,19,92,height,6);
            if(sel<top)top=sel;if(sel>=top+5)top=sel-4;
            for(i=top;i<count&&i<top+5;i++){int y=23+(i-top)*14;if(i==sel)box(6,y-1,86,14,8);draw_text(10,y,options[i],i==sel?2:1,80);}
        }else{int menu_y=choice_header_height(count);box(4,menu_y,232,157-menu_y,11);rect(4,menu_y,232,157-menu_y,6);
        render_choice_header(count);
        if(sel<top)top=sel;if(sel>=top+5)top=sel-4;
        for(i=top;i<count&&i<top+5;i++){int y=menu_y+7+(i-top)*18;if(i==sel){box(8,y-1,224,16,8);draw_text(10,y,">",2,12);}draw_text(22,y,options[i],i==sel?2:1,207);}
        }
        flip();dirty=0;}k=wait_frame();
        if(k&(KEY_UP|KEY_DOWN))dirty=1;
        if(k&KEY_UP){sel=(sel+count-1)%count;audio_effect(0);}if(k&KEY_DOWN){sel=(sel+1)%count;audio_effect(0);}
        debug_state[16]=sel;if(k&KEY_A){audio_effect(1);debug_state[15]=0;engine_ui_depth--;return sel;}if(((k&KEY_B)&&cancel>0)||halt_code){audio_effect(2);debug_state[15]=0;engine_ui_depth--;return cancel>0?cancel-1:0;}
    }
}

volatile u32 balanced_menu_metrics[4];/* scenes, row updates, list updates, reuse */
static void choice_row(int index,int selected,int top,int menu_y){
    if(battle_active){int y=23+(index-top)*14;box(6,y-1,86,14,index==selected?8:11);draw_text(10,y,options[index],index==selected?2:1,80);balanced_menu_metrics[1]++;return;}
    int y=menu_y+7+(index-top)*18;
    box(8,y-1,224,16,index==selected?8:11);
    if(index==selected)draw_text(10,y,">",2,12);
    draw_text(22,y,options[index],index==selected?2:1,207);
    balanced_menu_metrics[1]++;
}
static int menu_background_valid,menu_old_x,menu_old_y,menu_old_right,menu_old_bottom;
static u32 menu_background_stamp,menu_background_epoch,battle_cache_stamp,battle_cache_epoch;
static int menu_rendering,battle_cache_valid,battle_cache_usable;
void balanced_menu_invalidate(void){menu_background_valid=0;if(!menu_rendering)battle_cache_valid=0;}
static void scene_clip_raw(int x,int y,int w,int h){if(w>0&&h>0){video_clip(x,y,w,h);draw_scene();}}
static void scene_clip(int x,int y,int w,int h){
    if(w<=0||h<=0)return;
    int right=x+w,bottom=y+h,left=x>96?x:96,top=y>24?y:24,r=right<240?right:240,b=bottom<96?bottom:96;
    if(!battle_cache_usable||left>=r||top>=b){scene_clip_raw(x,y,w,h);return;}
    balanced_battle_cache_restore(left,top,r-left,b-top);
    scene_clip_raw(x,y,w,top-y);scene_clip_raw(x,b,w,bottom-b);
    scene_clip_raw(x,top,left-x,b-top);scene_clip_raw(r,top,right-r,b-top);
}
void balanced_menu_background(int x,int y,int width,int height){
    int right=clamp(x+width,0,240),bottom=clamp(y+height,0,160);
    if(!battle_active){draw_scene();return;}
    u32 stamp=battle_background_stamp();x=clamp(x,0,240);y=clamp(y,0,160);
    menu_rendering=1;battle_cache_usable=battle_cache_valid&&battle_cache_stamp==stamp&&battle_cache_epoch==balanced_surface_epoch;
    if(!battle_cache_usable)battle_cache_valid=0;
    if(menu_background_valid&&stamp==menu_background_stamp&&menu_background_epoch==balanced_surface_epoch){
        int ox=menu_old_x,oy=menu_old_y,orr=menu_old_right,ob=menu_old_bottom;
        int left=ox>x?ox:x,top=oy>y?oy:y,r=orr<right?orr:right,b=ob<bottom?ob:bottom;
        /* Only the previous modal rectangle can have overwritten the scene.
         * Restore its newly exposed pixels, leaving the rest untouched. */
        if(left>=r||top>=b)scene_clip(ox,oy,orr-ox,ob-oy);
        else{scene_clip(ox,oy,orr-ox,top-oy);scene_clip(ox,b,orr-ox,ob-b);
             scene_clip(ox,top,left-ox,b-top);scene_clip(r,top,orr-r,b-top);}
        /* Actor focus changes the name above the scene, independently of
         * the unchanged enemy artwork and party HP/MP rows. */
        scene_clip(0,0,240,15);
    }else{
        scene_clip(0,0,240,y);scene_clip(0,bottom,240,160-bottom);
        scene_clip(0,y,x,bottom-y);scene_clip(right,y,240-right,bottom-y);
    }
    video_clip(0,0,240,160);menu_old_x=x;menu_old_y=y;menu_old_right=right;menu_old_bottom=bottom;
    menu_background_stamp=stamp;menu_background_epoch=balanced_surface_epoch;menu_background_valid=1;
    if(right<=96||x>=240||bottom<=24||y>=96){battle_cache_valid=balanced_battle_cache_store();battle_cache_stamp=stamp;battle_cache_epoch=balanced_surface_epoch;}
    menu_rendering=0;
}
int choices_selected(LcfSpan text,int cancel,int initial){
    int count=0,sel=0,top=0,previous=-1,previous_top=-1,dirty=1,first=1;
    unsigned start=0,pos,scene_stamp=0;
    memset(dialog,0,sizeof(dialog));
    for(pos=0;pos<=text.size;pos++)if(pos==text.size||text.data[pos]=='/'){
        const char*s;int at=0;if(count>=16){fault(9052);return 0;}
        options[count]=dialog+count*512;s=format((LcfSpan){text.data+start,pos-start});
        while(*s&&at<510)options[count][at++]=*s++;
        count++;start=pos+1;
    }
    sel=clamp(initial,0,count-1);top=sel>=5?sel-4:0;
    debug_state[15]=2;debug_state[17]=count;debug_state[22]++;engine_ui_depth++;ui_generation++;
    for(;;){unsigned k;
        if(dirty){int i,menu_y=choice_header_height(count);u32 stamp=balanced_scene_stamp();int full=first||scene_stamp!=stamp;
            if(sel<top)top=sel;if(sel>=top+5)top=sel-4;
            if(full){balanced_menu_background(3,19,92,(count<5?count:5)*14+7);balanced_menu_metrics[0]++;
                if(battle_active){int height=(count<5?count:5)*14+7;box(3,19,92,height,11);rect(3,19,92,height,6);}
                else{box(4,menu_y,232,157-menu_y,11);rect(4,menu_y,232,157-menu_y,6);render_choice_header(count);}
                for(i=top;i<count&&i<top+5;i++)choice_row(i,sel,top,menu_y);
            }else if(top!=previous_top){
                /* Scrolling changes the list, not the image or portraits. */
                if(battle_active)box(6,22,86,70,11);else box(8,menu_y+6,224,90,11);
                for(i=top;i<count&&i<top+5;i++)choice_row(i,sel,top,menu_y);
                balanced_menu_metrics[2]++;
            }else if(sel!=previous){
                choice_row(previous,sel,top,menu_y);choice_row(sel,sel,top,menu_y);balanced_menu_metrics[3]++;
            }
            flip();dirty=first=0;previous=sel;previous_top=top;scene_stamp=balanced_scene_stamp();
        }
        k=wait_frame();
        if(k&KEY_UP){sel=(sel+count-1)%count;audio_effect(0);dirty=1;}
        if(k&KEY_DOWN){sel=(sel+1)%count;audio_effect(0);dirty=1;}
        debug_state[16]=sel;
        if(k&KEY_A){audio_effect(1);debug_state[15]=0;engine_ui_depth--;return sel;}
        if(((k&KEY_B)&&cancel>0)||halt_code){audio_effect(2);debug_state[15]=0;engine_ui_depth--;return cancel>0?cancel-1:0;}
    }
}
int choices(LcfSpan text,int cancel){return choices_selected(text,cancel,0);}
