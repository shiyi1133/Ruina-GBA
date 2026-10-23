"""Measure real input-to-LCD responses without writing emulated state."""
import struct,time

class ResponseMeter:
    def __init__(self,emulator):self.e=emulator;self.samples=[]
    def u32(self,name,offset=0):return struct.unpack('<I',self.e.memory(self.e.symbols[name]+offset,4))[0]
    def timing(self):return tuple(map(int,self.e.command('timing').split()[1:]))
    def lcd(self):
        _,h,b=self.e.command('lcdhash').split();return h,int(b)
    def presents(self):return self.u32('video_metrics',16)+self.u32('map_video_metrics',8)
    def action(self,label,key,strict_pixels=True):
        e=self.e;e.key(0);before=self.lcd();clock=self.timing();start=self.presents();trace=[];first=None;host=time.monotonic();stable=0
        for frame in range(1800):
            e.frames(1,key if frame<2 else 0);h,black=self.lcd();count=self.presents();ready=self.u32('ui_ready');pending=self.u32('input_latched')|self.u32('input_triggered')
            trace.append({'frame':frame+1,'LCD_hash':h,'black_pixels':black,'presentations':count-start,'ready':ready,'pending':pending})
            if first is None and count!=start and h!=before[0]:first=frame+1
            stable=stable+1 if ready and not pending else 0
            if first is not None and stable>=6 and frame>=13:break
        else:raise AssertionError(('response timeout',label,e.debug()))
        end=self.timing();assert end[2]-clock[2]==len(trace),(clock,end,len(trace));final=self.lcd()[0]
        unexpected=[t for t in trace if t['LCD_hash']not in(before[0],final)]
        if strict_pixels:assert not unexpected,(label,'incomplete/intermediate LCD output',unexpected)
        row={'action':label,'key':key,'press_to_complete_new_LCD_frames':first,'press_to_complete_new_LCD_ms':first*clock[1]*1000/clock[0],'black_LCD_frames':sum(t['black_pixels']==38400 for t in trace),'intermediate_LCD_frames':len(unexpected),'observer_frames':len(trace),'GBA_timing_before':clock,'GBA_timing_after':end,'host_seconds_with_IPC':time.monotonic()-host,'trace':trace}
        self.samples.append(row);print(label,first,round(row['press_to_complete_new_LCD_ms'],2),'ms; black',row['black_LCD_frames'],flush=True);return row
    def summary(self):
        rows=[]
        for label in dict.fromkeys(r['action']for r in self.samples):
            samples=[r for r in self.samples if r['action']==label];ms=[r['press_to_complete_new_LCD_ms']for r in samples]
            rows.append({'action':label,'samples':len(samples),'response_ms_min':min(ms),'response_ms_max':max(ms),'response_ms_mean':sum(ms)/len(ms),'black_frames':sum(r['black_LCD_frames']for r in samples),'intermediate_LCD_frames':sum(r['intermediate_LCD_frames']for r in samples)})
        return rows
