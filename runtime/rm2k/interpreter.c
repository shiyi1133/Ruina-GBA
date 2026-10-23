#include "engine.h"
#ifdef RUINA_BORROW_COMMANDS
#include "borrowed_commands.h"
#endif
static int params_slots[4][512],params_used[4],execution_level;
/* Bytecode is immutable cartridge data. Cache control-flow destinations only;
 * actor values, conditions and random draws are still evaluated every time. */
typedef struct {LcfSpan source;unsigned from,to;int kind,indent,a,b;} JumpMemo;
static JumpMemo jumps[256];
static JumpMemo*jump_slot(Frame*f,int kind,int indent,int a,int b){unsigned h=((unsigned long)f->reader.span.data>>2)^f->reader.pos^(kind*131U)^(a*17U);JumpMemo*m=jumps+(h&255);if(m->to&&m->source.data==f->reader.span.data&&m->source.size==f->reader.span.size&&m->from==f->reader.pos&&m->kind==kind&&m->indent==indent&&m->a==a&&m->b==b){f->reader.pos=m->to;return 0;}*m=(JumpMemo){f->reader.span,f->reader.pos,0,kind,indent,a,b};return m;}
static inline __attribute__((always_inline)) void command_audio(void){static unsigned audio_work;if(!(audio_work++&15))audio_service();}
static int get_command(LcfReader*r,LcfCommand*c,int*p){
    /* Long background pages and branch scans must refill sound without
     * advancing game ticks or recursively running another event interpreter. */
    command_audio();
    unsigned i,n;if(!lcf_command_values(r,c,p,512)){fault(9100);return 0;}n=c->parameter_count;if(n>512){fault(9101);return 0;}
    /* Only the supplied operands and fixed-schema defaults are observable.
     * Clearing all 512 shop slots for every background instruction made input
     * unresponsive on ARM7; ordinary commands use at most 16 default slots. */
    if(p){
        /* Slots start zeroed and each execution level owns one. Only slots
         * written by the previous instruction can need clearing. Branch
         * scans use a null operand pointer and never alter this ownership. */
        unsigned old=params_used[execution_level-1];if(old>16)old=16;
        for(i=n;i<old;i++)p[i]=0;params_used[execution_level-1]=n;
    }return 1;
}
static int value_or_var(int mode,int n){return mode?variable(n):n;}
/* liblcf TargetEvalMode: 0=single, 1=range, 2=indirect single.
 * Range is not a variable reference. Ruina uses it to reset story switches. */
