"""
audit_and_generate.py
=====================
1. Verifies all numbers cited in week-1..6 reports against code.
2. Computes actual simulation data for histograms.
3. Generates / re-generates all PNG figures:
   - report-weekly/figures/*.png  (benchmark figures)
   - report-weekly/Images/coord-flow.png
   - report-weekly/Images/real-time-data-pipeline.png
Run from  backend/  directory:
    uv run python scripts/audit_and_generate.py
"""

import sys
import math
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# --- Paths --------------------------------------------------------------------
BACKEND = pathlib.Path(__file__).parent.parent
FIGURES = BACKEND.parent / "report-weekly" / "figures"
IMAGES  = BACKEND.parent / "report-weekly" / "Images"
FIGURES.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BACKEND))

from app.algorithms.alpha_beta_filter import AlphaBetaFilter
from app.algorithms.kalman_filter import KalmanFilter, KalmanFilter3D

# --- Sensor noise params (must match schemas / sensor_fusion.py) --------------
_SIG_GPS_LAT  = 5.0   # m
_SIG_GPS_LON  = 5.0   # m
_SIG_AZ_DEG   = 0.3   # degrees
_SIG_EL_DEG   = 0.2   # degrees
_SIG_RANGE    = 0.5   # m

# GPS horizontal sigma (same as sensor_fusion.py line 117)
_SIGMA_GPS = math.sqrt(_SIG_GPS_LAT**2 + _SIG_GPS_LON**2) / math.sqrt(2)  # = 5.0 m
_SIG_AZ_R  = math.radians(_SIG_AZ_DEG)   # 0.005236 rad
_SIG_EL_R  = math.radians(_SIG_EL_DEG)   # 0.003491 rad


def compute_sigma_pos(range_m: float) -> float:
    """RSS uncertainty model from sensor_fusion.py."""
    sigma_lateral   = range_m * math.sin(_SIG_AZ_R)
    sigma_elevation = range_m * math.sin(_SIG_EL_R)
    return math.sqrt(_SIGMA_GPS**2 + sigma_lateral**2 + _SIG_RANGE**2 + sigma_elevation**2)

DT       = 0.1    # 10 Hz
DURATION = 120.0  # seconds
N_STEPS  = int(DURATION / DT)   # 1200
SEED     = 42


# --- Small trajectory generators (sync, no asyncio) --------------------------

def gen_pedestrian(rng, n_steps, dt=DT):
    """Linear walk ~1.2 m/s, narrow corridor."""
    vel = np.array([1.0, 0.2])
    pos = np.array([-90.0, 40.0])
    traj = []
    for _ in range(n_steps):
        traj.append(pos.copy())
        pos = pos + vel * dt + rng.normal(0, 0.02, 2)
    return np.array(traj)


def gen_motorcycle(rng, n_steps, dt=DT):
    """Figure-8 at ~8 m/s."""
    traj, t = [], 0.0
    r1, r2 = 160.0, 120.0
    omega = 2 * math.pi / 60
    for _ in range(n_steps):
        E = r1 * math.sin(omega * t)
        N = r2 * math.sin(2 * omega * t) / 2 + 40
        traj.append([E, N])
        t += dt
    return np.array(traj)


def gen_drone(rng, n_steps, dt=DT):
    """Expanding spiral."""
    traj, t = [], 0.0
    for _ in range(n_steps):
        r = 80 + t * 0.8
        E = r * math.cos(0.12 * t - math.pi / 2)
        N = r * math.sin(0.12 * t - math.pi / 2)
        traj.append([E, N])
        t += dt
    return np.array(traj)


def add_noise(gt, rng):
    """Add simulated sensor noise to ground-truth ENU trajectory."""
    n = len(gt)
    az_noise  = rng.normal(0, math.radians(0.3), n)
    el_noise  = rng.normal(0, math.radians(0.2), n)
    gps_noise = rng.normal(0, 5.0, (n, 2))
    r_noise   = rng.normal(0, 0.5, n)

    noisy = np.zeros((n, 2))
    for i in range(n):
        E, N = gt[i]
        true_range = math.sqrt(E**2 + N**2) + 1e-3
        dE = true_range * math.sin(az_noise[i]) + r_noise[i] * E / true_range
        dN = true_range * math.sin(el_noise[i]) + r_noise[i] * N / true_range
        noisy[i, 0] = E + gps_noise[i, 0] + dE
        noisy[i, 1] = N + gps_noise[i, 1] + dN
    return noisy


