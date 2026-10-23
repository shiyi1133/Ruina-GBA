"""Private headless display for the unchanged supplied RPG Maker game.

Uses the official EasyRPG compatible interpreter as a reference, not as the GBA
runtime. Its results must not be represented as original RPG_RT.exe acceptance.
Input commands are genuine keyboard events on this process's private X display.
"""
import ctypes as C,ctypes.util,json,os,signal,subprocess,sys,time
from pathlib import Path
from PIL import ImageGrab
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/oracle'

def main():
 display=next(f':{n}'for n in range(93,104)if not Path(f'/tmp/.X11-unix/X{n}').exists())
 for p in ['saves','config']:(OUT/p).mkdir(exist_ok=True)
 log=open(OUT/'interactive.log','w');xlog=open(OUT/'xvfb.log','a')
 server=subprocess.Popen(['Xvfb',display,'-screen','0','640x480x24','-nolisten','tcp'],stdout=xlog,stderr=xlog);player=None;xd=None
 try:
  time.sleep(.5);env=os.environ.copy();env.update(DISPLAY=display,SDL_AUDIODRIVER='dummy',SDL_RENDER_DRIVER='software')
  args=[str(OUT/'linux/easyrpg-player'),'--project-path',str(OUT/'original_game'),'--save-path',str(OUT/'saves'),'--config-path',str(OUT/'config'),'--new-game','--no-audio','--window','--no-vsync','--no-pause-focus-lost','--seed','12345','--encoding','936','--font1','/mnt/c/Windows/Fonts/simsun.ttc','--font2','/mnt/c/Windows/Fonts/simsun.ttc','--record-input',str(OUT/'reference_input.log'),'--no-log-color']
  player=subprocess.Popen(args,env=env,stdout=log,stderr=log)
  x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
  x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
  x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong
  x.XStringToKeysym.argtypes=[C.c_char_p];x.XStringToKeysym.restype=C.c_ulong
  x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_ubyte
  x.XFlush.argtypes=[C.c_void_p];x.XCloseDisplay.argtypes=[C.c_void_p]
  x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
  x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
  x.XFree.argtypes=[C.c_void_p];xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
  xd=x.XOpenDisplay(display.encode());assert xd
  time.sleep(2)
  parent=C.c_ulong();root=C.c_ulong();children=C.POINTER(C.c_ulong)();n=C.c_uint()
  x.XQueryTree(xd,x.XDefaultRootWindow(xd),C.byref(root),C.byref(parent),C.byref(children),C.byref(n))
  if n.value:x.XSetInputFocus(xd,children[0],2,0)
  if children:x.XFree(children)
  x.XFlush(xd);print('READY',display,flush=True)
  for line in sys.stdin:
   cmd=json.loads(line)
   if cmd.get('quit'):break
   if 'key'in cmd:
    code=x.XKeysymToKeycode(xd,x.XStringToKeysym(cmd['key'].encode()));assert code
    xt.XTestFakeKeyEvent(xd,code,1,0);x.XFlush(xd);time.sleep(cmd.get('hold',.08));xt.XTestFakeKeyEvent(xd,code,0,0);x.XFlush(xd)
   if 'wait'in cmd:time.sleep(cmd['wait'])
   if 'shot'in cmd:ImageGrab.grab(xdisplay=display).save(ROOT/'evidence'/cmd['shot'])
   print(json.dumps({'ok':True,'command':cmd,'reference_process_exit':player.poll()},ensure_ascii=False),flush=True)
 finally:
  if xd:x.XCloseDisplay(xd)
  if player and player.poll()is None:player.terminate();player.wait(timeout=5)
  server.terminate();server.wait(timeout=5);log.close();xlog.close()
if __name__=='__main__':main()
