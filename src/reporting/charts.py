"""Charts use the same adjusted series as the analysis."""
from pathlib import Path

def market_chart(result, folder: Path):
    if not result.get("market"):return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    frame=pd.DataFrame(result["price_rows"]);dates=pd.to_datetime(frame["date"])
    values=pd.Series(result["market"]["chart_prices"])
    fig,axes=plt.subplots(2,1,figsize=(9,4.5),sharex=True,gridspec_kw={"height_ratios":[3,1]})
    axes[0].plot(dates,values,color="#14566e",label="Adjusted series normalized to last close")
    for days,color in [(20,"#d99d32"),(50,"#5a927b")]:
        axes[0].plot(dates,values.rolling(days).mean(),color=color,label=f"MA{days}",linewidth=1)
    axes[0].set_ylabel("VND / share");axes[0].legend(fontsize=7,loc="upper left")
    axes[1].bar(dates,frame["volume"]/1e6,color="#94b2bc",width=1.8);axes[1].set_ylabel("Million shares")
    for ax in axes:ax.grid(alpha=.18);ax.spines[["top","right"]].set_visible(False)
    fig.autofmt_xdate();fig.tight_layout();folder.mkdir(parents=True,exist_ok=True)
    path=folder/"market.png";fig.savefig(path,dpi=160);plt.close(fig)
    return path