def run_filters(gt, noisy, scenario="pedestrian"):
    """Return arrays (raw_err, ab_err, kf_err) of 2D position errors (m)."""
    n = len(gt)
    sigma_a = 0.5 if scenario == "pedestrian" else 5.0
    is_3d   = (scenario == "drone")

    ab = AlphaBetaFilter(alpha=0.4, dt=DT)
    kf = KalmanFilter3D(dt=DT, sigma_a=sigma_a) if is_3d else KalmanFilter(dt=DT, sigma_a=sigma_a)

    raw_err = np.zeros(n)
    ab_err = np.zeros(n)
    kf_err = np.zeros(n)

    for i in range(n):
        meas_E, meas_N = noisy[i]
        gt_E, gt_N = gt[i]

        raw_err[i] = math.sqrt((meas_E - gt_E)**2 + (meas_N - gt_N)**2)

        ab_state = ab.step(meas_E, meas_N)
        ab_err[i] = math.sqrt((ab_state[0] - gt_E)**2 + (ab_state[1] - gt_N)**2)

        sigma_pos = compute_sigma_pos(math.sqrt(meas_E**2 + meas_N**2))
        if is_3d:
            st = kf.step(meas_E, meas_N, 0.0, sigma_pos)
            kf_err[i] = math.sqrt((st[0] - gt_E)**2 + (st[1] - gt_N)**2)
        else:
            st = kf.step(meas_E, meas_N, sigma_pos)
            kf_err[i] = math.sqrt((st[0] - gt_E)**2 + (st[1] - gt_N)**2)

    return raw_err, ab_err, kf_err


def collect_axis_errors(gt, noisy, sigma_a=0.5):
    """Return per-axis signed errors for pedestrian scenario."""
    ab = AlphaBetaFilter(alpha=0.4, dt=DT)
    kf = KalmanFilter(dt=DT, sigma_a=sigma_a)
    ab_eE, ab_eN, kf_eE, kf_eN, raw_eE, raw_eN = [], [], [], [], [], []
    for i in range(len(gt)):
        mE, mN = noisy[i]
        gtE, gtN = gt[i]
        raw_eE.append(mE - gtE)
        raw_eN.append(mN - gtN)
        ab_st = ab.step(mE, mN)
        ab_eE.append(ab_st[0] - gtE)
        ab_eN.append(ab_st[1] - gtN)
        sigma_pos = compute_sigma_pos(math.sqrt(mE**2 + mN**2))
        st = kf.step(mE, mN, sigma_pos)
        kf_eE.append(st[0] - gtE)
        kf_eN.append(st[1] - gtN)
    return (np.array(raw_eE), np.array(raw_eN),
            np.array(ab_eE),  np.array(ab_eN),
            np.array(kf_eE),  np.array(kf_eN))


def collect_positions(gt, noisy, scenario="pedestrian"):
    n = len(gt)
    sigma_a = 0.5 if scenario == "pedestrian" else 5.0
    ab = AlphaBetaFilter(alpha=0.4, dt=DT)
    kf = KalmanFilter(dt=DT, sigma_a=sigma_a)
    ab_pos = np.zeros((n, 2))
    kf_pos = np.zeros((n, 2))
    for i in range(n):
        mE, mN = noisy[i]
        ab_st = ab.step(mE, mN)
        ab_pos[i] = ab_st[:2]
        sigma_pos = compute_sigma_pos(math.sqrt(mE**2 + mN**2))
        st = kf.step(mE, mN, sigma_pos)
        kf_pos[i] = st[:2]
    return ab_pos, kf_pos


def cumulative_rmse(err):
    return np.sqrt(np.cumsum(err**2) / np.arange(1, len(err)+1))


# --- Run simulations ----------------------------------------------------------
print("Running simulations (seed=42) ...")

noisy_ped   = add_noise(gen_pedestrian(np.random.default_rng(SEED), N_STEPS),
                         np.random.default_rng(SEED+1))
