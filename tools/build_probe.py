"""Build the optional mGBA 0.11 read-only acceptance harness."""
import os,subprocess
from pathlib import Path
from project_env import ROOT
base=Path(os.environ.get('MGBA_PREFIX','/home/app/gba-runtime/tooling/build/mgba-idle-stage/home/app/projects/GBA_HACK/GBA_HACK_ENV/tools/mgba-dist'))
subprocess.run(['cc','-O2','-g','-DENABLE_DIRECTORIES',str(ROOT/'tools/gba_acceptance_probe.c'),'-I'+str(base/'include'),'-L'+str(base/'lib'),'-Wl,-rpath,'+str(base/'lib'),'-lmgba','-o',str(ROOT/'build/gba_acceptance_probe.new')],check=True)

os.replace(ROOT/'build/gba_acceptance_probe.new',ROOT/'build/gba_acceptance_probe')
