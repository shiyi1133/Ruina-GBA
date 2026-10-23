"""Package only the frozen playable demo; development experiments stay separate."""
import hashlib,json,shutil,zipfile
from pathlib import Path
from project_env import ROOT

def main():
 report=json.loads((ROOT/'evidence/demo_20261021/result.json').read_text());assert report['status']=='pass'
 source=ROOT/'history/pre_native_playback_20261021/废都物语_GBA_开篇开发验证版.gba';digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest==report['rom_sha256']
 name='废都物语_GBA_DEMO_20261021';folder=ROOT/'交付'/name;folder.mkdir(parents=True,exist_ok=True)
 rom=folder/'废都物语_GBA_DEMO_v0.3.gba';shutil.copy2(source,rom)
 text='''废都物语 GBA DEMO · 开发试玩版 v0.3

这是当前可试玩的功能版本，还不是完整移植成品。当前版本可能还有问题。
使用 GBA 模拟器打开“废都物语_GBA_DEMO_v0.3.gba”，选择新游戏即可。

本次抽查：新游戏开场、原作出身与取名、地图实际行走、调查入口、第一场战斗及胜利后剧情。
已另行抽查：手册、世界地图、武器制作、防具制作，以及普通存档冷启动。
剧情、人物数值和事件读取原作数据；图像与界面适配 GBA。

操作提示：
方向键行走，A 调查或确定，B 返回，START 打开菜单。
L / R 可切换地图调查点；A 会沿可通行路线走过去调查；L+R 只走过去。
在允许保存的地方，可通过菜单保存普通 SAV。
模拟器的键盘/手柄按键请以你自己的映射设置为准。

尚在开发：后期配乐、部分后期功能核对和整体效率优化。
复杂场景的绘制仍偏慢；后续剧情与全部结局没有完整通关验收。
本 DEMO 的配乐使用已验证的开篇音频方案。全曲实时播放器仍在另行开发。

建议从新游戏开始体验。请保留你原有的游戏与存档；该文件使用独立名称。
遇到问题，请记录所选出身、所在场景、操作步骤，最好附上普通 SAV。
本次交付后会继续开发；完整流程验收由玩家进行，开发侧进行抽查。
'''
 (folder/'试玩说明.txt').write_text(text,encoding='utf-8-sig')
 shutil.copy2(ROOT/'evidence/demo_20261021/result.json',folder/'本次抽查记录.json')
 for n in ['opening_cave.png','walking.png','first_battle.png','first_victory.png']:
  p=ROOT/'evidence/demo_20261021'/n
  if p.exists():shutil.copy2(p,folder/n)
 receipt={'name':name,'rom':rom.name,'bytes':rom.stat().st_size,'sha256':digest,'full_game_port':False,'native_full_music_experiment_included':False,'spot_check':report['checks'],'unverified':['all later scenarios and endings','full game performance','hardware']}
 (folder/'交付校验.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 archive=folder.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(folder.rglob('*')):
   if p.is_file():z.write(p,Path(name)/p.relative_to(folder))
 with zipfile.ZipFile(archive)as z:assert z.testzip()is None;assert hashlib.sha256(z.read(name+'/'+rom.name)).hexdigest()==digest
 downloads=Path('/mnt/c/Users/APP/Downloads');target=downloads/name;shutil.copytree(folder,target,dirs_exist_ok=True);shutil.copy2(archive,downloads/archive.name)
 assert hashlib.sha256((target/rom.name).read_bytes()).hexdigest()==digest
 print(json.dumps({'zip':str(downloads/archive.name),'rom':str(target/rom.name),'rom_sha256':digest,'zip_bytes':archive.stat().st_size,'spot_check':'pass'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
