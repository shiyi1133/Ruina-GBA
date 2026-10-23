"""Extract UI labels only. Recipes, prices, checks and rewards stay in LCF.

Each label records its original command location. Native navigation selects an
original map event; it never evaluates or replaces a recipe/title rule.
"""
import json
from inspect_lcf import ROOT,data_root,array,commands,fields,integer,text
MENUS=(13,14,15,18,19,22)
def literal(s):return '"'+''.join('\\%03o'%b for b in s.encode('gbk'))+'"'
def main():
 db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1]
 items=dict(array(db[13]));rows=[]
 controls={(13,1):'开始调理',(13,2):'返回',
           (22,3):'返回',(22,4):'称号与SP说明',(22,5):'特技修炼',(22,6):'大河神殿'}
 for mid in MENUS:
  path=ROOT/f'build/original/Map{mid:04d}.lmu'
  for eid,event in array(data_root(path.read_bytes())[1].get(81,b'')):
   if mid==13 and eid in (5,6):continue # Original graphical cursor navigation.
   if mid==22 and eid==2:continue # Hidden helper, called after a title selection.
   pages=[(pid,p,commands(p.get(52,b'')))for pid,p in array(event.get(5,b''))]
   if not any(integer(p.get(33,b''))==0 and any(c['code'] not in (0,10,12410,22410)for c in cc)for _,p,cc in pages):continue
   label=controls.get((mid,eid),'');origin='native navigation label' if label else ''
   if not label and eid==3 and mid!=13:label='返回';origin='native navigation label'
   if not label and mid==18:
    for pid,p,cc in pages:
     condition=fields(p.get(2,b''));item_id=integer(condition.get(6,b''))
     if integer(condition.get(1,b''))&8 and item_id in items:
      label=text(items[item_id].get(1,b''));origin=f'page{pid}/condition/item{item_id}';break
   if not label:
    for pid,p,cc in pages:
     for index,c in enumerate(cc):
      par=c['params']
      if c['code']==10610 and par and par[0]in(75,96):
       label=c['text'];origin=f'page{pid}/command{index}';break
     if label:break
   if not label:
    for pid,p,cc in pages:
     for index,c in enumerate(cc):
      par=c['params']
      if c['code']==10320 and len(par)>=5 and par[:2]==[0,0] and par[2]in items:
       label=text(items[par[2]].get(1,b''));origin=f'page{pid}/command{index}/item{par[2]}';break
     if label:break
   if not label:
    for pid,p,cc in pages:
     for index,c in enumerate(cc):
      if c['code']==10110 and c['text'].strip() not in ('','\\^'):
       label=c['text'].split('／')[0].split('\n')[0];origin=f'page{pid}/command{index}';break
     if label:break
   if label:rows.append({'map':mid,'event':eid,'label':label,'origin':origin})
 lines=['/* Generated UI labels; all gameplay remains in original_lcf.bin. */',
        '#include "../source/source_menus.h"','const SourceMenuLabel source_menu_labels[]={']
 lines += ['    {%d,%d,%s},'%(r['map'],r['event'],literal(r['label']))for r in rows]
 lines += ['};','const unsigned source_menu_label_count=sizeof(source_menu_labels)/sizeof(source_menu_labels[0]);','']
 (ROOT/'build/source_menu_labels.c').write_text('\n'.join(lines))
 (ROOT/'build/source_menu_manifest.json').write_text(json.dumps({'kind':'labels only; original event semantics retained','entries':rows},ensure_ascii=False,indent=2))
 print(json.dumps({'native_menu_labels':len(rows)}))
if __name__=='__main__':main()
