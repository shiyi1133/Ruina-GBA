"""Build the continuing playable balanced renderer from production sources.

Prototype source overrides were promoted into platform/gba and runtime/rm2k.
Controlled tests now link the exact same production objects.
"""
import hashlib,json,subprocess,sys
from project_env import ROOT

OVERRIDES={}

def main():
    subprocess.run([sys.executable,str(ROOT/'tools/build.py'),'--incremental'],cwd=ROOT,check=True)
    rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';elf=ROOT/'build/ruina_opening_dev.elf'
    receipt=json.loads((ROOT/'build/build_receipt.json').read_text());digest=hashlib.sha256(rom.read_bytes()).hexdigest();assert digest==receipt['sha256']
    report={'status':'compiled_not_tested','ROM':str(rom),'ELF':str(elf),'sha256':digest,'bytes':rom.stat().st_size,'scope':'continuing playable balanced renderer; production source integration','compiler_inputs_sha256':receipt['compiler_inputs_sha256']}
    out=ROOT/'evidence/balanced_optimization_20261023';out.mkdir(parents=True,exist_ok=True);(out/'candidate_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='compiler_inputs_sha256'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
