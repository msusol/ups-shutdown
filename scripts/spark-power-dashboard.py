#!/usr/bin/env python3
"""Build a self-contained HTML page from the spark-power CSVs (see docs/process/spark-power-sampler.md).

Charts GPU watts, CPU busy % and UPS charge %, with a red band wherever the UPS was not online (ups_status != OL), plus a list of
on-battery / back-on-mains events from the NUT journal (those reach back further than the CSVs). No network and no libraries: the
page draws with a <canvas>, so it opens straight from disk.

    python3 scripts/spark-power-dashboard.py            # writes ~/.local/state/spark-power/dashboard.html
    python3 scripts/spark-power-dashboard.py --days 3 --open
"""
import argparse
import csv
import json
import re
import subprocess
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DIR = Path.home() / ".local/state/spark-power"
BUCKET_S = 60          # one point per minute keeps a week of 10-second rows to ~10k points


def load(directory: Path, days: int):
    cutoff = datetime.now() - timedelta(days=days)
    buckets: dict[int, list] = {}
    for f in sorted(directory.glob("spark-power-*.csv")):
        with f.open(newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    ts = datetime.fromisoformat(r["timestamp"])
                    if ts < cutoff:
                        continue
                    row = (float(r["gpu_watts"]), float(r["cpu_busy_pct"]), float(r["ups_charge"]), r["ups_status"])
                except (KeyError, ValueError):
                    continue                                   # a torn or blank row never stops the page
                buckets.setdefault(int(ts.timestamp()) // BUCKET_S * BUCKET_S, []).append(row)
    points = []
    for t in sorted(buckets):
        rows = buckets[t]
        n = len(rows)
        off = any(s != "OL" for *_, s in rows)
        points.append([t, round(sum(r[0] for r in rows) / n, 2), round(max(r[0] for r in rows), 2),
                       round(sum(r[1] for r in rows) / n, 1), round(min(r[2] for r in rows), 1), int(off)])
    return points


def journal_events(days: int):
    """UPS power events from NUT's journal as (iso time, text). Empty if the journal is unreadable."""
    try:
        out = subprocess.run(["journalctl", "-u", "nut-monitor", "--since", f"{days + 30} days ago", "-o", "short-iso", "--no-pager"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    ev = []
    for line in out.splitlines():
        m = re.match(r"(\S+)\s+\S+\s+\S+: (UPS \S+ (?:on battery|on line power|battery is low).*)", line)
        if m:
            ev.append((m.group(1)[:19], m.group(2)))
    return ev


PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Spark power</title>
<style>
:root{--bg:#fff;--fg:#1c1c1c;--mut:#666;--grid:#ddd;--gpu:#2a6fdb;--peak:#9db9ea;--cpu:#e08a1e;--chg:#1f9d55;--bad:rgba(220,40,40,.28)}
@media(prefers-color-scheme:dark){:root{--bg:#161616;--fg:#e8e8e8;--mut:#999;--grid:#333;--gpu:#6aa3ff;--peak:#3d5a8c;--cpu:#f0a13c;--chg:#4cc77f;--bad:rgba(255,80,80,.35)}}
body{margin:0 auto;max-width:1100px;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:22px 0 4px}.mut{color:var(--mut)}
canvas{width:100%;height:190px;display:block}.stats{display:flex;flex-wrap:wrap;gap:8px 24px;margin:10px 0}
.stats b{font-size:18px;display:block}li{margin:2px 0}.bad{color:#d33}
</style>
<h1>Spark power</h1>
<div class=mut id=range></div>
<div class=stats id=stats></div>
<h2>UPS events <span class=mut>(from the NUT journal)</span></h2><ul id=events></ul>
<h2>GPU watts <span class=mut>(line = minute average, pale = minute peak)</span></h2><canvas id=c1></canvas>
<h2>CPU busy %</h2><canvas id=c2></canvas>
<h2>UPS charge % <span class=mut>(lowest in each minute)</span></h2><canvas id=c3></canvas>
<p class=mut>Red bands: the UPS was not on mains. The GPU number is only the GPU, not the whole machine.</p>
<script>
const D=__DATA__, EV=__EVENTS__, GENERATED="__NOW__";
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n);
const fmt=t=>new Date(t*1000).toLocaleString([],{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
function draw(id,cols,ymax){
  const c=document.getElementById(id),dpr=devicePixelRatio||1,W=c.clientWidth,H=c.clientHeight;c.width=W*dpr;c.height=H*dpr;
  const g=c.getContext("2d");g.scale(dpr,dpr);g.font="11px system-ui";
  const L=40,R=6,T=6,B=18,t0=D[0][0],t1=D[D.length-1][0]||t0+1,x=t=>L+(t-t0)/(t1-t0||1)*(W-L-R),y=v=>T+(1-v/ymax)*(H-T-B);
  g.fillStyle=css("--bad");let s=null;
  D.forEach((p,i)=>{if(p[5]&&s===null)s=p[0];if((!p[5]||i==D.length-1)&&s!==null){g.fillRect(x(s)-1,T,Math.max(3,x(p[0])-x(s)+2),H-T-B);s=null}});
  g.strokeStyle=css("--grid");g.fillStyle=css("--mut");
  for(let i=0;i<=4;i++){const v=ymax*i/4;g.beginPath();g.moveTo(L,y(v));g.lineTo(W-R,y(v));g.stroke();g.fillText(Math.round(v),4,y(v)+4)}
  for(let i=0;i<=6;i++){const t=t0+(t1-t0)*i/6;g.fillText(fmt(t),Math.min(x(t),W-90),H-4)}
  cols.forEach(([k,col,w])=>{g.strokeStyle=css(col);g.lineWidth=w;g.beginPath();D.forEach((p,i)=>i?g.lineTo(x(p[0]),y(p[k])):g.moveTo(x(p[0]),y(p[k])));g.stroke()});
}
function render(){
  if(!D.length){document.getElementById("range").textContent="No data found.";return}
  document.getElementById("range").textContent=fmt(D[0][0])+" to "+fmt(D[D.length-1][0])+" - built "+GENERATED;
  const avg=D.reduce((a,p)=>a+p[1],0)/D.length,pk=Math.max(...D.map(p=>p[2])),minc=Math.min(...D.map(p=>p[4])),off=D.filter(p=>p[5]).length;
  document.getElementById("stats").innerHTML=[["Average GPU watts",avg.toFixed(1)],["Peak GPU watts",pk.toFixed(0)],["Lowest UPS charge",minc+"%"],["Minutes off mains (in these files)",off]]
    .map(([a,b])=>"<div><b>"+b+"</b><span class=mut>"+a+"</span></div>").join("");
  document.getElementById("events").innerHTML=EV.length?EV.map(e=>"<li>"+e[0].replace("T"," ")+" - "+e[1]+"</li>").join(""):"<li class=mut>None found.</li>";
  draw("c1",[[2,"--peak",1],[1,"--gpu",1.5]],Math.ceil(pk/20)*20||20);draw("c2",[[3,"--cpu",1.5]],100);draw("c3",[[4,"--chg",1.5]],100);
}
render();addEventListener("resize",render);
</script>
"""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--out", type=Path)
    p.add_argument("--open", action="store_true", help="open the page in a browser when done")
    a = p.parse_args()
    points = load(a.dir, a.days)
    out = a.out or a.dir / "dashboard.html"
    out.write_text(PAGE.replace("__DATA__", json.dumps(points)).replace("__EVENTS__", json.dumps(journal_events(a.days)))
                   .replace("__NOW__", datetime.now().strftime("%Y-%m-%d %H:%M")))
    print(f"{out}  ({len(points)} points, {a.days} days)")
    if a.open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
