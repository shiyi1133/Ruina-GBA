"""Opening-only Mode 3 preview: natural inputs and independent XYZ pixels."""
import hashlib, json, struct, sys, zipfile, zlib
from pathlib import Path
import numpy as np
from PIL import Image
from drive_opening import ROOT, Emulator
from project_env import ARCHIVE
from portrait_assets import logical


def main():
    build = json.loads((ROOT/'evidence/quality_preview/build.json').read_text())
    rom, elf = Path(build['ROM']), Path(build['ELF'])
    digest = hashlib.sha256(rom.read_bytes()).hexdigest();assert digest == build['ROM_sha256']
    out = ROOT/'evidence/quality_preview'/digest[:12];out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as z:
        names = {logical(n): n for n in z.namelist()}
        def source(folder, name):
            path='Ruina121/game/'+folder+'/'+name+'.xyz';raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);data=zlib.decompress(raw[8:]);indices=np.frombuffer(data,np.uint8,offset=768).reshape(h,w);rgb=np.frombuffer(data,np.uint8,768).reshape(256,3).astype(np.uint16)>>3;palette=rgb[:,0]|rgb[:,1]<<5|rgb[:,2]<<10
            return indices,palette,palette[indices]
        lotus=source('Picture','風景・蓮');cave=source('Panorama','背景・滝の洞窟');faces=source('FaceSet','顔絵主役');title=source('Title','廃都タイトル2')
    rows=[]
    def screen(e,path):
        e.frames(2);e.shot(path);a=np.asarray(Image.open(path).convert('RGB')).astype(np.uint16)>>3
        return a[...,0]|a[...,1]<<5|a[...,2]<<10
    def value(e,name):return struct.unpack('<I',e.memory(e.symbols[name],4))[0]
    def qstate(e):return struct.unpack('<8I',e.memory(e.symbols['quality_debug'],32))
    def palette_face_check(e,png):
        info=struct.unpack('<13I',e.memory(e.symbols['quality_faces'],52));checked=0;different=0
        for i in range(info[0]):
            image,x,y=info[1+i*3:4+i*3]
            if not 7<=image<23 or x+48>240 or y+48>160:continue
            index=image-7;sx,sy=index%4*48,index//4*48;expected=faces[2][sy:sy+48,sx:sx+48];mask=faces[0][sy:sy+48,sx:sx+48]!=0
            different+=int(np.count_nonzero((png[y:y+48,x:x+48]!=expected)&mask));checked+=int(mask.sum())
        assert different==0,(info,different)
        return checked
    for mode in (0,1):
        for origin in (1,2,3,4):
            case=out/('native'if mode==0 else'fit')/('origin_'+str(origin));case.mkdir(parents=True,exist_ok=True)
            e=Emulator(rom=rom,elf=elf);checks={};steps=[];face_pixels=0;inspected=False
            try:
                e.frames(180);e.key(0);png=screen(e,case/'title.png');title_pixels=png.copy()
                assert struct.unpack('<H',e.memory(0x04000000,2))[0]==0x0403
                checks['GBA_mode3_direct_RGB555']=True
                e.key(1)
                assert e.debug()[15]==2 and e.debug()[17]==2,('view mode menu not shown',e.debug())
                if mode:e.key(128)
                e.key(1);picked=False
                assert value(e,'quality_fit')==mode,('requested view was not selected',mode,qstate(e))
                checks['requested_view_mode_is_active']=True
                for i in range(220):
                    d=e.debug();q=qstate(e);steps.append({'step':i,'UI':d[15],'map':d[9],'event':d[7],'offset':d[8],'quality':q})
                    assert d[0]!=0x4641554c and q[0]!=3,(d,q)
                    if q[0]==2 and d[15]==4:
                        screen(e,case/'first_map.png');break
                    if d[15]==1:
                        if mode==0 and origin==1 and not inspected:
                            before=d;pause=value(e,'engine_clock_paused');e.key(4)
                            assert value(e,'quality_inspecting')==1
                            image=screen(e,case/'original_illustration.png')
                            left=(lotus[2].shape[1]-240)//2;expected=lotus[2][:160,left:left+240]
                            difference=int(np.count_nonzero(image!=expected));assert difference==0,('lotus native source',difference)
                            e.key(16);image=screen(e,case/'original_illustration_panned.png');assert not np.any(image!=lotus[2][:160,left+8:left+248])
                            e.key(2);after=e.debug();assert after[15]==1 and after[16]==before[16] and after[21]==before[21]
                            assert value(e,'engine_clock_paused')==pause
                            checks['full_illustration_inspector_exact_RGB555_and_does_not_advance_text']=True;inspected=True
                        if value(e,'quality_faces') and face_pixels==0:
                            image=screen(e,case/'dialogue_face.png');face_pixels+=palette_face_check(e,image)
                        if i in (0,4,8,10,11,14,15,16,17,18):screen(e,case/f'dialogue_{i:03}.png')
                        e.key(1)
                    elif d[15]==2:
                        if value(e,'quality_faces')==4:
                            image=screen(e,case/'four_original_faces.png');face_pixels+=palette_face_check(e,image)
                        if not picked and d[17]==4:
                            for _ in range({3:0,1:1,2:2,4:3}[origin]):e.key(128)
                            picked=True
                        e.key(1)
                    elif d[15]==3:
                        screen(e,case/'name.png');e.key(8)
                    else:e.frames(120)
                else:raise AssertionError(('opening limit',e.debug(),qstate(e)))
                checks['natural_original_opening_reaches_first_map']=qstate(e)[0]==2 and e.debug()[9]==23
                assert struct.unpack('<i',e.memory(e.symbols['game']+16,4))[0]==origin
                checks['chosen_origin_retained']=True
                checks['original_faces_have_no_palette_fitting']=face_pixels>0
                map_state=e.memory(e.symbols['game'],39704);assert value(e,'engine_clock_paused')==1
                e.key(4);assert qstate(e)[1]==1,qstate(e)
                crops=[]
                targets=[None,(0,0),(80,0),(0,80),(80,80)]if(mode==0 and origin==1)else[None]
                for target in targets:
                    if target is not None:
                        for _ in range(30):
                            q=qstate(e);x,y=q[2:4]
                            if (x,y)==target:break
                            e.key(16 if x<target[0]else 32 if x>target[0]else 128 if y<target[1]else 64)
                        else:raise AssertionError(('map pan target',target,qstate(e)))
                    q=qstate(e);x,y=q[2:4];image=screen(e,case/f'original_map_{x}_{y}.png');expected=cave[2][y:y+160,x:x+240]
                    mask=np.ones((160,240),bool)
                    for xx,yy in ((116,2),(230,76),(116,150),(2,76)):mask[yy:yy+8,xx:xx+8]=False
                    delta=int(np.count_nonzero((image!=expected)&mask));assert delta==0,(x,y,delta)
                    crops.append({'camera':[x,y],'different_source_RGB555_pixels':delta,'pixels_compared':int(mask.sum())})
                checks['first_map_original_pixels_exact_in_all_observed_crops']=True
                e.key(4);assert qstate(e)[1]==0
                assert e.memory(e.symbols['game'],39704)==map_state
                checks['exploration_mask_can_be_restored_without_story_changes']=True
                e.key(8);e.key(0);restarted=screen(e,case/'title_after_restart.png')
                assert qstate(e)[0]==0 and not np.any(restarted!=title_pixels)
                checks['restart_title_has_no_old_map_overlay']=True
                assert all(checks.values()),checks
                row={'status':'pass','origin':origin,'view':'native'if mode==0 else'fit','checks':checks,'face_pixels_compared':face_pixels,'native_map_crops':crops,'steps':steps,'commands':e.log}
                (case/'result.json').write_text(json.dumps(row,ensure_ascii=False,indent=2));rows.append({k:v for k,v in row.items()if k not in('steps','commands')});print('PASS',mode,origin,flush=True)
            except Exception as error:
                e.shot(case/'failure.png');(case/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'debug':e.debug(),'quality':qstate(e),'steps':steps,'commands':e.log},ensure_ascii=False,indent=2));raise
            finally:e.close()
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==digest
    result={'status':'pass','ROM_sha256':digest,'base_ROM_sha256':build['base_v062_ROM_sha256'],'scope':'all four original origins, both overview/native modes through first map only; actual emulated buttons, no memory writes or instant states','cases':rows,'native_map_pixels_compared':sum(c['pixels_compared']for r in rows for c in r['native_map_crops']),'different_original_RGB555_pixels':0,'face_pixels_compared':sum(r['face_pixels_compared']for r in rows),'physical_hardware':'not_run','whole_game':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='cases'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