gt_ped      = gen_pedestrian(np.random.default_rng(SEED), N_STEPS)
raw_ped, ab_ped, kf_ped = run_filters(gt_ped, noisy_ped, "pedestrian")

gt_moto      = gen_motorcycle(np.random.default_rng(SEED), N_STEPS)
noisy_moto   = add_noise(gt_moto, np.random.default_rng(SEED+2))
raw_moto, ab_moto, kf_moto = run_filters(gt_moto, noisy_moto, "motorcycle")

gt_drone     = gen_drone(np.random.default_rng(SEED), N_STEPS)
noisy_drone  = add_noise(gt_drone, np.random.default_rng(SEED+3))
raw_drone, ab_drone, kf_drone = run_filters(gt_drone, noisy_drone, "drone")

# --- Verification printout ----------------------------------------------------
print("\n=== VERIFICATION: Final RMSE ===")
for label, raw_e, ab_e, kf_e in [
    ("Pedestrian", raw_ped, ab_ped, kf_ped),
    ("Motorcycle", raw_moto, ab_moto, kf_moto),
    ("Drone",      raw_drone, ab_drone, kf_drone),
]:
    print(f"  {label:12s}: raw={math.sqrt(np.mean(raw_e**2)):.3f}"
          f"  ab={math.sqrt(np.mean(ab_e**2)):.3f}"
          f"  kf={math.sqrt(np.mean(kf_e**2)):.3f}  m")

raw_eE, raw_eN, ab_eE, ab_eN, kf_eE, kf_eN = collect_axis_errors(gt_ped, noisy_ped)
print("\n=== VERIFICATION: sigma_E / sigma_N (pedestrian) ===")
print(f"  Raw:        sigE={np.std(raw_eE):.3f}  sigN={np.std(raw_eN):.3f}")
print(f"  Alpha-beta: sigE={np.std(ab_eE):.3f}  sigN={np.std(ab_eN):.3f}")
print(f"  Kalman:     sigE={np.std(kf_eE):.3f}  sigN={np.std(kf_eN):.3f}")

print("\n=== VERIFICATION: beta formula (alpha=0.4) ===")
alpha_val = 0.4
beta_code   = (2 - alpha_val) - 2 * math.sqrt(1 - alpha_val)
beta_simple = alpha_val**2 / (2 - alpha_val)
print(f"  Code  (2-a)-2*sqrt(1-a) = {beta_code:.5f}")
print(f"  Simplified a^2/(2-a)   = {beta_simple:.5f}")

print("\n=== VERIFICATION: sigma_pos at key ranges ===")
sg = 5.0
saz = math.radians(0.3)
sel = math.radians(0.2)
sl = 0.5
Rcross = sg / math.sqrt(math.sin(saz)**2 + math.sin(sel)**2)
for R in [50, 500, 1000]:
    sp = math.sqrt(sg**2 + (R*math.sin(saz))**2 + sl**2 + (R*math.sin(sel))**2)
    imu_frac = ((R*math.sin(saz))**2 + (R*math.sin(sel))**2) / sp**2
    print(f"  R={R:5d}m: sigma_pos={sp:.2f} m  IMU contrib={100*imu_frac:.0f}%")
print(f"  Cross-over range = {Rcross:.1f} m")

print("\n=== VERIFICATION: pipeline timing percentages ===")
times = [("LLA->ECEF", 2.1), ("ECEF->ENU", 3.8),
         ("SensorFusion", 1.2), ("Kalman", 48.5), ("ENU->LLA", 3.4)]
total_us = sum(t for _, t in times)
for name, t in times:
    print(f"  {name:20s}: {t:5.1f} us = {100*t/total_us:.1f}%")
print(f"  Total: {total_us:.1f} us")

print("\n=== HISTOGRAM DATA (pedestrian, n=1200) ===")
BIN_EDGES = np.arange(0, 4.1, 0.2)
BIN_CENTERS = (BIN_EDGES[:-1] + BIN_EDGES[1:]) / 2
ab_hist, _ = np.histogram(ab_ped, bins=BIN_EDGES)
kf_hist, _ = np.histogram(kf_ped, bins=BIN_EDGES)

