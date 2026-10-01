"""Compare observed vs estimated solar; mock output is never empirical validation."""
import argparse
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from backend.weather.cli import demo_venues
from backend.weather.adapters import MockAsosAdapter
from .solar import estimate_solar
from .wbgt import estimate_series


def compare(venue,points,output):
    paired = [(p,estimate_solar(venue,p)) for p in points if p.solar_wm2 is not None]
    if not paired:
        raise ValueError("No observed irradiance available")
    errors = [s.estimated_wm2-p.solar_wm2 for p,s in paired]
    mock = any(p.is_mock for p,s in paired)
    result = {"mae_wm2":sum(abs(e) for e in errors)/len(errors), "bias_wm2":sum(errors)/len(errors),
              "count":len(errors), "is_mock":mock,"label":"MOCK SYNTHETIC DEMO - NOT OBSERVATIONAL VALIDATION" if mock else "OBSERVED SOLAR COMPARISON"}
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(10,4))
    x=[p.valid_time.hour for p,s in paired]
    ax.plot(x,[p.solar_wm2 for p,s in paired],label="Synthetic mock" if mock else "Observed")
    ax.plot(x,[s.estimated_wm2 for p,s in paired],label="Estimate")
    ax.fill_between(x,[s.low_wm2 for p,s in paired],[s.high_wm2 for p,s in paired],alpha=.2,label="Estimated range")
    ax.set(xlabel="Hour (KST)",ylabel="Solar irradiance (W/m2)",title=result["label"])
    ax.legend(); fig.tight_layout(); fig.savefig(output/'solar-comparison.png',dpi=150); plt.close(fig)
    (output/'solar-metrics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def main():
    venue=demo_venues()[0]; points=MockAsosAdapter().fetch(venue,venue.asos_station_id,date(2026,8,1))
    output=Path('data/output/p2'); metrics=compare(venue,points,output)
    risks=[asdict(r) for v in demo_venues() for r in estimate_series(v,MockAsosAdapter().fetch(v,v.asos_station_id,date(2026,8,1)))]
    (output/'risks.json').write_text(json.dumps(risks,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'risk_count':len(risks),**metrics}))

if __name__ == '__main__': main()
