"""Inventory original event requirements; presence of a case is not acceptance.
This deliberately reports partial and unsupported commands for the full game.
"""
import collections,hashlib,json,re
from inspect_lcf import ROOT,data_root,array,commands
def main():
 lock=json.loads((ROOT/'third_party/sources.lock.json').read_text())
 for f in lock['files']:
  p=ROOT/'third_party'/f['project']/f['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],str(p)
 enum_text=(ROOT/'runtime/rm2k/rm2k_commands.h').read_text()
 enum={name:int(n)for name,n in re.findall(r'(RM2K_\w+)\s*=\s*(\d+)',enum_text)}
 upstream=(ROOT/'third_party/liblcf/src/generated/lcf/rpg/eventcommand.h').read_text()
 expected={'RM2K_'+name:int(n)for name,n in re.findall(r'^\s*(\w+)\s*=\s*(\d+),?',upstream,re.M)}
 assert enum==expected,'Native command IDs drifted from pinned liblcf'
 source=(ROOT/'runtime/rm2k/interpreter.c').read_text();cases={enum[n]for n in re.findall(r'case\s+(RM2K_\w+)\s*:',source)}|{0,10}
 names={n:k.removeprefix('RM2K_')for k,n in enum.items()};names[0]='CommandStreamEnd'
 visual={11010,11020,11030,11040,11050,11060,11070,11120,11210,11310,11320,11340,10630,10680,10690,11720}
 partial={10710:'Shared battle rules and original event pages implemented; late-game combinations receive spot checks, full campaign acceptance belongs to the user',10110:'Original text, variables, names, choices and paging retained; typewriter/color/wait glyph effects simplified for GBA',10690:'All scene transitions cut to black while preparing the next image, then show its final state without fades. Original transition style settings are not reproduced'}
 counts=collections.Counter();examples={};forms=collections.defaultdict(collections.Counter);mapmax=0;largest_map=0;map_pages=0;troop_pages=0;parallel_pages=0;route_ops=collections.Counter();routes=0;repeat_routes=0;capacities={}
 profile=(ROOT/'source/game_profile.h').read_text()
 limits={k:int(v)for k,v in re.findall(r'#define (MAX_\w+) (\d+)',profile)}
 def embedded(par,index):
  n=0
  for _ in range(5):
   b=par[index];index+=1;n=(n<<7)|(b&127)
   if not b&128:return n,index
  raise ValueError('invalid movement integer')
 for path in sorted((ROOT/'build/original').iterdir()):
  if path.suffix not in ('.ldb','.lmu'):continue
  db=data_root(path.read_bytes())[1];streams=[]
  if path.suffix=='.lmu':
   entries=array(db.get(81,b''));maximum=max([i for i,_ in entries]or[0])
   if maximum>mapmax:mapmax=maximum;largest_map=path.name
   for eid,e in entries:
    for pid,p in array(e.get(5,b'')):
     map_pages+=1;parallel_pages+=int(int.from_bytes(p.get(33,b'\0'),'big')==4);streams.append((f'{path.name}/event{eid}/page{pid}',p.get(52,b'')))
  else:
   for table,cap in [(11,'MAX_ACTOR'),(12,'MAX_SKILL'),(13,'MAX_ITEM'),(14,'MAX_ENEMY'),(15,'MAX_TROOP'),(17,'MAX_ATTRIBUTE'),(18,'MAX_STATE'),(23,'MAX_SWITCH'),(24,'MAX_VAR'),(25,'MAX_COMMON')]:
    maximum=max([i for i,_ in array(db.get(table,b'\0'))]or[0]);capacities[cap]={'capacity':limits[cap],'original_maximum':maximum,'fits':maximum<=limits[cap]};assert maximum<=limits[cap]
   for cid,c in array(db.get(25,b'')):streams.append((f'common{cid}',c.get(22,b'')))
   for tid,t in array(db.get(15,b'')):
    members=array(t.get(2,b'\0'));assert len(members)<=limits['MAX_BATTLE_ENEMY'],(tid,len(members))
    for pid,p in array(t.get(11,b'')):
     assert pid<=limits['MAX_BATTLE_PAGE'];troop_pages+=1;streams.append((f'troop{tid}/page{pid}',p.get(12,b'')))
  for location,stream in streams:
   for c in commands(stream):
    counts[c['code']]+=1;examples.setdefault(c['code'],location)
    par=c['params']
    if par and c['code']in(12010,13310,10220,10210):forms[c['code']][str(par[0] if c['code']!=10220 else par[4])]+=1
    if c['code']==11330:
     routes+=1;repeat_routes+=bool(par[2]);at=4
     while at<len(par):
      op=par[at];at+=1;route_ops[op]+=1
      if op in(32,33):_,at=embedded(par,at)
      elif op in(34,35):
       n,at=embedded(par,at);at+=n
       for _ in range(1 if op==34 else 3):_,at=embedded(par,at)
     assert at==len(par)
 capacity=int(re.search(r'#define MAX_EVENT (\d+)',(ROOT/'source/game_profile.h').read_text())[1]);assert mapmax<capacity
 rows=[]
 for code,count in sorted(counts.items()):
  category='unsupported'if code not in cases else 'partial'if code in partial else 'visual adaptation'if code in visual else 'implemented subset; runtime acceptance separate'
  rows.append({'code':code,'name':names.get(code,'unknown'),'occurrences':count,'category':category,'example':examples[code],'limit':partial.get(code)})
 out=ROOT/'evidence/refactor';out.mkdir(exist_ok=True)
 gaps=[
  {'feature':'原版地图探索与触发','status':'implemented_with_spot_checks','gap':'真实步行、接触、通行、强制移动已接入；本作8205页事件均为固定自主移动类型，未宣称支持任意RM2000自主AI'},
  {'feature':'图片与特殊地图界面','status':'implemented_with_spot_checks','gap':'通用图片合成、坐标/缩放/透明度与实际底图已接入；手册、世界地图、锻造、制甲有独立GBA按键抽查'},
  {'feature':'动画表现','status':'reduced_by_user_request','gap':'转场直接黑屏后显示新图，色调和透明度动画直接取端点；技能用短闪光和原音效，雨雪静态覆盖；独立事件等待与实质判定保留，见动画简化说明.txt'},
  {'feature':'战斗数值与状态','status':'implemented_with_spot_checks','gap':'已有原函数对照、全部原状态命中组合和双击/全体武器检查；未宣称所有后期组合均经过自然游玩'},
  {'feature':'称号、制作、料理、调和','status':'implemented_with_spot_checks','gap':'沿用原事件和配方条件；指定称号、料理、调和及锻造制甲抽查，全部配方枚举非人工试玩'},
  {'feature':'存读档','status':'implemented_with_spot_checks','gap':'v5将39704字节Game压入32KiB SRAM，读取v2/v3/v4/v5；后期受控状态压缩往返已验，当前构建冷读档另计'},
  {'feature':'完整音频','status':'simplified_profile_validation_separate','gap':'全部99首MIDI、6首WAV和218音效进入单卡，游戏和欣赏均用用户确认的简化音色；完整乐谱、循环、GBA时钟与队列压力报告分别绑定当前来源，不以旧全音源实验代表当前简化版'},
  {'feature':'完整剧情与结局','status':'user_playthrough_not_run','gap':'原LCF事件未逐章改写；按用户分工，仅做功能与流程抽查，完整自然通关及实机验收由用户进行'},
 ]
 report={'status':'audit_complete','source_lock_verified':True,'command_ids_match_pinned_liblcf':True,'commands_observed':sum(counts.values()),'map_event_capacity':capacity,'largest_original_map_event_id':mapmax,'largest_map':largest_map,'database_capacities':capacities,'battle_enemy_capacity':limits['MAX_BATTLE_ENEMY'],'original_map_pages':map_pages,'original_troop_pages':troop_pages,'parallel_map_pages':parallel_pages,'operand_forms':{str(k):dict(v)for k,v in forms.items()},'forced_movement':{'routes':routes,'repeating_routes':repeat_routes,'opcodes':dict(sorted(route_ops.items()))},'work_order':['feature completeness and execution spot checks','runtime performance after functional acceptance'],'full_game_compatibility':'not_complete','all_features_can_be_completed':'not_confirmed_by_existing_tests','functional_gaps':gaps,'commands':rows}
 (out/'compatibility_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False))
 print('unsupported',[(r['code'],r['name'],r['occurrences'])for r in rows if r['category']=='unsupported'])
if __name__=='__main__':main()