print("  pgfplots coords for Alpha-beta:")
coords_ab = " ".join(f"({c:.1f},{h})" for c, h in zip(BIN_CENTERS, ab_hist) if h > 0)
print(f"    {coords_ab}")
print("  pgfplots coords for Kalman:")
coords_kf = " ".join(f"({c:.1f},{h})" for c, h in zip(BIN_CENTERS, kf_hist) if h > 0)
print(f"    {coords_kf}")
print(f"  Total ab={ab_hist.sum()}  kf={kf_hist.sum()}")

# --- FIGURES ------------------------------------------------------------------
print("\nGenerating PNG figures...")

ORANGE = '#E07B39'
BLUE = '#4A8FD4'
RED = '#C0392B'
GREEN = '#27ae60'
DARK   = '#2c3e50'
BG   = '#f9f9f9'

def style_ax(ax):
    ax.set_facecolor(BG)
    ax.grid(linestyle='--', alpha=0.45)


# --- Figure 1: RMSE Bar ---
raw_f = [math.sqrt(np.mean(e**2)) for e in [raw_ped, raw_moto, raw_drone]]
ab_f  = [math.sqrt(np.mean(e**2)) for e in [ab_ped,  ab_moto,  ab_drone]]
kf_f  = [math.sqrt(np.mean(e**2)) for e in [kf_ped,  kf_moto,  kf_drone]]

x = np.arange(3)
w = 0.26
fig, ax = plt.subplots(figsize=(10, 5.5))
fig.patch.set_facecolor(BG)
style_ax(ax)
b1 = ax.bar(x-w, raw_f, w, label='Do tho',     color=ORANGE, edgecolor='#B5612B')
b2 = ax.bar(x,   ab_f,  w, label='Alpha-beta', color=BLUE,   edgecolor='#2E6FA3')
b3 = ax.bar(x+w, kf_f,  w, label='Kalman',     color=RED,    edgecolor='#96281B')
ax.axhline(5.0, color='black', linestyle='dotted', linewidth=1.5, label='Yeu cau < 5 m')
ax.set_xticks(x)
ax.set_xticklabels(["Nguoi di bo", "Xe may", "Drone (3D)"], fontsize=12)
ax.set_ylabel('RMSE cuoi phien (m)', fontsize=11)
ax.set_title('So sanh RMSE cuoi phien - Seed 42, T = 120 s, R = 400 m', fontsize=12)
ax.legend(fontsize=10)
ax.set_ylim(0, 3.5)
for bar in [*b1, *b2, *b3]:
    h = bar.get_height()
    ax.text(bar.get_x()+bar.get_width()/2, h+0.04, f'{h:.2f}',
            ha='center', va='bottom', fontsize=9, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGURES/"rmse_bar_comparison.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved rmse_bar_comparison.png")

# --- Figure 2: RMSE Convergence ---
t_ax = np.arange(N_STEPS) * DT
datasets = [
    ("Nguoi di bo", raw_ped,   ab_ped,   kf_ped),
    ("Xe may",      raw_moto,  ab_moto,  kf_moto),
    ("Drone (3D)",  raw_drone, ab_drone, kf_drone),
]
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
fig.patch.set_facecolor(BG)
for ax, (title, raw_e, ab_e, kf_e) in zip(axes, datasets):
    style_ax(ax)
    ax.plot(t_ax, cumulative_rmse(raw_e), color=ORANGE, alpha=0.8, linewidth=1.2, label='Do tho')
    ax.plot(t_ax, cumulative_rmse(ab_e),  color=BLUE,   linewidth=2.0,            label='Alpha-beta')
    ax.plot(t_ax, cumulative_rmse(kf_e),  color=RED,    linewidth=2.0, linestyle='--', label='Kalman')
    ax.axhline(5.0, color='black', linestyle='dotted', linewidth=1.0, label='Nguong 5 m')
    ax.set_title(title, fontsize=11)
    ax.set_xlabel('Thoi gian (s)', fontsize=9)
    ax.set_ylabel('RMSE tich luy (m)', fontsize=9)
    ax.legend(fontsize=8)
    ax.set_ylim(0, 5.2)
    ax.set_xlim(0, 120)