static int target_range(const int*p,int*from,int*to){if(p[0]==0)*from=*to=p[1];else if(p[0]==1){*from=p[1];*to=p[2];}else if(p[0]==2)*from=*to=variable(p[1]);else {fault(9205);return 0;}return 1;}
static int compare(int a,int b,int op){if(op<0||op>5){fault(9102);return 0;}return rm2k_compare(a,b,op);}
static int party_has(int a){int i;for(i=0;i<game.party_count;i++)if(game.party[i]==a)return 1;return 0;}
static int item_count(int id,int equipped){int n=0,i,j;if(id<1||id>MAX_ITEM){fault(9103);return 0;}n=game.items[id];if(equipped)for(i=0;i<game.party_count;i++)for(j=0;j<5;j++)if(game.actors[game.party[i]].equipment[j]==id)n++;return n;}
static int conditional(const int*p,LcfSpan text){int a=p[1],op=p[2],n=p[3],i;Actor*s;
    switch(p[0]){
    case 0:return sw(a)==(op==0);
    case 1:return compare(variable(a),value_or_var(op,n),p[4]);
    case 2:return op?timer_seconds(0)<=a:timer_seconds(0)>=a;
    case 3:return op?game.gold<=a:game.gold>=a;
    case 4:return (item_count(a,1)>0)==(op==0);
    case 5:
        if(a<1||a>MAX_ACTOR){fault(9104);return 0;}s=&game.actors[a];
        switch(op){case 0:return party_has(a);case 1:for(i=0;i<(int)text.size;i++)if(s->name[i]!=text.data[i])return 0;return !s->name[text.size];case 2:return s->level>=n;case 3:return s->hp>=n;case 4:return learned(a,n);case 5:for(i=0;i<5;i++)if(s->equipment[i]==n)return 1;return 0;case 6:return has_state(a,n)!=0;}
        break;
    case 6:{static const int directions[4]={8,6,2,4};return p[2]>=0&&p[2]<4&&event_direction(a)==directions[p[2]];}
    case 8:return !vm_background;
    case 9:return audio_played_once();
    }
    fault(9120+p[0]);return 0;
}
static void skip_to(Frame*f,int indent,int first,int second){LcfCommand c;JumpMemo*m=jump_slot(f,1,indent,first,second);if(!m)return;while(f->reader.pos<f->reader.span.size){if(!get_command(&f->reader,&c,0))return;if((int)c.indent==indent&&(c.code==(unsigned)first||c.code==(unsigned)second)){m->to=f->reader.pos;return;}}m->source.data=0;fault(9140);}
static void label(Frame*f,int id){LcfReader r={f->reader.span,0,0};LcfCommand c;JumpMemo*m=jump_slot(f,2,0,id,0);if(!m)return;while(r.pos<r.span.size){if(!get_command(&r,&c,0))return;if(c.code==RM2K_Label){LcfReader p={c.parameters,0,0};ru32 n;if(lcf_number(&p,&n)&&n==(unsigned)id){m->to=f->reader.pos=r.pos;return;}}}m->source.data=0;fault(9141);}
static void end_loop(Frame*f,unsigned indent){LcfReader r={f->reader.span,0,0};LcfCommand prev;unsigned start=0,until=f->reader.pos;JumpMemo*m=jump_slot(f,3,indent,0,0);if(!m)return;while(r.pos<until){if(!get_command(&r,&prev,0))break;if(prev.code==RM2K_Loop&&prev.indent==indent)start=r.pos;}if(!start){m->source.data=0;fault(9183);}else m->to=f->reader.pos=start;}
static void choose_branch(Frame*f,int indent,int selected){LcfCommand c;while(f->reader.pos<f->reader.span.size){if(!get_command(&f->reader,&c,0))return;if((int)c.indent==indent&&c.code==RM2K_ShowChoiceOption){LcfReader p={c.parameters,0,0};ru32 n;if(lcf_number(&p,&n)&&(int)n==selected)return;}if((int)c.indent==indent&&c.code==RM2K_ShowChoiceEnd)return;}fault(9142);}
static void change_party(int id,int remove){int i;if(id<1||id>MAX_ACTOR){fault(9143);return;}for(i=0;i<game.party_count;i++)if(game.party[i]==id)break;if(remove&&i<game.party_count){for(;i+1<game.party_count;i++)game.party[i]=game.party[i+1];game.party_count--;parallel_revision++;}else if(!remove&&i==game.party_count&&i<4){game.party[game.party_count++]=id;parallel_revision++;}}
static int target_actor(int mode,int id,int index){if(mode==0)return index<game.party_count?game.party[index]:0;if(index)return 0;return mode==1?id:variable(id);}
static int operand(const int*p){int a=p[5],b=p[6];switch(p[4]){
    case 0:return a;case 1:return variable(a);case 2:return variable(variable(a));
    case 3:{int lo=a<b?a:b,hi=a>b?a:b;return lo+random_n(hi-lo+1);}
    case 4:return b==0?item_count(a,0):item_count(a,1)-item_count(a,0);
    case 5:return actor_query(a,b);
    case 6:switch(b){case 0:return a==10001?game.map:0;case 1:return event_coordinate(a,0);case 2:return event_coordinate(a,1);case 3:return event_direction(a);case 4:return event_coordinate(a,0)*16+8-map_display_x();case 5:return event_coordinate(a,1)*16+16-map_display_y();}break;
    case 7:switch(a){case 0:return game.gold;case 1:return timer_seconds(0);case 2:return game.party_count;case 3:return game.saves;case 4:return game.battles;case 5:return game.wins;case 6:return game.defeats;case 7:return game.escapes;case 8:return audio_midi_ticks();case 9:return timer_seconds(1);}break;
    case 8:return battle_enemy_query(a,b);
    }fault(9170+p[4]);return 0;
}
static int needs_ui(unsigned code){return code==RM2K_ShowMessage||code==RM2K_ShowChoice||code==RM2K_InputNumber||code==RM2K_EnterHeroName||code==RM2K_OpenShop||code==RM2K_OpenSaveMenu||code==RM2K_OpenMainMenu||code==RM2K_EnemyEncounter||code==RM2K_ShowPicture||code==RM2K_MovePicture||code==RM2K_ErasePicture||code==RM2K_EraseScreen||code==RM2K_ShowScreen;}
static void visible_wait(int frames){int i;for(i=0;i<frames&&!halt_code;i++){wait_frame();if(!presentation_busy()&&!battle_active&&!engine_ui_depth&&(world_presented_revision!=parallel_revision&&(i==frames-1||(i&7)==0))){world_redraw();}}}
/* The large opcode switch is cold relative to per-pixel drawing and image
 * decoding. Keep command transport hot, reserving scarce IWRAM for those
 * inner loops; bytecode order, waits and event rules are unchanged. */
