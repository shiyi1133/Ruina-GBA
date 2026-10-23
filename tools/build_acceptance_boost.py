"""Build an isolated, opt-in high-stat/all-learnable-skill acceptance ROM.

The ordinary v0.7.1 sources, binary and saves are never rebuilt or modified.
"""
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix
from inspect_lcf import data_root,array,integer,text,commands


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-zip');args=parser.parse_args()
    delivery_path=ROOT/'evidence/ui_v071/delivery.json'
    delivery=json.loads(delivery_path.read_text()) if delivery_path.exists() else {
        'SOURCE_ZIP':str(ROOT.parent/'废都物语_GBA_匹配工程_v0.7.1_20261023.zip'),
        'source_zip_sha256':'1c4bee4e51b6a1ecb5f494b7b80ec9d5d55337f0fb9bc1a4ad28adcea0ef53f5',
        'ROM_sha256':'738ae5637483a631e0ab109433497ac752cfc2b6ed43b94acab6b4b7e3818979'}
    archive=Path(args.source_zip or delivery['SOURCE_ZIP']);assert sha(archive)==delivery['source_zip_sha256']
    formal=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';formal_existed=formal.exists()
    formal_before=sha(formal) if formal_existed else delivery['ROM_sha256'];assert formal_before==delivery['ROM_sha256']
    stage=Path(tempfile.mkdtemp(prefix='ruina-acceptance-20261023-',dir='/tmp'))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        roots={Path(n).parts[0] for n in z.namelist()};assert len(roots)==1
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(stage)
    project=stage/next(iter(roots))
    db=data_root((project/'build/original/RPG_RT.ldb').read_bytes())[1]
    skills=dict(array(db[12]));learn=set();sources=[]
    for aid,actor in array(db[11]):
        if aid<=20:
            for _,skill in array(actor.get(63,b'')):learn.add(integer(skill.get(2)))
    for cid,c in array(db[25]):sources.append((f'common:{cid}',c.get(22,b'')))
    for tid,t in array(db[15]):
        for pid,page in array(t.get(11,b'')):sources.append((f'battle:{tid}:{pid}',page.get(12,b'')))
    for file in (project/'build/original').glob('*.lmu'):
        for eid,event in array(data_root(file.read_bytes())[1].get(81,b'')):
            for pid,page in array(event.get(5,b'')):sources.append((f'{file.name}:{eid}:{pid}',page.get(52,b'')))
    for location,stream in sources:
        for command in commands(stream):
            params=command['params']
            if command['code']==10440 and params[2]==0:
                assert params[3]==0,('unexpected dynamic skill grant',location,params)
                learn.add(params[4])
    valid=sorted(i for i in learn if i in skills and skills[i].get(1,b'').strip())
    assert all('ボ' not in text(skills[i].get(1,b'')) and 'テスト' not in text(skills[i].get(1,b'')) for i in valid)
    heroes=[i for i,a in array(db[11]) if 1<=i<=20 and a.get(1,b'').strip()]
    assert heroes==list(range(1,15))+list(range(16,21)),heroes
    items=dict(array(db[13]));weapon=items[453]
    assert integer(weapon.get(3))==1 and not integer(weapon.get(15))
    assert all(weapon.get(62,b'')[i] for i in range(4))
    attributes=dict(array(db[17]));weapon_attributes=weapon.get(66,b'')
    for sid in valid:
        if '$C' not in text(skills[sid][1]) or integer(skills[sid].get(45)):continue
        for i,flag in enumerate(skills[sid].get(44,b'')):
            if flag and integer(attributes[i+1].get(2))==0:assert i<len(weapon_attributes) and weapon_attributes[i],sid
    source='''/* Acceptance variant only. Ordinary skill costs, weapons, events,
 * damage and save format are unchanged. Grant once per fresh new game. */
#include "game.h"
static int pending;
volatile u32 acceptance_boost_trace[4];/* grants, actors, skills/actor, cap */
static const u16 actors[]={ACTORS};
static const u16 skills[]={SKILLS};
void acceptance_boost_arm(void){pending=1;memset((void*)acceptance_boost_trace,0,sizeof(acceptance_boost_trace));}
void acceptance_boost_skip(void){pending=0;}
void acceptance_boost_prepare(void){
    unsigned i,j;if(!pending||game.map==RUINA_START_MAP||!game.party_count)return;
    pending=0;
    for(i=0;i<sizeof(actors)/sizeof(actors[0]);i++){
        int id=actors[i];Actor*a=&game.actors[id];
        for(j=0;j<6;j++)a->bonus[j]=999;
        for(j=0;j<sizeof(skills)/sizeof(skills[0]);j++){
            set_learned(id,skills[j],1);if(!(j&31))audio_service();
        }
        a->hp=stat(id,0);a->mp=stat(id,1);
    }
    /* A legal one-handed magic blade supplies all spell weapon attributes.
     * Keep the selected protagonist's original weapon, with three spares
     * for manually equipping later companions. Do not loot future actors. */
    for(i=0;i<(unsigned)game.party_count;i++){
        int id=game.party[i];Actor*a=&game.actors[id];
        if(id>=1&&id<=4){int old=a->equipment[0];
            if(old&&old!=453)game.items[old]=clamp(game.items[old]+1,0,99);
            a->equipment[0]=453;
        }
    }
    game.items[453]=clamp(game.items[453]+3,0,99);
    acceptance_boost_trace[0]++;acceptance_boost_trace[1]=sizeof(actors)/sizeof(actors[0]);
    acceptance_boost_trace[2]=sizeof(skills)/sizeof(skills[0]);acceptance_boost_trace[3]=999;
}
'''.replace('ACTORS',','.join(map(str,heroes))).replace('SKILLS',','.join(map(str,valid)))
    (project/'source/acceptance_boost.c').write_text(source)
    def replace(path,old,new):
        p=project/path;s=p.read_text();assert s.count(old)==1,(path,old);p.write_text(s.replace(old,new))
    replace('source/game.h','void init_game(void);','void init_game(void);\nvoid acceptance_boost_arm(void);\nvoid acceptance_boost_skip(void);\nvoid acceptance_boost_prepare(void);')
    replace('source/ruina_adapter.c','engine_init(seed);','engine_init(seed);acceptance_boost_arm();')
    replace('source/maps.c','void map_screen(void){world_screen();}','void map_screen(void){acceptance_boost_prepare();world_screen();}')
    replace('source/maps.c','队伍状态 · 原始数值','队伍状态 · 验收版')
    replace('source/game.c','开始游戏/继续游戏/制作信息/音乐欣赏','开始游戏（验收版）/继续游戏/制作信息/音乐欣赏')
    replace('source/game.c','audio_restore();}','acceptance_boost_skip();audio_restore();}')
    replace('tools/build.py',"b'RUB7'","b'RUA7'")
    replace('tools/build.py',"report['version']='0.7.1'","report['version']='0.7.1-acceptance'")
    replace('tools/build.py','evidence/ui_v071/current_validation.json','evidence/acceptance_boost_20261023/validation.json')
    # All menu glyphs already exist; keep every image and font row byte-identical.
    glyphs={int(x) for x in re.search(r'glyph_codes\[[^]]+\]=\{([^}]+)\}',(project/'build/assets.c').read_text()).group(1).split(',')}
    assert all(int.from_bytes(c.encode('gbk'),'big') in glyphs for c in '开始游戏（验收版）')
    env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_acceptance_original.zip',RUINA_FONT='/nonexistent_acceptance_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_acceptance_asset_python')
    out=ROOT/'evidence/acceptance_boost_20261023';out.mkdir(parents=True,exist_ok=True)
    with (out/'build.log').open('w') as stream:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    rom=project/'build/废都物语_GBA_开篇开发验证版.gba';elf=project/'build/ruina_opening_dev.elf';assert (sha(formal)==formal_before) if formal_existed else not formal.exists()
    baseline=json.loads((ROOT/'build/build_receipt.json').read_text());receipt=json.loads((project/'build/build_receipt.json').read_text())
    changed=[p for p,h in receipt['compiler_inputs_sha256'].items() if baseline['compiler_inputs_sha256'].get(p)!=h]
    assert set(changed)=={'source/acceptance_boost.c','source/game.h','source/game.c','source/maps.c','source/ruina_adapter.c'},changed
    report={'status':'built_not_tested','variant':'v0.7.1-acceptance','project':str(project),'ROM':str(rom),'ELF':str(elf),'ROM_sha256':sha(rom),'ROM_bytes':rom.stat().st_size,'baseline_ROM_sha256':formal_before,'baseline_source_ZIP_sha256':sha(archive),'actors':heroes,'skills':[{'id':i,'name':text(skills[i][1])} for i in valid],'skill_count':len(valid),'magic_count':sum('$C' in text(skills[i][1]) for i in valid),'source_of_skills':'union of original real actor learning tables and all literal Learn Skill commands, excluding empty skill records','stats':{'HP':999,'MP':999,'attack':999,'defense':999,'magic':999,'speed':999},'level':'original','application':'once after original character creation, immediately before first playable map; loading a save does not regrant or heal','starting_weapon':{'id':453,'name':text(weapon[1]),'original_weapon':'kept in inventory','spares':3,'legal_for_all_four_origins':True,'all_65_spell_weapon_requirements_satisfied':True},'changed_compiler_inputs':changed,'unmodified':'all runtime rules, original game data, images, fonts, music, story switches, money and SRAM format','production_untouched':True}
    (out/'build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='skills'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
