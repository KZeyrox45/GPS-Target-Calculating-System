/**
 * BENCHMARK MODULE
 * Run RMSE/MaxErr comparison between algorithms over a standard grid of cases.
 * Usage in console:
 *   Benchmark.run();
 *   Benchmark.renderTable(); // optional renders into a floating div
 */
(function(){
  'use strict';

  function deg(v){ return v * (Math.PI/180); }

  function standardSuite(){
    // Latitudes, azimuths, distances (km)
    const lats = [-60, -30, 0, 30, 60];
    const lons = [0];
    const azis = [0,45,90,135,180,225,270,315];
    const ds   = [0.1,1,2.5,5,10,50];
    const cases = [];
    for (const lat of lats) for (const lon of lons)
      for (const az of azis) for (const d of ds)
        cases.push({lat, lon, azimuth: az, distance: d});
    return cases;
  }

  function distanceMeters(a, b){
    const km = window.CoordinateCalculator.calculateDistance(a.lat, a.lon, b.lat, b.lon);
    return km * 1000.0;
  }

  function run(opts={}){
    const algorithms = opts.algorithms || window.CoordinateCalculator.listAlgorithms();
    const reference = opts.reference || 'vincenty';
    const cases = opts.cases || standardSuite();
    const results = {};
    algorithms.forEach(algo=>{
      results[algo] = { sqerr:0, maxErr:0, count:0 };
    });

    for (const tc of cases){
      // reference output
      const ref = window.CoordinateCalculator.calculateTargetCoordinate(
        tc.lat, tc.lon, tc.azimuth, tc.distance, reference
      );
      for (const algo of algorithms){
        const out = window.CoordinateCalculator.calculateTargetCoordinate(
          tc.lat, tc.lon, tc.azimuth, tc.distance, algo
        );
        const err = distanceMeters(ref, out);
        const r = results[algo];
        r.sqerr += err*err;
        r.maxErr = Math.max(r.maxErr, err);
        r.count += 1;
      }
    }

    // finalize
    const summary = algorithms.map(algo=>{
      const r = results[algo];
      const rmse = Math.sqrt(r.sqerr / Math.max(1, r.count));
      return { algorithm: algo, rmseMeters: rmse, maxErrMeters: r.maxErr, cases: r.count };
    }).sort((a,b)=> (a.algorithm===reference)-(b.algorithm===reference));

    console.table(summary.map(s=>({
      Algorithm: s.algorithm + (s.algorithm===reference?' (ref)':''),
      RMSE_m: s.rmseMeters.toFixed(3),
      Max_m: s.maxErrMeters.toFixed(3),
      N: s.cases
    })));

    return { reference, cases: cases.length, summary };
  }

  function renderTable(containerId){
    const { summary, reference } = run();
    let container = document.getElementById(containerId||'benchmarkResult');
    if (!container){
      container = document.createElement('div');
      container.id = 'benchmarkResult';
      container.style.position = 'absolute';
      container.style.left = '1rem';
      container.style.bottom = '1rem';
      container.style.zIndex = '1000';
      container.style.background = 'rgba(255,255,255,0.95)';
      container.style.padding = '12px';
      container.style.border = '1px solid #e5e7eb';
      container.style.borderRadius = '8px';
      document.body.appendChild(container);
    }
    const html = [`<div style="font-weight:700;margin-bottom:6px">Benchmark (ref=${reference})</div>`,
      '<table style="font-size:12px;border-collapse:collapse">',
      '<tr><th style="border:1px solid #ddd;padding:4px">Algorithm</th><th style="border:1px solid #ddd;padding:4px">RMSE (m)</th><th style="border:1px solid #ddd;padding:4px">Max (m)</th></tr>'
    ];
    summary.forEach(s=>{
      html.push(`<tr><td style="border:1px solid #ddd;padding:4px">${s.algorithm}${s.algorithm===reference?' (ref)':''}</td>`+
                `<td style="border:1px solid #ddd;padding:4px">${s.rmseMeters.toFixed(3)}</td>`+
                `<td style="border:1px solid #ddd;padding:4px">${s.maxErrMeters.toFixed(3)}</td></tr>`);
    });
    html.push('</table>');
    container.innerHTML = html.join('');
  }

  if (typeof window !== 'undefined'){
    window.Benchmark = { run, renderTable, standardSuite };
    console.log('✅ Benchmark module loaded. Use Benchmark.run() or Benchmark.renderTable()');
  }
})();