fig.suptitle('Hoi tu RMSE - Seed 42, T = 120 s, R = 400 m', fontsize=12)
plt.tight_layout()
plt.savefig(FIGURES/"rmse_convergence.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved rmse_convergence.png")

# --- Figure 3: Error vs Range ---
R = np.linspace(0, 1200, 500)
k_imu = math.sin(saz)**2 + math.sin(sel)**2
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor(BG)
style_ax(ax)
ax.fill_between(R, 0, np.sqrt(sg**2 + sl**2 + k_imu*R**2), alpha=0.06, color='gray')
ax.plot(R, np.full_like(R, math.sqrt(sg**2+sl**2)), color=GREEN, linewidth=2.0,
        label='sigma_GPS (hang so)')
ax.plot(R, math.sqrt(k_imu)*R, color='#8e44ad', linewidth=2.0, linestyle='--',
        label='sigma_IMU(R) (tuyen tinh)')
ax.plot(R, np.full_like(R, sl), color='#e67e22', linewidth=1.5, linestyle=':',
        label='sigma_Laser (hang so)')
ax.plot(R, np.sqrt(sg**2+sl**2+k_imu*R**2), color=DARK, linewidth=2.5,
        label='sigma_pos tong (RSS)')
ax.axvline(Rcross, color='red', linestyle='-.', linewidth=1.8,
           label=f'Cross-over R ~ {Rcross:.0f} m')
ax.text(Rcross+15, 2.0, f'~{Rcross:.0f} m', color='red', fontsize=11)
ax.set_xlabel('Khoang cach R (m)', fontsize=11)
ax.set_ylabel('Sai so chuan sigma (m)', fontsize=11)
ax.set_title('Mo hinh lan truyen sai so - sigma_pos theo khoang cach', fontsize=12)
ax.legend(fontsize=10, loc='upper left')
ax.set_xlim(0,1200)
ax.set_ylim(0, 9.5)
plt.tight_layout()
plt.savefig(FIGURES/"error_vs_range.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved error_vs_range.png")

# --- Figure 4: Trajectory Top View ---
ab_ped_pos,  kf_ped_pos  = collect_positions(gt_ped,   noisy_ped,   "pedestrian")
ab_moto_pos, kf_moto_pos = collect_positions(gt_moto,  noisy_moto,  "motorcycle")
ab_drone_pos,kf_drone_pos= collect_positions(gt_drone, noisy_drone, "drone")

fig, axes = plt.subplots(1, 3, figsize=(14, 5))
fig.patch.set_facecolor(BG)
traj_sets = [
    ("Nguoi di bo", gt_ped,   ab_ped_pos,   kf_ped_pos),
    ("Xe may",      gt_moto,  ab_moto_pos,  kf_moto_pos),
    ("Drone (3D)",  gt_drone, ab_drone_pos, kf_drone_pos),
]
for ax, (title, gt, ab_pos, kf_pos) in zip(axes, traj_sets):
    style_ax(ax)
    ax.plot(gt[:,0], gt[:,1],       color=GREEN, linewidth=1.8, label='Ground truth', zorder=3)
    ax.plot(kf_pos[:,0], kf_pos[:,1], color=RED, linewidth=1.0, linestyle='--', label='Kalman', alpha=0.8)
    ax.plot(ab_pos[:,0], ab_pos[:,1], color=BLUE, linewidth=1.0, linestyle='-.', label='Alpha-beta', alpha=0.8)
    ax.plot(0, 0, '^', color='black', markersize=8, label='Observer', zorder=5)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel('East (m)', fontsize=9)
    ax.set_ylabel('North (m)', fontsize=9)
    ax.legend(fontsize=8)
    ax.set_aspect('equal', adjustable='datalim')
fig.suptitle('Quy dao muc tieu - mat phang East-North', fontsize=12)
plt.tight_layout()
plt.savefig(FIGURES/"trajectory_topview.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved trajectory_topview.png")

