// src/services/api.js
// Centralized API service for all backend calls

const BASE = {
  gc: '/api/gc',   // grid-controller  :5001
  tr: '/api/tr',   // transformer       :5002
  zn: '/api/zn',   // zone-north        :5003
  zs: '/api/zs',   // zone-south        :5004
  ze: '/api/ze',   // zone-east         :5005
  zw: '/api/zw',   // zone-west         :5006
  zc: '/api/zc',   // zone-central      :5007
  lb: '/api/lb',   // load-balancer     :5008
  vr: '/api/vr',   // voltage-regulator :5009
  fd: '/api/fd',   // fault-detection   :5010
};

async function get(base, path) {
  try {
    const r = await fetch(`${base}${path}`, { signal: AbortSignal.timeout(3000) });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export const api = {
  gridSummary:     () => get(BASE.gc, '/metrics/summary'),
  alerts:          (n=50, includeResolved=true) => get(BASE.gc, `/alerts?limit=${n}&include_resolved=${includeResolved}`),
  remediationLog:  (n=20) => get(BASE.gc, `/remediation-log?limit=${n}`),
  transformers:    () => get(BASE.tr, '/status'),
  zoneNorth:       () => get(BASE.zn, '/status'),
  zoneSouth:       () => get(BASE.zs, '/status'),
  zoneEast:        () => get(BASE.ze, '/status'),
  zoneWest:        () => get(BASE.zw, '/status'),
  zoneCentral:     () => get(BASE.zc, '/status'),
  loadBalancer:    () => get(BASE.lb, '/status'),
  voltageRegulator:() => get(BASE.vr, '/status'),
  faultDetection:  () => get(BASE.fd, '/status'),

  allZones: async () => {
    const [n, s, e, w, c] = await Promise.all([
      get(BASE.zn, '/status'),
      get(BASE.zs, '/status'),
      get(BASE.ze, '/status'),
      get(BASE.zw, '/status'),
      get(BASE.zc, '/status'),
    ]);
    return { north: n, south: s, east: e, west: w, central: c };
  },

  injectFault: async (service, payload) => {
    const bases = { transformer: BASE.tr, 'fault-detection': BASE.fd,
                    'voltage-regulator': BASE.vr, 'load-balancer': BASE.lb };
    const b = bases[service] || BASE.gc;
    try {
      const r = await fetch(`${b}/demo/inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return r.json();
    } catch { return null; }
  },

  startSimulation: () => fetch(`${BASE.gc}/simulation/start`, { method: 'POST' }).then(r => r.json()).catch(() => null),
  stopSimulation:  () => fetch(`${BASE.gc}/simulation/stop`,  { method: 'POST' }).then(r => r.json()).catch(() => null),
};
