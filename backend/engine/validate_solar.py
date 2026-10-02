"""Compare observed vs estimated solar; mock output is never empirical validation."""
import argparse
from dataclasses import asdict
from datetime import date, timedelta
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from backend.weather.cli import demo_venues
from backend.weather.adapters import MockAsosAdapter
from .solar import estimate_solar
from .wbgt import estimate_series
import numpy as np
import pandas as pd
from pvlib.location import Location


def interval_estimates(venue, points, step_seconds=60):
    """Same existing attenuation model, integrated over [tm-1h, tm].

    Midpoint integration is for validation only. End-of-hour cloud/rain is held
    constant within the hour; it is not fabricated subhour weather.
    """
    if step_seconds <= 0 or 3600 % step_seconds:
        raise ValueError('Integration step must divide an hour')
    n = 3600 // step_seconds
    times = pd.DatetimeIndex([p.valid_time-timedelta(hours=1)+timedelta(seconds=(j+.5)*step_seconds)
                              for p in points for j in range(n)])
    loc = Location(venue.lat, venue.lon, tz='Asia/Seoul', altitude=0)
    pos = loc.get_solarposition(times)
    clear = loc.get_clearsky(times, model='ineichen', solar_position=pos)
    ghi = np.maximum(0, clear.ghi.to_numpy()).reshape(len(points), n)
    ghi[pos.apparent_zenith.to_numpy().reshape(len(points), n) >= 90] = 0
    clouds = {1:.25, 3:.7, 4:.95}
    factors = np.array([(1-.75*(p.cloud_fraction if p.cloud_fraction is not None else clouds.get(p.sky_code,.7))**3.4)
                        *(.5 if p.pty_code not in (0,None) or (p.rain_mm is not None and p.rain_mm > 0) else 1)
                        for p in points])
    return ghi.mean(axis=1)*factors


def compare_observed(venue, points, output):
    if any(p.is_mock for p in points):
        raise ValueError('Observed comparison must not contain mock data')
    paired = [p for p in points if p.solar_wm2 is not None]
    if not paired:
        raise ValueError('No observed solar values')
    estimated = interval_estimates(venue, paired)
    observed = np.array([p.solar_wm2 for p in paired])
    errors = estimated-observed
    result = {'label':'KMA ASOS Suwon 119 - OBSERVED hourly solar comparison',
        'is_mock':False, 'count':len(paired), 'missing_count':len(points)-len(paired),
        'total_count':len(points), 'mae_wm2':float(np.abs(errors).mean()), 'bias_wm2':float(errors.mean()),
        'rmse_wm2':float(np.sqrt((errors**2).mean())),
        'max_absolute_error_wm2':float(np.abs(errors).max()),
        'positive_observation_count':int(np.sum(observed>0)),
        'positive_observation_mae_wm2':float(np.abs(errors[observed>0]).mean()) if np.any(observed>0) else None,
        'interval':'preceding one hour ending at tm (KST)', 'observation_unit':'MJ/m2 -> hour-mean W/m2',
        'integration_step_seconds':60, 'cloud_missing_hours':sum(p.cloud_fraction is None for p in points),
        'venue_geometry':{'lat':venue.lat,'lon':venue.lon,'altitude_assumed_m':0},
        'original_sample_sha256':paired[0].provenance['original_sample_sha256'],
        'limitations':['Hourly cloud/rain held constant within the preceding hour',
                      'Existing virtual venue coordinates; station coordinates not inferred',
                      'Solar comparison only; field WBGT accuracy is not validated']}
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    x=[p.valid_time for p in points]
    by_time={p.valid_time:(o,e) for p,o,e in zip(paired,observed,estimated)}
    plotted_observed=[by_time.get(p.valid_time,(np.nan,np.nan))[0] for p in points]
    plotted_estimated=[by_time.get(p.valid_time,(np.nan,np.nan))[1] for p in points]
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    axes[0].plot(x,plotted_observed,label='Observed hour mean',alpha=.8,lw=.7)
    axes[0].plot(x,plotted_estimated,label='Estimated hour mean',alpha=.7,lw=.7)
    axes[0].set(xlabel='Date (KST)',ylabel='Solar (W/m2)',title=result['label']); axes[0].legend()
    axes[1].scatter(observed,estimated,s=7,alpha=.35)
    bound=max(observed.max(),estimated.max()); axes[1].plot([0,bound],[0,bound],'k--',label='1:1')
    axes[1].set(xlabel='Observed hour mean (W/m2)',ylabel='Estimated hour mean (W/m2)',
        title=f"MAE {result['mae_wm2']:.2f} | bias {result['bias_wm2']:+.2f} | n={len(paired)}, missing={result['missing_count']}")
    axes[1].legend(); fig.tight_layout(); fig.savefig(output/'solar-comparison.png',dpi=150); plt.close(fig)
    rows=[{'time':p.valid_time.isoformat(),'observed_wm2':float(o),'estimated_wm2':float(e),'error_wm2':float(e-o)}
          for p,o,e in zip(paired,observed,estimated)]
    (output/'solar-pairs.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (output/'solar-metrics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


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
    parser=argparse.ArgumentParser();parser.add_argument('--observed',action='store_true')
    args=parser.parse_args()
    if args.observed:
        from backend.weather.asos_samples import load_dataset
        data=load_dataset();venue=demo_venues()[0]
        points=[p for day in data.dates for p in data.fetch(venue,data.station_id,day)]
        print(json.dumps(compare_observed(venue,points,Path('docs/real-data/solar'))));return
    venue=demo_venues()[0]; points=MockAsosAdapter().fetch(venue,venue.asos_station_id,date(2026,8,1))
    output=Path('data/output/p2'); metrics=compare(venue,points,output)
    risks=[asdict(r) for v in demo_venues() for r in estimate_series(v,MockAsosAdapter().fetch(v,v.asos_station_id,date(2026,8,1)))]
    (output/'risks.json').write_text(json.dumps(risks,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'risk_count':len(risks),**metrics}))

if __name__ == '__main__': main()
