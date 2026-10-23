"""Bundle verified source/ROM and publish the explicitly requested public repo.

No upload occurs during bundle. Publish verifies local hashes before creating
or changing the dedicated Ruina-GBA repository and its draft v0.7 release.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,tempfile,time,zipfile
from pathlib import Path
from project_env import ROOT
from deliver_balanced import BASE,STATE,current,ROM_NAME,sha,read,write
PUBLIC=BASE/'public_project.json'
REPO='shiyi1133/Ruina-GBA'
COMBINED='废都物语_GBA_v0.7_工程与试玩ROM_20261023.zip'
README='''# 废都物语 GBA 移植原型

把《Ruina 废都物语》的原始事件数据与规则接到原生 GBA 运行时的实验工程。供爱好者参考、修改与继续完善。

[v0.7 下载：工程与试玩 ROM](https://github.com/shiyi1133/Ruina-GBA/releases/tag/v0.7)

解压合集后，`试玩/` 中的 `.gba` 可直接用 GBA 模拟器打开；`工程/` 是与它匹配的源码和转换资源。
这版包含完整游戏数据，可继续游玩，支持普通 SAV；**全流程、全部结局和实机尚未验收**。

![首次地图](docs/首次地图.png)
![战斗选项](docs/战斗选项.png)

## v0.7 的主要变化

- 地图和人物保留原尺寸，通过滚动查看；光标、边缘箭头、文字与地图分层。
- 头像保留独立 RGB555 颜色；插图与战斗适配 240×160，部分原动画简化为切换。
- 菜单只更新变化的区域。战斗支持逐级 B 返回并保留上级选择，取消不消耗资源。
- 游戏与音乐欣赏均用简化音色，游戏过程中进一步简化。
- 剧情、技能数值、物品、配方、敌人与奖励数据保持原包内容。

这是有选择的 RM2000 兼容运行时，**并非完整 EasyRPG Player 的 GBA 移植**。颜色、分辨率与部分演出仍受 GBA 限制。

## 构建

已验证 Linux/WSL + Python 3 + GNU Arm Embedded 13.2.1：

```sh
python3 tools/build.py --incremental
```

输出为 `build/废都物语_GBA_开篇开发验证版.gba`。可通过 `ARM_TOOLCHAIN_PREFIX` 指定 `arm-none-eabi-` 前缀。
已转换资源随工程提供，正常重建不需要原 ZIP、系统字体或 Python 图像库。Windows 原生构建尚未验证。

重新转换素材时设置 `RUINA_SOURCE_ARCHIVE`、`RUINA_FONT`，并安装 Pillow/NumPy。详细操作见 `工程使用说明.txt` 与 `README.txt`。

## 工程入口与验证

- `runtime/rm2k/`：事件、战斗、地图、物品、存档等共用逻辑。
- `platform/gba/`：GBA 显示、音频、按键与存储。
- `source/`：本作启动、特殊列表和音乐欣赏。
- `build/`：保留的转换资源；编译产物由构建命令生成。
- `tools/validate_balanced.py`：当前验证入口，需外部 mGBA 开发库、C 编译器和图像库。
- `evidence/`：各版真实测试结果，包含失败、拒绝和未运行记录；请核对报告中的 ROM SHA-256。

发行包的源码 ZIP 已新解压重建，并与试玩 ROM 逐字节核对。模拟器抽查覆盖四种出身、首战、第一 CP、菜单返回、普通存档恢复和画面/声音专项，不能代替完整通关。

## 来源和许可

引擎及工具采用 GPL-3.0-or-later；上游代码及许可见 `third_party/`、`sources.lock.json` 与 `LICENSE`。
原游戏素材及汉化、修复内容保留各自权利归属。完整来源和署名见 `CREDITS.txt`。
'''

def run(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True).strip()
def bundle():
    receipt=current();state=read(STATE);assert state['status']=='sealed, not delivered' and receipt['sha256']==state['rom_sha256']
    for key in('source_zip','demo_zip'):assert sha(Path(state[key]))==state[key+'_sha256']
    stage=Path(state['stage']);source_zip=Path(state['source_zip']);demo=Path(state['demo']);combined=stage/COMBINED;expected={}
    intro='''试玩：打开“试玩”目录中的 GBA 文件。使用普通 SAV；保留自己的旧版本与存档备份。
工程：进入“工程”目录，阅读“工程使用说明.txt”。源码与试玩 ROM 已逐字节重建核对。
完整自然通关、全部结局及实机尚未验收，供爱好者继续测试和改进。
'''
    with zipfile.ZipFile(combined,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        def put(name,data):z.writestr('废都物语_GBA_v0.7/'+name,data);expected[name]=hashlib.sha256(data).hexdigest()
        with zipfile.ZipFile(source_zip)as source:
            for name in source.namelist():put('工程/'+str(Path(*Path(name).parts[1:])),source.read(name))
        for p in sorted(demo.rglob('*')):
            if p.is_file():put('试玩/'+str(p.relative_to(demo)),p.read_bytes())
        put('先看这里.txt',intro.encode('utf-8-sig'))
        put('文件校验.json',json.dumps({'ROM_sha256':receipt['sha256'],'files':expected.copy()},ensure_ascii=False,indent=2).encode())
    with zipfile.ZipFile(combined)as z:
        assert z.testzip()is None and len(z.namelist())==len(set(z.namelist()))
        assert sum(Path(n).suffix.lower()=='.gba'for n in z.namelist())==1
        for name,digest in expected.items():assert hashlib.sha256(z.read('废都物语_GBA_v0.7/'+name)).hexdigest()==digest,name
    destination=Path(tempfile.mkdtemp(prefix='ruina-public-source-',dir='/tmp'))
    with zipfile.ZipFile(source_zip)as z:z.extractall(destination);root=destination/Path(z.namelist()[0]).parts[0]
    assert not(root/'.git').exists();(root/'README.md').write_text(README)
    (root/'.gitignore').write_text('__pycache__/\n*.pyc\n/build/*.o\n/build/*.elf\n/build/*.gba\n/build/*.map\n/build/*.su\n/build/fixtures/\n/build/gba_acceptance_probe\n')
    (root/'.gitattributes').write_text('* -text\n')
    docs=root/'docs';docs.mkdir();
    for name in('首次地图.png','战斗选项.png','制作信息.png'):shutil.copy2(demo/'实际截图'/name,docs/name)
    assert '胖胖'not in README and '咩咩'not in README
    forbidden=re.compile(rb'(?:github_pat_[A-Za-z0-9_]{30,}|gh[pousr]_[A-Za-z0-9]{30,})')
    for p in root.rglob('*'):
        if not p.is_file():continue
        assert p.stat().st_size<100*1024*1024,('GitHub file too large',p)
        if p.suffix in('.py','.json','.txt','.md','.sh','.toml','.yml'):assert not forbidden.search(p.read_bytes()),('token-shaped text in public source',p)
    info={'status':'bundled_not_published','ROM_sha256':receipt['sha256'],'combined':str(combined),'combined_sha256':sha(combined),'combined_bytes':combined.stat().st_size,'combined_files_checked':len(expected),'source_zip_sha256':sha(source_zip),'demo_zip_sha256':sha(Path(state['demo_zip'])),'public_source':str(root),'repo':REPO,'assets':[str(combined),state['source_zip'],state['demo_zip']],'prepared_unix':time.time()};write(PUBLIC,info);print(json.dumps(info,ensure_ascii=False,indent=2))

def publish():
    receipt=current();state=read(STATE);info=read(PUBLIC);assert info['ROM_sha256']==state['rom_sha256']==receipt['sha256']
    assert sha(Path(info['combined']))==info['combined_sha256']
    for key in('source_zip','demo_zip'):assert sha(Path(state[key]))==state[key+'_sha256']==info[key+'_sha256']
    root=Path(info['public_source']);assert info['repo']==REPO
    identity=json.loads(run(['gh','api','user']));assert identity['login']=='shiyi1133'and identity['id']==224809678
    if not(root/'.git').exists():
        run(['git','init','-b','main',str(root)]);run(['git','config','user.name','shiyi1133'],root);run(['git','config','user.email','224809678+shiyi1133@users.noreply.github.com'],root)
        run(['git','add','--all'],root);run(['git','commit','-m','Release playable v0.7 with balanced graphics and battle menu fixes'],root)
    commit=run(['git','rev-parse','HEAD'],root);assert not run(['git','status','--porcelain'],root)
    if not info.get('repository_created'):
        # Creation fails on an unrelated existing repository instead of reusing it.
        url=run(['gh','repo','create',REPO,'--public','--description','Ruina GBA 移植原型：原生运行时、均衡画质试玩与匹配工程'])
        info.update(repository_created=True,repository_url='https://github.com/'+REPO,commit=commit);write(PUBLIC,info)
        run(['git','remote','add','origin','https://github.com/'+REPO+'.git'],root)
    run(['git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential','push','-u','origin','main'],root)
    repo=json.loads(run(['gh','repo','view',REPO,'--json','isPrivate,url,defaultBranchRef']));assert repo['isPrivate']is False and repo['defaultBranchRef']['name']=='main'
    assert run(['gh','api','repos/'+REPO+'/git/ref/heads/main','--jq','.object.sha'])==commit
    notes=Path(info['combined']).parent/'github_release_notes.txt';notes.write_text('''可继续游玩的 v0.7 移植原型，附匹配工程与试玩 ROM 合集，也提供单独下载。

战斗菜单支持逐级 B 返回并保留选择，取消不耗资源；复用背景和局部更新改善切换响应。地图/人物保留原尺寸，头像保留独立 RGB555 颜色。游戏与音乐欣赏均使用简化音色。

实际源码 ZIP 已新解压重建并与试玩 ROM 逐字节核对。验证范围及哈希见包内记录；完整自然通关、全部结局、实机尚未验收。
''')
    if not info.get('draft_created'):
        run(['gh','release','create','v0.7','--repo',REPO,'--target',commit,'--draft','--title','v0.7 均衡画质可玩原型 · 工程与试玩','--notes-file',str(notes)])
        info['draft_created']=True;write(PUBLIC,info)
    for asset in info['assets']:run(['gh','release','upload','v0.7',asset,'--repo',REPO,'--clobber'])
    downloads=Path(tempfile.mkdtemp(prefix='ruina-release-download-',dir='/tmp'));run(['gh','release','download','v0.7','--repo',REPO,'--dir',str(downloads)])
    downloaded=[]
    for asset in info['assets']:
        source=Path(asset);copy=downloads/source.name;assert sha(source)==sha(copy);downloaded.append({'name':source.name,'sha256':sha(copy),'bytes':copy.stat().st_size})
    run(['gh','release','edit','v0.7','--repo',REPO,'--draft=false']);release=json.loads(run(['gh','release','view','v0.7','--repo',REPO,'--json','url,isDraft,tagName,assets']));assert not release['isDraft']and release['tagName']=='v0.7'
    destinations=[]
    for parent in(ROOT/'交付',Path('/mnt/c/Users/APP/Downloads')):
        parent.mkdir(exist_ok=True);target=parent/Path(info['combined']).name
        assert not target.exists()or sha(target)==info['combined_sha256'],('Will not overwrite different bundle',target)
        if not target.exists():shutil.copy2(info['combined'],target)
        assert sha(target)==info['combined_sha256'];destinations.append(str(target))
    info['local_combined_destinations']=destinations
    info.update(status='published_remote_assets_hash_verified',commit=commit,release_url=release['url'],download_verified_assets=downloaded,verification_download=str(downloads),published_unix=time.time());write(PUBLIC,info);print(json.dumps(info,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('bundle','publish'));args=p.parse_args();globals()[args.action]()
