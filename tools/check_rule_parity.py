"""Differentially test the native pure-rule adapter against real pinned source.

The C++ oracle bodies are extracted from upstream files, not rewritten copies
of the native implementation. Host rule checks are separate from GBA gameplay.
"""
import ctypes as C,hashlib,json,random,subprocess
from pathlib import Path
from inspect_lcf import ROOT,data_root,array,integer
def extract(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=1;end=brace+1
 while depth:
  if text[end]=='{':depth+=1
  elif text[end]=='}':depth-=1
  end+=1
 return text[start:end]
def main():
 reference=ROOT/'third_party/Player/src';algo=(reference/'algo.cpp').read_text();actor=(reference/'game_actor.cpp').read_text();variables=(reference/'game_variables.cpp').read_text()
 selected=[extract(algo,'int '+name+'(')for name in ['VarianceAdjustEffect','AdjustDamageForDefend','CalcNormalAttackEffect','CalcSkillEffect','CalcSkillCost']]
 selected.append(extract(actor,'int Game_Actor::CalculateExp('))
 selected += [extract(variables,'constexpr Var_t '+name+'(')for name in ['VarSet','VarAdd','VarSub','VarMult','VarDiv','VarMod']]
 prefix=r'''
#include <algorithm>
#include <vector>
#include <limits>
#include <cstdint>
using std::min;using std::max;using Var_t=int;
#define EP_UNLIKELY(x) (x)
#define EP_LIKELY(x) (x)
namespace lcf { namespace rpg {
struct Class {int exp_base,exp_inflation,exp_correction;};
struct Actor {int exp_base,exp_inflation,exp_correction;};
struct System {enum BattleCondition {BattleCondition_none};int easyrpg_alternative_exp=0;};
struct Skill {enum SpType{SpType_fixed,SpType_percent};int power=0,physical_rate=0,magical_rate=0,variance=0,sp_type=0,sp_percent=0,sp_cost=0,scope=0;bool ignore_defense=false,easyrpg_affected_by_row_modifiers=false;};
} namespace Data {std::vector<rpg::Class> classes;std::vector<rpg::Actor> actors(1);rpg::System system;}
namespace ReaderUtil {template<class T> const T*GetElement(const std::vector<T>&v,int id){return id>0&&id<=(int)v.size()?&v[id-1]:nullptr;}}
}
class Game_Actor {public:struct{int class_id=0;}data;int GetId()const{return 1;}int MaxExpValue()const{return 999999;}int CalculateExp(int level)const;};
namespace Player {bool IsLegacy(){return false;}bool IsRPG2k(){return true;}bool IsRPG2k3(){return false;}}
namespace Rand {int roll;int GetRandomNumber(int,int){return roll;}}
struct Game_Battler {enum Weapon{WeaponAll};int atk=0,def=0,spi=0;bool defend=false,strong=false;int GetAtk(Weapon=WeaponAll)const{return atk;}int GetDef()const{return def;}int GetSpi()const{return spi;}bool IsDefending()const{return defend;}bool HasStrongDefense()const{return strong;}};
namespace Feature {bool HasRow(){return false;}}
bool IsRowAdjusted(const Game_Battler&,lcf::rpg::System::BattleCondition,bool,bool){return false;}
namespace Attribute {int ApplyAttributeNormalAttackMultiplier(int v,const Game_Battler&,const Game_Battler&,Game_Battler::Weapon){return v;}int ApplyAttributeSkillMultiplier(int v,const Game_Battler&,const lcf::rpg::Skill&){return v;}}
bool SkillTargetsEnemies(const lcf::rpg::Skill&s){return s.scope<2;}
'''
 suffix=r'''
extern "C" int up_exp(int b,int i,int c,int lv){lcf::Data::actors[0]={b,i,c};return Game_Actor().CalculateExp(lv);}
extern "C" int up_variance(int b,int v,int r){Rand::roll=r;return VarianceAdjustEffect(b,v);}
extern "C" int up_defend(int n,int d,int s){Game_Battler b;b.defend=d;b.strong=s;return AdjustDamageForDefend(n,b);}
extern "C" int up_normal(int a,int d){Game_Battler s,t;s.atk=a;t.def=d;return CalcNormalAttackEffect(s,t,Game_Battler::WeaponAll,false,false,false,lcf::rpg::System::BattleCondition_none,false);}
extern "C" int up_skill(int p,int ph,int ma,int a,int sp,int d,int ts,int hostile,int ignore){Game_Battler s,t;s.atk=a;s.spi=sp;t.def=d;t.spi=ts;lcf::rpg::Skill sk;sk.power=p;sk.physical_rate=ph;sk.magical_rate=ma;sk.scope=hostile?0:3;sk.ignore_defense=ignore;return CalcSkillEffect(s,t,sk,false,false,lcf::rpg::System::BattleCondition_none,false);}
extern "C" int up_cost(int c,int h){lcf::rpg::Skill s;s.sp_cost=c;return CalcSkillCost(s,100,h);}
extern "C" int up_var(int a,int b,int op){int n;switch(op){case 0:n=VarSet(a,b);break;case 1:n=VarAdd(a,b);break;case 2:n=VarSub(a,b);break;case 3:n=VarMult(a,b);break;case 4:n=VarDiv(a,b);break;default:n=VarMod(a,b);}return std::max(-999999,std::min(n,999999));}
'''
 generated=ROOT/'build/upstream_rule_oracle.cpp';generated.write_text(prefix+'\n'.join(selected)+suffix)
 oracle_path=ROOT/'build/upstream_rule_oracle.so';native_path=ROOT/'build/native_rules.so'
 subprocess.run(['c++','-std=c++17','-O2','-fPIC','-shared',str(generated),'-o',str(oracle_path)],check=True)
 subprocess.run(['cc','-std=c99','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared',str(ROOT/'runtime/rm2k/rm2k_rules.c'),'-o',str(native_path)],check=True)
 native=C.CDLL(str(native_path));oracle=C.CDLL(str(oracle_path));rng=random.Random(0x5255494e);counts={}
 def compare(name,native_name,cases):
  a=getattr(oracle,name);b=getattr(native,native_name);n=0
  for values in cases:
   a.argtypes=b.argtypes=[C.c_int]*len(values);expected=a(*values);actual=b(*values)
   assert actual==expected,(name,values,expected,actual)
   n+=1
  counts[native_name]=n
 db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1]
 curves={(integer(a.get(41,b''),30),integer(a.get(42,b''),30),integer(a.get(43,b'')))for _,a in array(db[11])}
 compare('up_exp','rm2k_exp',[(b,i,c,level)for b,i,c in curves for level in range(51)])
 compare('up_normal','rm2k_normal_base',[(a,d)for a in [1,2,3,4,9,31,99,999]for d in range(1,1000)])
 compare('up_skill','rm2k_skill_base',[(rng.randrange(1000),rng.randrange(11),rng.randrange(11),rng.randrange(1,1000),rng.randrange(1,1000),rng.randrange(1,1000),rng.randrange(1,1000),rng.randrange(2),rng.randrange(2))for _ in range(12000)])
 compare('up_cost','rm2k_skill_cost',[(c,h)for c in range(1000)for h in (0,1)])
 compare('up_defend','rm2k_defend',[(n,d,s)for n in range(-100,1000)for d in (0,1)for s in (0,1)])
 cases=[]
 for b in [-100,0,1,2,3,10,99,999]:
  for v in range(11):
   adj=max(1,v*b//10)if v>0 and b>0 else 0
   for roll in sorted({0,adj//2,adj}):cases.append((b,v,roll))
 compare('up_variance','rm2k_variance',cases)
 pairs=[(a,b,op)for a in [-999999,-1,0,1,999999]for b in [-999999,-1,0,1,999999]for op in range(6)]
 pairs += [(rng.randrange(-999999,1000000),rng.randrange(-999999,1000000),rng.randrange(6))for _ in range(5000)]
 compare('up_var','rm2k_variable_op',pairs)
 out=ROOT/'evidence/refactor';out.mkdir(exist_ok=True)
 report={'status':'pass','kind':'host differential rule checks against extracted pinned upstream functions','engine_profile':{'rpg2k':True,'major_updated':True,'english':False},'checks':counts,'total':sum(counts.values()),'upstream_lock_sha256':hashlib.sha256((ROOT/'third_party/sources.lock.json').read_bytes()).hexdigest(),'native_source_sha256':hashlib.sha256((ROOT/'runtime/rm2k/rm2k_rules.c').read_bytes()).hexdigest(),'original_RPG_RT_execution':'not_run','gba_gameplay':'separate acceptance reports','not_covered':['complete attribute/state rules','enemy AI','battle events','all original engine behaviours']}
 (out/'rule_parity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
