"""Host differential checks using pinned upstream battle/map/timer bodies.
No emulator memory is changed. These are controlled rule fixtures, not a game
playthrough or proof that all later story branches run on GBA.
"""
import ctypes as C,hashlib,json,random,subprocess
from pathlib import Path
from check_rule_parity import extract
from inspect_lcf import ROOT,data_root,array,fields,integer

def main():
 ref=ROOT/'third_party/Player/src'
 prefix=r'''
#include <algorithm>
#include <array>
#include <vector>
#include <cstdint>
#include <cassert>
#include <cmath>
#include "rm2k_rules.h"
namespace lcf {namespace rpg {
struct TroopPageCondition {
 struct Flags {bool switch_a=false,switch_b=false,variable=false,turn=false,fatigue=false,enemy_hp=false,actor_hp=false,turn_enemy=false,turn_actor=false,command_actor=false;}flags;
 int switch_a_id=1,switch_b_id=2,variable_id=1,variable_value=0,turn_a=0,turn_b=0,fatigue_min=0,fatigue_max=100,enemy_id=0,enemy_hp_min=0,enemy_hp_max=100,actor_id=1,actor_hp_min=0,actor_hp_max=100;
 int turn_enemy_id=0,turn_enemy_a=0,turn_enemy_b=0,turn_actor_id=1,turn_actor_a=0,turn_actor_b=0,command_actor_id=1,command_id=0;
};
struct EventCommand {std::vector<int>parameters;};
}}
namespace Player {bool IsRPG2k3Commands(){return false;}bool IsLegacy(){return false;}}
namespace Output {template<class...A>void Warning(const char*,A...){}}
struct Game_Battler {int hp=1,maxhp=1,def=0,spi=0,sp=0,maxsp=0;int GetHp()const{return hp;}int GetSp()const{return sp;}int GetMaxSp()const{return maxsp;}int GetMaxHp()const{return maxhp;}int GetBattleTurn()const{return 0;}int GetLastBattleAction()const{return 0;}int GetDef()const{return def;}int GetSpi()const{return spi;}void ChangeHp(int d,bool){hp+=d;}};
static Game_Battler enemy,actor;
struct Switches {int a=0,b=0;bool Get(int id){return id==1?a:b;}};
struct Variables {int n=0;int Get(int){return n;}void Set(int,int v){n=v;}};
struct EnemyParty {Game_Battler*GetEnemy(int id){return id==0&&enemy.hp>=0&&enemy.maxhp>0?&enemy:nullptr;}};
struct Actors {Game_Battler*GetActor(int id){return id==1&&actor.hp>=0&&actor.maxhp>0?&actor:nullptr;}};
static int global_turn;static bool in_battle;
namespace Game_Battle {bool CheckTurns(int,int,int);int GetTurn(){return global_turn;}bool IsBattleRunning(){return in_battle;}}
namespace Game_Map {void SetNeedRefresh(bool){}}
namespace Utils {template<class T,class U>T RoundTo(U n){return (T)std::lround(n);}}
constexpr int DEFAULT_FPS=60;
struct Game_Party {
 enum {Timer1,Timer2};
 struct {int timer1_frames=0,timer2_frames=0;bool timer1_active=false,timer2_active=false,timer1_visible=false,timer2_visible=false,timer1_battle=false,timer2_battle=false;}data;
 int GetFatigue();std::vector<Game_Battler*>GetActors(){return {&actor};}
 void SetTimer(int,int);void StartTimer(int,bool,bool);void StopTimer(int);void UpdateTimers();int GetTimerFrames(int);int GetTimerSeconds(int);
};
namespace Main_Data {static Switches sw;static Variables var;static EnemyParty ep;static Actors actors;static Game_Party party;
auto*game_switches=&sw;auto*game_variables=&var;auto*game_enemyparty=&ep;auto*game_actors=&actors;auto*game_party=&party;}
struct Game_Interpreter_Battle {bool AreConditionsMet(const lcf::rpg::TroopPageCondition&,Game_Battler*);};
namespace Rand {int roll;int GetRandomNumber(int,int){return roll;}}
'''
 variance=extract((ref/'algo.cpp').read_text(),'int VarianceAdjustEffect(')
 prefix+='namespace Algo {\n'+variance+'\n}\n'
 prefix+='struct Game_Interpreter {bool CommandSimulatedAttack(const lcf::rpg::EventCommand&);std::vector<Game_Battler*>GetActors(int,int){return {&actor};}void CheckGameOver(){}};\n'
 bodies=[(ref/'map_data.h').read_text(),extract((ref/'game_battle.cpp').read_text(),'bool Game_Battle::CheckTurns('),extract((ref/'game_interpreter_battle.cpp').read_text(),'bool Game_Interpreter_Battle::AreConditionsMet('),extract((ref/'game_interpreter.cpp').read_text(),'bool Game_Interpreter::CommandSimulatedAttack(')]
 party=(ref/'game_party.cpp').read_text()
 for sig in ['void Game_Party::SetTimer(','void Game_Party::StartTimer(','void Game_Party::StopTimer(','void Game_Party::UpdateTimers(','int Game_Party::GetTimerSeconds(','int Game_Party::GetTimerFrames(','int Game_Party::GetFatigue(']:bodies.append(extract(party,sig))
 suffix=r'''
extern "C" int up_fatigue(int h,int mh,int m,int mm){actor.hp=h;actor.maxhp=mh;actor.sp=m;actor.maxsp=mm;return Game_Party().GetFatigue();}
extern "C" int up_chip(int id){return ChipIdToIndex(id);}
extern "C" int up_turn(int n,int b,int m){return Game_Battle::CheckTurns(n,b,m);}
extern "C" int up_page(const Rm2kBattleCondition*c,int n,int eh,int em,int ah,int am){
 lcf::rpg::TroopPageCondition p;int f=c->flags;auto&g=p.flags;g.switch_a=f&1;g.switch_b=f&2;g.variable=f&4;g.turn=f&8;g.fatigue=f&16;g.enemy_hp=f&32;g.actor_hp=f&64;g.turn_enemy=f&128;g.turn_actor=f&256;g.command_actor=f&512;
 Main_Data::sw.a=c->switch_a;Main_Data::sw.b=c->switch_b;Main_Data::var.n=c->variable;
 p.variable_value=c->threshold;p.turn_a=c->turn_a;p.turn_b=c->turn_b;p.enemy_hp_min=c->enemy_min;p.enemy_hp_max=c->enemy_max;p.actor_hp_min=c->actor_min;p.actor_hp_max=c->actor_max;
 global_turn=n;enemy.hp=eh;enemy.maxhp=em;actor.hp=ah;actor.maxhp=am;return Game_Interpreter_Battle().AreConditionsMet(p,nullptr);
}
extern "C" int up_sim(int a,int d,int s,int ad,int as){actor.def=ad;actor.spi=as;actor.hp=999;lcf::rpg::EventCommand c;c.parameters={1,1,a,d,s,0,1,1};Game_Interpreter().CommandSimulatedAttack(c);return Main_Data::var.n;}
extern "C" void up_timer(int sec,int vis,int battle,int active_battle,int paused,int steps,int*out){
 Game_Party p;p.SetTimer(0,sec);p.StartTimer(0,vis,battle);in_battle=active_battle;for(int i=0;i<steps;i++)if(!paused)p.UpdateTimers();
 out[0]=p.data.timer1_frames;out[1]=p.data.timer1_active;out[2]=p.data.timer1_visible;out[3]=p.data.timer1_battle;out[4]=p.GetTimerSeconds(0);
}
'''
 path=ROOT/'build/shared_upstream_oracle.cpp';path.write_text(prefix+'\n'.join(bodies)+suffix)
 subprocess.run(['c++','-std=c++17','-O2','-fPIC','-shared','-Iruntime/rm2k',str(path),'-o',str(ROOT/'build/shared_upstream_oracle.so')],cwd=ROOT,check=True)
 stub=ROOT/'build/shared_native_fixture.c';stub.write_text('''#include "engine.h"
Game game;int battle_active;unsigned parallel_revision;void parallel_tick(void){}void movement_tick(void){}void pictures_tick(void){}void animations_tick(void){}void presentation_tick(void){}int variable(int id){(void)id;return 0;}void fault(int n){(void)n;}
void native_timer(int sec,int vis,int battle,int active_battle,int paused,int steps,int*out){
 int i,p[5]={0,0,sec,0,0};for(i=0;i<2;i++)game.timer_frames[i]=game.timer_active[i]=game.timer_visible[i]=game.timer_battle[i]=0;
 timer_command(p);p[0]=1;p[3]=vis;p[4]=battle;timer_command(p);battle_active=active_battle;engine_clock_paused=paused;
 for(i=0;i<steps;i++)engine_tick();out[0]=game.timer_frames[0];out[1]=game.timer_active[0];out[2]=game.timer_visible[0];out[3]=game.timer_battle[0];out[4]=timer_seconds(0);
}
''')
 subprocess.run(['cc','-std=c99','-O2','-fPIC','-shared','-ffreestanding','-Isource','-Iruntime/rm2k',str(stub),'runtime/rm2k/rm2k_rules.c','runtime/rm2k/timers.c','-o','build/shared_native_fixture.so'],cwd=ROOT,check=True)
 up=C.CDLL(str(ROOT/'build/shared_upstream_oracle.so'));native=C.CDLL(str(ROOT/'build/shared_native_fixture.so'))
 checks={};rng=random.Random(0x474241)
 def compare(un,nn,cases):
  a=getattr(up,un);b=getattr(native,nn);count=0
  for case in cases:
   a.argtypes=b.argtypes=[C.c_int]*len(case);expected=a(*case);actual=b(*case);assert actual==expected,(un,case,expected,actual);count+=1
  checks[nn]=count
 compare('up_chip','rm2k_chip_index',[(i,)for i in range(-10,10200)])
 compare('up_turn','rm2k_turn_matches',[(t,b,m)for t in range(31)for b in range(8)for m in range(8)])
 compare('up_sim','rm2k_simulated_base',[(rng.randrange(1000),rng.randrange(401),rng.randrange(801),rng.randrange(1000),rng.randrange(1000))for _ in range(3000)])
 compare('up_fatigue','rm2k_fatigue',[(h,mh,m,mm)for mh,mm in [(rng.randrange(1,1001),rng.randrange(1001))for _ in range(10000)]for h,m in [(rng.randrange(mh+1),rng.randrange(mm+1))]])
 class Condition(C.Structure):_fields_=[(n,C.c_int)for n in ['flags','switch_a','switch_b','variable','threshold','turn_a','turn_b','enemy_min','enemy_max','actor_min','actor_max']]
 up.up_page.argtypes=native.rm2k_battle_page.argtypes=[C.POINTER(Condition)]+[C.c_int]*5
 db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1];n=0
 rows=[fields(p.get(2,b''))for _,t in array(db[15])for _,p in array(t.get(11,b''))]
 def num(d,k,default=0):return integer(d.get(k,b''),default)
 for row in rows:
  for turn in [0,1,2,3,10]:
   for ratio in [0,1,20,30,50,100]:
    c=Condition(num(row,1),1,1,num(row,5),num(row,5),num(row,6),num(row,7),num(row,11),num(row,12,100),num(row,14),num(row,15,100))
    args=[turn,ratio,100,ratio,100];expected=up.up_page(C.byref(c),*args);actual=native.rm2k_battle_page(C.byref(c),*args);assert actual==expected,(c.flags,args,expected,actual);n+=1
 for _ in range(5000):
  mn=rng.randrange(101);mx=rng.randrange(mn,101);c=Condition(rng.randrange(2048),rng.randrange(2),rng.randrange(2),rng.randrange(-100,101),rng.randrange(-100,101),rng.randrange(5),rng.randrange(5),mn,mx,mn,mx)
  args=[rng.randrange(12),rng.randrange(-1,101),100,rng.randrange(-1,101),100];expected=up.up_page(C.byref(c),*args);actual=native.rm2k_battle_page(C.byref(c),*args);assert actual==expected,('page',c.flags,args,expected,actual);n+=1
 checks['original_battle_page_conditions']=n
 up.up_timer.argtypes=native.native_timer.argtypes=[C.c_int]*6+[C.POINTER(C.c_int)];n=0
 for sec in [0,1,2,60]:
  for vis in [0,1]:
   for bt in [0,1]:
    for battle in [0,1]:
     for paused in [0,1]:
      for steps in [0,1,59,60,61,119,120,3600,3660]:
       a=(C.c_int*5)();b=(C.c_int*5)();args=[sec,vis,bt,battle,paused,steps];up.up_timer(*args,a);native.native_timer(*args,b);assert list(a)==list(b),('timer',args,list(a),list(b));n+=1
 checks['original_timer_frames_and_flags']=n
 out=ROOT/'evidence/mechanisms';out.mkdir(exist_ok=True)
 report={'status':'pass','kind':'host differential checks against extracted pinned upstream functions','checks':checks,'total':sum(checks.values()),'source_lock_sha256':hashlib.sha256((ROOT/'third_party/sources.lock.json').read_bytes()).hexdigest(),'emulator_gameplay':'separate acceptance required','RPG_RT_or_hardware':'not_run','test_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'shared_rule_parity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