# --- Figure 5: Error Time Series ---
fig, ax = plt.subplots(figsize=(11, 4.5))
fig.patch.set_facecolor(BG)
style_ax(ax)
ax.plot(t_ax, raw_moto, color=ORANGE, alpha=0.6, linewidth=0.8, label='Do tho')
ax.plot(t_ax, ab_moto,  color=BLUE,   linewidth=1.2,            label='Alpha-beta')
ax.plot(t_ax, kf_moto,  color=RED,    linewidth=1.2, linestyle='--', label='Kalman')
ax.axhline(5.0, color='black', linestyle='dotted', linewidth=1.5, label='Nguong 5 m')
ax.set_xlabel('Thoi gian (s)', fontsize=11)
ax.set_ylabel('Sai so vi tri (m)', fontsize=11)
ax.set_title('Sai so vi tri theo thoi gian - kich ban xe may (120 s)', fontsize=12)
ax.legend(fontsize=10)
ax.set_xlim(0,120)
ax.set_ylim(0, 8)
plt.tight_layout()
plt.savefig(FIGURES/"error_timeseries.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved error_timeseries.png")

# --- Figure 6: Error Histogram (pedestrian) ---
fig, ax = plt.subplots(figsize=(9, 4.5))
fig.patch.set_facecolor(BG)
style_ax(ax)
bins = np.arange(0, 4.1, 0.2)
ax.hist(ab_ped, bins=bins, color=BLUE, alpha=0.65, edgecolor='#2E6FA3',
        label=f'Alpha-beta (RMSE={math.sqrt(np.mean(ab_ped**2)):.2f} m)')
ax.hist(kf_ped, bins=bins, color=RED,  alpha=0.65, edgecolor='#96281B',
        label=f'Kalman (RMSE={math.sqrt(np.mean(kf_ped**2)):.2f} m)')
ax.set_xlabel('Sai so tuc thoi (m)', fontsize=11)
ax.set_ylabel('So luong mau', fontsize=11)
ax.set_title('Phan bo sai so tuc thoi - kich ban nguoi di bo (n=1200)', fontsize=11)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig(FIGURES/"error_histogram_pedestrian.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved error_histogram_pedestrian.png")

# --- coord-flow.png ----------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 3.8))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.set_xlim(0, 10)
ax.set_ylim(0, 3.0)
ax.axis('off')

box_data = [
    (0.85, 1.35, "WGS84\nObserver", '#AED6F1'),
    (2.65, 1.35, "ECEF\n(geocentric)", '#A9DFBF'),
    (5.00, 1.35, "ENU\n(local frame)", '#FAD7A0'),
    (7.35, 1.35, "ENU Target\n(offset)", '#F9E79F'),
    (9.15, 1.35, "WGS84\nTarget", '#AED6F1'),
]
for xc, yc, txt, color in box_data:
    rect = mpatches.FancyBboxPatch((xc-0.75, yc-0.45), 1.5, 0.9,
                                    boxstyle="round,pad=0.08",
                                    facecolor=color, edgecolor='#555', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(xc, yc, txt, ha='center', va='center', fontsize=9.5, fontweight='bold')

arrows = [
    (0.85+0.75, 2.65-0.75, "(1)\nellipsoid"),
    (2.65+0.75, 5.0-0.75,  "(2) R_ecef^enu"),
    (5.0+0.75,  7.35-0.75, "(3)\np + d*v"),
    (7.35+0.75, 9.15-0.75, "(4)\ninverse"),
]
for x_from, x_to, label in arrows:
    ax.annotate('', xy=(x_to, 1.35), xytext=(x_from, 1.35),
                arrowprops=dict(arrowstyle='->', color='#333', lw=2.0))
    xm = (x_from + x_to) / 2
    ax.text(xm, 1.95, label, ha='center', va='bottom', fontsize=8, color='#555')

# Extra: Polar input
ax.annotate('', xy=(5.0, 0.9), xytext=(5.0, 0.3),
            arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=1.5))
ax.text(5.0, 0.15, 'Polar(az, el, d) => v(alpha,beta)*d',
        ha='center', va='top', fontsize=8.5, color='#e74c3c')

ax.set_title('Pipeline chuyen doi toa do LLA - ECEF - ENU',
             fontsize=13, fontweight='bold', pad=6)
plt.tight_layout()
plt.savefig(IMAGES/"coord-flow.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved coord-flow.png -> Images/")

# --- real-time-data-pipeline.png ---------------------------------------------
fig, ax = plt.subplots(figsize=(12, 4.8))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.set_xlim(0, 12)
ax.set_ylim(0, 4.8)
ax.axis('off')