static void __attribute__((noinline)) execute_events_until(int parent_depth){
    int budget=vm_background?256:8000;int*params=params_slots[execution_level-1];static u8 message_bytes[8192];
    while(depth>parent_depth&&!halt_code&&!battle_event_stopped()&&(!vm_background||!vm_background_map||game.map==vm_background_map)&&budget--){
        Frame*f=&stack[depth-1];LcfCommand local;const LcfCommand*c=&local;const int*p=params;int i,a,n,ok;
        if(f->reader.pos>=f->reader.span.size){depth--;continue;}
        unsigned command_start=f->reader.pos;
        #ifdef RUINA_BORROW_COMMANDS
        {const BorrowedCommand*borrow=lcf_borrow_command(&f->reader);
         if(borrow){c=&borrow->command;p=borrow->values;command_audio();}
         else if(!get_command(&f->reader,&local,params))return;
        }
#else
        if(!get_command(&f->reader,&local,params))return;
#endif
        if(vm_background&&(engine_ui_depth||presentation_busy())&&needs_ui(c->code)){f->reader.pos=command_start;return;}
        if(vm_background&&needs_ui(c->code)&&c->code!=RM2K_ShowPicture&&c->code!=RM2K_MovePicture&&c->code!=RM2K_ErasePicture)parallel_revision++;
        debug_state[0]=0x52554e;debug_state[5]=c->code;debug_state[6]=f->common_id;debug_state[7]=f->event_id;debug_state[8]=f->reader.pos;debug_state[9]=game.map;debug_state[10]=game.vars[41];
        switch(c->code){
        case 0:depth--;break;
        case 10:case RM2K_Comment:case RM2K_Comment_2:case RM2K_MessageOptions:break;
        case RM2K_ShowMessage:{int len=c->text.size;LcfReader r=f->reader;LcfCommand next;if(len>8000){fault(9180);break;}memcpy(message_bytes,c->text.data,len);
            while(r.pos<r.span.size){LcfReader peek=r;if(!get_command(&peek,&next,0))break;if(next.code!=RM2K_ShowMessage_2)break;if(len+next.text.size+1>8000){fault(9181);break;}message_bytes[len++]='\n';memcpy(message_bytes+len,next.text.data,next.text.size);len+=next.text.size;r=peek;}
            f->reader=r;message((LcfSpan){message_bytes,len});break;}
        case RM2K_ShowMessage_2:fault(9182);break;
        case RM2K_ChangeFaceGraphic:current_face=c->text.size?face_image(c->text,p[0]):-1;break;
        case RM2K_ShowChoice:n=choices(c->text,p[0]);choose_branch(f,c->indent,n);break;
        case RM2K_InputNumber:event_number_input(p[0],p[1]);break;
        case RM2K_KeyInputProc:if(vm_background){if(!event_input_ready(p,c->parameter_count)){f->reader.pos=command_start;return;}}else event_key_input(p,c->parameter_count);break;
        case RM2K_ShowChoiceOption:skip_to(f,c->indent,RM2K_ShowChoiceEnd,RM2K_ShowChoiceEnd);break;
        case RM2K_ShowChoiceEnd:case RM2K_EndBranch:break;
        case RM2K_ConditionalBranch:if(!conditional(p,c->text))skip_to(f,c->indent,RM2K_ElseBranch,RM2K_EndBranch);break;
        case RM2K_ElseBranch:skip_to(f,c->indent,RM2K_EndBranch,RM2K_EndBranch);break;
        case RM2K_ConditionalBranch_B:if(!battle_event_condition(p))skip_to(f,c->indent,RM2K_ElseBranch_B,RM2K_EndBranch_B);break;
        case RM2K_ElseBranch_B:skip_to(f,c->indent,RM2K_EndBranch_B,RM2K_EndBranch_B);break;
        case RM2K_EndBranch_B:break;
        case RM2K_Label:break;
        case RM2K_JumpToLabel:label(f,p[0]);break;
        case RM2K_Loop:break;
        case RM2K_EndLoop:end_loop(f,c->indent);break;
        case RM2K_BreakLoop:{LcfCommand end;while(f->reader.pos<f->reader.span.size){if(!get_command(&f->reader,&end,0))break;if(end.code==RM2K_EndLoop&&end.indent<c->indent)break;}break;}
        case RM2K_EndEventProcessing:depth--;break;
        case RM2K_EraseEvent:erase_event(f->event_id);break;
        case RM2K_CallEvent:if(p[0]==0)push_common(p[1]);else if(p[0]==1)push_event(p[1]==10005?f->event_id:p[1],p[2]);else if(p[0]==2){int event=variable(p[1]);push_event(event==10005?f->event_id:event,variable(p[2]));}else fault(9184);break;
        case RM2K_TimerOperation:timer_command(p);break;
        case RM2K_ControlSwitches:{int from,to;if(!target_range(p,&from,&to))break;if(from<1||to>MAX_SWITCH){fault(9185);break;}for(i=from;i<=to;i++){int old=game.switches[i];game.switches[i]=p[3]==2?!old:p[3]==0;if(old!=game.switches[i]&&map_watches_switch(i))parallel_revision++;}break;}
        case RM2K_ControlVars:{int from,to;int value=operand(p);if(!target_range(p,&from,&to))break;if(from<1||to>MAX_VAR){fault(9186);break;}for(i=from;i<=to;i++){if(p[3]<0||p[3]>5){fault(9187);break;}int old=game.vars[i],operand_value=p[4]==3&&from!=to?operand(p):value;game.vars[i]=rm2k_variable_op(old,operand_value,p[3]);if(old!=game.vars[i]&&map_watches_variable(i))parallel_revision++;}break;}
        case RM2K_ChangeGold:game.gold=clamp(game.gold+(p[0]?-1:1)*value_or_var(p[1],p[2]),0,999999);break;
        case RM2K_ChangeItems:a=value_or_var(p[1],p[2]);n=value_or_var(p[3],p[4]);if(a<1||a>MAX_ITEM){fault(9188);break;}if(n>=0){int count=clamp(game.items[a]+(p[0]?-n:n),0,99);if(count!=game.items[a])parallel_revision++;game.items[a]=count;}break;
        case RM2K_ChangePartyMembers:change_party(value_or_var(p[1],p[2]),p[0]);break;
        case RM2K_SimulatedAttack:
            for(i=0;(a=target_actor(p[0],p[1],i))!=0&&i<4;i++){
                int range;n=rm2k_simulated_base(p[2],p[3],p[4],stat(a,3),stat(a,4));range=rm2k_variance_range(n,p[5]);n=rm2k_variance(n,p[5],range?random_n(range+1):0);if(n<0)n=0;
                game.actors[a].hp=clamp(game.actors[a].hp-n,0,stat(a,0));if(!game.actors[a].hp)set_state(a,1,1);
                if(p[6]){if(p[7]<1||p[7]>MAX_VAR){fault(9202);break;}game.vars[p[7]]=n;}if(p[0]!=0)break;
            }
            if(!battle_active){for(i=0;i<game.party_count;i++)if(game.actors[game.party[i]].hp>0)break;if(game.party_count&&i==game.party_count)fault(RM2K_GameOver);}break;
        case RM2K_ChangeExp:case RM2K_ChangeLevel:case RM2K_ChangeParameters:case RM2K_ChangeSkills:case RM2K_ChangeEquipment:case RM2K_ChangeHP:case RM2K_ChangeSP:case RM2K_ChangeCondition:case RM2K_FullHeal:
            for(i=0;(a=target_actor(p[0],p[1],i))!=0&&i<4;i++){
                Actor*s;if(a<1||a>MAX_ACTOR){fault(9189);break;}s=&game.actors[a];n=(p[2]?-1:1)*value_or_var(p[3],p[4]);
                switch(c->code){
                case RM2K_ChangeExp:actor_exp(a,s->exp+n);break;
                case RM2K_ChangeLevel:actor_level(a,s->level+n);break;
                case RM2K_ChangeParameters:if(p[3]<0||p[3]>5){fault(9190);break;}s->bonus[p[3]]+=(p[2]?-1:1)*value_or_var(p[4],p[5]);break;
                case RM2K_ChangeSkills:set_learned(a,value_or_var(p[3],p[4]),p[2]==0);break;
                case RM2K_ChangeEquipment:{int item=p[2]?0:value_or_var(p[3],p[4]),slot=p[2]?p[3]:val(item_data[item],3,0)-1,j;if(slot==5){for(j=0;j<5;j++){if(s->equipment[j])game.items[s->equipment[j]]=clamp(game.items[s->equipment[j]]+1,0,99);s->equipment[j]=0;}}else if(slot>=0&&slot<5){if(s->equipment[slot])game.items[s->equipment[slot]]=clamp(game.items[s->equipment[slot]]+1,0,99);if(item&&game.items[item])game.items[item]--;s->equipment[slot]=item;}else fault(9191);parallel_revision++;break;}
                case RM2K_ChangeHP:if(s->hp>0){s->hp=clamp(s->hp+n,p[5]?0:1,stat(a,0));if(!s->hp)set_state(a,1,1);}break;
                case RM2K_ChangeSP:s->mp=clamp(s->mp+n,0,stat(a,1));break;
                case RM2K_ChangeCondition:set_state(a,p[3],p[2]==0);break;
                case RM2K_FullHeal:memset(s->states,0,sizeof(s->states));s->hp=stat(a,0);s->mp=stat(a,1);break;
                }if(p[0]!=0)break;
            }break;
        case RM2K_ChangeHeroName:case RM2K_ChangeHeroTitle:a=p[0];if(a<1||a>MAX_ACTOR){fault(9192);break;}{char*d=c->code==RM2K_ChangeHeroName?game.actors[a].name:game.actors[a].title;unsigned len=c->text.size;if(len>31){fault(9192);break;}memcpy(d,c->text.data,len);d[len]=0;}break;
        case RM2K_ChangeActorFace:if(p[0]>0&&p[0]<=MAX_ACTOR){int image=face_image(c->text,p[1]);game.actors[p[0]].face=p[1];game.actor_face_sheet[p[0]]=image>=0?image:65535;}else fault(9193);break;
        case RM2K_ChangeSpriteAssociation:if(p[0]>0&&p[0]<=MAX_ACTOR){int image=resource_image(3,c->text);game.actor_sprite[p[0]]=image>=0?image:65535;game.actor_sprite_index[p[0]]=p[1];parallel_revision++;}else fault(9193);break;
        case RM2K_EnterHeroName:event_name_input(p[0]);break;
        /* This execution level owns its parameter slot until the shop closes;
         * nested events use the next slot. Avoid a 2032-byte stack copy in
         * every interpreter frame, including frames that never open a shop. */
        case RM2K_OpenShop:{int mode=p[0],handlers=p[2],count=(int)c->parameter_count-4,changed;if(count<0||count>508){fault(9195);break;}changed=open_shop(mode,p+4,count);if(handlers)skip_to(f,c->indent,changed?RM2K_Transaction:RM2K_NoTransaction,RM2K_EndShop);break;}
        case RM2K_Transaction:case RM2K_NoTransaction:skip_to(f,c->indent,RM2K_EndShop,RM2K_EndShop);break;
        case RM2K_EndShop:break;
        case RM2K_Teleport:set_map(p[0],p[1],p[2]);break;
        case RM2K_ChangeEventLocation:event_relocate(p[0],value_or_var(p[1],p[2]),value_or_var(p[1],p[3]));break;
        case RM2K_MemorizeLocation:for(i=0;i<3;i++){if(p[i]<1||p[i]>MAX_VAR){fault(9196);break;}game.vars[p[i]]=i==0?game.map:i==1?game.x:game.y;}break;
        case RM2K_RecallToLocation:set_map(variable(p[0]),variable(p[1]),variable(p[2]));break;
        case RM2K_StoreTerrainID:if(p[3]<1||p[3]>MAX_VAR){fault(9196);break;}game.vars[p[3]]=map_terrain(value_or_var(p[0],p[1]),value_or_var(p[0],p[2]));break;
        case RM2K_StoreEventID:a=value_or_var(p[0],p[1]);n=value_or_var(p[0],p[2]);if(p[3]<1||p[3]>MAX_VAR){fault(9196);break;}game.vars[p[3]]=0;for(i=MAX_EVENT-1;i>0;i--){LcfSpan e=map_event(i);if(e.data&&event_coordinate(i,0)==a&&event_coordinate(i,1)==n){game.vars[p[3]]=i;break;}}break;
        case RM2K_ChangeSaveAccess:game.save_enabled=p[0]!=0;break;
        case RM2K_ChangeMainMenuAccess:game.menu_enabled=p[0]!=0;break;
        case RM2K_OpenSaveMenu:{static const char prompt[]="保存当前进度/暂不保存";if(choices((LcfSpan){(const u8*)prompt,sizeof(prompt)-1},2)==0){if(save_checkpoint())describe("已保存当前剧情进度。");else describe("保存校验失败。");}break;}
        case RM2K_OpenMainMenu:system_menu();break;
        case RM2K_EnemyEncounter:{int escape_mode=p[3],old_backdrop=game.battle_backdrop,result;if(p[2]==1)game.battle_backdrop=resource_image(4,c->text);else {LcfSpan terrain=entry(db[16],p[2]==2?p[8]:map_terrain(game.x,game.y));game.battle_backdrop=resource_image(4,field(terrain,4));}result=battle(value_or_var(p[0],p[1]),p[3],p[4],p[5]);game.battle_backdrop=old_backdrop;if(halt_code)break;if(result==1&&escape_mode==1){depth=0;break;}skip_to(f,c->indent,result==3?RM2K_EndBattle:RM2K_VictoryHandler+result,RM2K_EndBattle);break;}
        case RM2K_ChangeMonsterHP:case RM2K_ChangeMonsterMP:case RM2K_ChangeMonsterCondition:case RM2K_ShowHiddenMonster:case RM2K_ChangeBattleBG:case RM2K_ShowBattleAnimation_B:case RM2K_TerminateBattle:if(!battle_event_command(c->code,p,c->text))fault(9203);break;
        case RM2K_VictoryHandler:case RM2K_EscapeHandler:case RM2K_DefeatHandler:skip_to(f,c->indent,RM2K_EndBattle,RM2K_EndBattle);break;
        case RM2K_EndBattle:break;
        case RM2K_GameOver:describe("……你们全灭了。");depth=0;halt_code=RM2K_GameOver;break;
        case RM2K_ReturntoTitleScreen:depth=0;halt_code=RM2K_ReturntoTitleScreen;break;
        /* Graphic-only commands have explicit renderer adaptations. */
        case RM2K_ShowPicture:render_picture_show(c->text,p);break;
        case RM2K_MovePicture:n=pictures_move(p);if(vm_background&&n){vm_wait_frames=n;return;}visible_wait(n);break;
        case RM2K_ErasePicture:render_picture_erase(p[0]);break;
        case RM2K_MoveEvent:movement_start(c);break;
        case RM2K_ProceedWithMovement:if(vm_background&&movement_active()){f->reader.pos=command_start;return;}while(movement_active()&&!halt_code)visible_wait(1);break;
        case RM2K_TileSubstitution:tile_substitute(p[0],p[1],p[2]);break;
        case RM2K_TintScreen:case RM2K_PanScreen:case RM2K_ChangePBG:case RM2K_PlayerVisibility:render_screen_command(c->code,c->text,p);n=render_screen_wait(c->code,p);if(vm_background&&n){vm_wait_frames=n;return;}visible_wait(n);break;
        case RM2K_EraseScreen:case RM2K_ShowScreen:case RM2K_FlashScreen:case RM2K_ShakeScreen:case RM2K_WeatherEffects:n=presentation_command(c->code,p);if(vm_background&&n){vm_wait_frames=n;return;}visible_wait(n);break;
        case RM2K_ShowBattleAnimation:n=animation_start(p[0]);if(!p[2])break;if(vm_background&&n){vm_wait_frames=n;return;}visible_wait(n);break;
        case RM2K_FlashSprite:presentation_cue(3,6);break;
        case RM2K_ChangeSystemGraphics:case RM2K_ChangeScreenTransitions:break;
        case RM2K_Wait:n=p[0]>0?p[0]*6:1;if(vm_background){vm_wait_frames=n;return;}visible_wait(n);break;
        case RM2K_ChangeSystemBGM:case RM2K_ChangeSystemSFX:case RM2K_PlayBGM:case RM2K_FadeOutBGM:case RM2K_MemorizeBGM:case RM2K_PlayMemorizedBGM:case RM2K_PlaySound:debug_state[20]=c->code;audio_command(c->code,c->text,p);break;
        default:fault(c->code);break;
        }
        (void)ok;
    }
    if(battle_event_stopped())depth=parent_depth;
    if(budget<=0&&!vm_background)fault(9199);
}
void run_events_until(int parent_depth){if(execution_level>=4){fault(9204);return;}execution_level++;execute_events_until(parent_depth);execution_level--;}
void run_events(void){run_events_until(0);}
