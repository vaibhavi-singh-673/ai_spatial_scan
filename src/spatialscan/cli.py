import argparse,json
from pathlib import Path
from .tiers.lidar import run as lidar_run
from .tiers.visual import collect_images,collect_video_frames,estimate_visual_capture
from .evaluate import evaluate
from .quality import assess_capture
from .benchmark import run_benchmark
from .audit import audit_submission
from .fixloop import run_fix_loop
from .report import write_html_report
from .render import render_plan

def main():
    ap=argparse.ArgumentParser(prog="spatialscan")
    sub=ap.add_subparsers(dest="cmd",required=True)
    r=sub.add_parser("run")
    r.add_argument("--tier",choices=["lidar","photos","video"],required=True)
    r.add_argument("--input",required=True)
    r.add_argument("--output",required=True)
    r.add_argument("--render")
    r.add_argument("--scale-m-per-pixel",type=float)
    e=sub.add_parser("evaluate")
    e.add_argument("--prediction",required=True); e.add_argument("--ground-truth",required=True); e.add_argument("--output",required=True)
    q=sub.add_parser("quality", help="Assess capture readiness before reconstruction")
    q.add_argument("--tier",choices=["lidar","photos","video"],required=True)
    q.add_argument("--input",required=True)
    q.add_argument("--output",required=True)
    q.add_argument("--scale-m-per-pixel",type=float)
    h=sub.add_parser("report", help="Render a JSON result or quality report as HTML")
    h.add_argument("--input",required=True)
    h.add_argument("--output",required=True)
    b=sub.add_parser("benchmark", help="Run registered captures without fabricating missing evidence")
    b.add_argument("--manifest",required=True)
    b.add_argument("--output",default="benchmarks/results/benchmark.json")
    a=sub.add_parser("audit", help="Audit submission evidence against the scoring rubric")
    a.add_argument("--root",default=".")
    a.add_argument("--output",default="benchmarks/results/submission_audit.json")
    f=sub.add_parser("fixloop", help="Run before/after LiDAR fix-loop ablation")
    f.add_argument("--input",required=True)
    f.add_argument("--output",required=True)
    args=ap.parse_args()
    if args.cmd=="run":
        if args.tier=="lidar": result=lidar_run(args.input,Path(args.output).stem)
        elif args.tier=="video": result=estimate_visual_capture(collect_video_frames(args.input),args.tier,args.scale_m_per_pixel)
        else: result=estimate_visual_capture(collect_images(args.input),args.tier,args.scale_m_per_pixel)
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(json.dumps(result,indent=2))
        if args.render: render_plan(result,args.render)
        print(f"Wrote {args.output}")
    elif args.cmd=="evaluate":
        out=evaluate(args.prediction,args.ground_truth)
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(json.dumps(out,indent=2))
        print(json.dumps(out,indent=2))
    elif args.cmd=="quality":
        out=assess_capture(args.input,args.tier,args.scale_m_per_pixel)
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(json.dumps(out,indent=2))
        print(json.dumps(out,indent=2))
    elif args.cmd=="report":
        write_html_report(args.input,args.output)
        print(f"Wrote {args.output}")
    elif args.cmd=="audit":
        out=audit_submission(args.root)
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        Path(args.output).write_text(json.dumps(out,indent=2))
        print(json.dumps(out,indent=2))
    elif args.cmd=="fixloop":
        out=run_fix_loop(args.input,args.output)
        print(json.dumps(out,indent=2))
    else:
        out=run_benchmark(args.manifest,args.output)
        print(json.dumps(out,indent=2))