def draw_box(ax, xc, yc, w, h, txt, color, edge='#555', fontsize=9):
    rect = mpatches.FancyBboxPatch((xc-w/2, yc-h/2), w, h,
                                    boxstyle="round,pad=0.08",
                                    facecolor=color, edgecolor=edge, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(xc, yc, txt, ha='center', va='center', fontsize=fontsize, fontweight='bold')

# Sensor layer
for xc, label in [(0.8, "GPS"), (1.9, "IMU"), (3.0, "Laser")]:
    draw_box(ax, xc, 3.8, 0.8, 0.6, label, '#F1948A', '#922B21', 10)

draw_box(ax, 1.9, 2.9, 1.0, 0.5, "JSON\npack", '#F8C471', '#B7950B', 9)

for xc in [0.8, 1.9, 3.0]:
    ax.annotate('', xy=(1.9 if abs(xc-1.9)<0.5 else (1.5 if xc<1.9 else 2.3), 3.15),
                xytext=(xc, 3.5),
                arrowprops=dict(arrowstyle='->', color='#999', lw=1.0,
                                connectionstyle='arc3,rad=0.15'))

# WebSocket 1
ax.annotate('', xy=(4.3, 2.9), xytext=(2.4, 2.9),
            arrowprops=dict(arrowstyle='->', color='#1a5276', lw=2.0))
ax.text(3.35, 3.15, 'WebSocket', ha='center', va='bottom', fontsize=8.5, color='#1a5276')

# Server steps
srv = [("Coord\nConvert", 4.9), ("Sensor\nFusion", 6.2),
       ("Kalman /\nAlpha-b.", 7.5), ("WGS84\nout", 8.8)]
for label, xc in srv:
    draw_box(ax, xc, 2.9, 1.05, 0.7, label, '#A9DFBF', '#1E8449', 9)

for i in range(len(srv)-1):
    ax.annotate('', xy=(srv[i+1][1]-0.53, 2.9),
                xytext=(srv[i][1]+0.53, 2.9),
                arrowprops=dict(arrowstyle='->', color='#1E8449', lw=1.5))

# WebSocket 2
ax.annotate('', xy=(10.0, 2.9), xytext=(9.33, 2.9),
            arrowprops=dict(arrowstyle='->', color='#1a5276', lw=2.0))
ax.text(9.67, 3.15, 'WebSocket', ha='center', va='bottom', fontsize=8.5, color='#1a5276')

# Frontend
draw_box(ax, 10.7, 2.9, 1.3, 0.7, "React\nLeaflet\nMap", '#AED6F1', '#1A5276', 9)

# Layer labels
label_y = 4.3
ax.text(1.9, label_y, 'Tang cam bien (Raspberry Pi)',
        ha='center', fontsize=9.5, fontweight='bold', color='#922B21',
        bbox=dict(boxstyle='round', facecolor='#FADBD8', alpha=0.7))
ax.text(6.7, label_y, 'Tang may chu (FastAPI, Python)',
        ha='center', fontsize=9.5, fontweight='bold', color='#1E8449',
        bbox=dict(boxstyle='round', facecolor='#D5F5E3', alpha=0.7))
ax.text(10.7, label_y, 'Tang giao dien',
        ha='center', fontsize=9.5, fontweight='bold', color='#1A5276',
        bbox=dict(boxstyle='round', facecolor='#D6EAF8', alpha=0.7))

# Bottom: cycle note
ax.text(6.0, 0.4, 'Chu ky xu ly: 10 Hz (100 ms / buoc) | Tong tre <= 12 ms (LAN)',
        ha='center', va='center', fontsize=9, style='italic', color='#555',
        bbox=dict(boxstyle='round', facecolor='#FDFEFE', edgecolor='#BFC9CA'))

ax.set_title('Pipeline du lieu thoi gian thuc tu cam bien den giao dien',
             fontsize=12, fontweight='bold', pad=8)
plt.tight_layout()
plt.savefig(IMAGES/"real-time-data-pipeline.png", dpi=150, bbox_inches='tight')
plt.close()
print("  Saved real-time-data-pipeline.png -> Images/")

print("\n=== All done. ===")
