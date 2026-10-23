"""Compare bitmap membership order to the original ascending-ID vector."""
import argparse,hashlib,json,subprocess
from project_env import ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('--shop',default='runtime/rm2k/shop.c');args=p.parse_args();source=ROOT/args.shop;target=ROOT/'build/shop_item_order_host'
    subprocess.run(['cc','-std=c99','-O2','-ffreestanding','-fdata-sections','-ffunction-sections','-Wl,--gc-sections','-Isource','-Iruntime/rm2k','-Iplatform/gba','-Ibuild','-DSHOP_SOURCE="'+str(source)+'"','tests/shop_item_order_host.c','-o',str(target)],cwd=ROOT,check=True)
    result=json.loads(subprocess.check_output([str(target)],text=True));assert result['status']=='pass';result.update(source=args.shop,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Original ascending-ID array used as independent expected order across 1024 random densities, including empty/full and word boundaries. Buying keeps caller order and duplicate IDs. No prices or transactions changed by the index representation.')
    helper=source.parent/'item_mask.h';result['item_mask_header_sha256']=hashlib.sha256(helper.read_bytes()).hexdigest()if helper.exists()else None
    out=ROOT/'evidence/balanced_optimization_20261023/shop_order';out.mkdir(parents=True,exist_ok=True);(out/(result['source_sha256'][:12]+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
