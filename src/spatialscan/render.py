import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
def render_plan(result,path):
    fig,ax=plt.subplots(figsize=(8,6))
    for room in result["rooms"]:
        p=room.get("polygon_xy_m") or []
        if len(p)<3:
            ax.text(.02,.98,f"{room.get('name',room.get('id','room'))}: metric footprint unavailable",
                    transform=ax.transAxes,va="top")
            continue
        x=[a[0] for a in p]+[p[0][0]]; y=[a[1] for a in p]+[p[0][1]]
        ax.plot(x,y)
        ax.text(sum(x[:-1])/len(p),sum(y[:-1])/len(p),room["name"])
    ax.set_aspect("equal"); ax.set_xlabel("m"); ax.set_ylabel("m"); ax.grid(True,alpha=.25)
    fig.tight_layout(); fig.savefig(path,dpi=180); plt.close(fig)
