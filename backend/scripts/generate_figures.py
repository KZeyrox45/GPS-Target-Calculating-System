"""
generate_figures.py  - (re)generates all report figures using the actual simulation engine.

Run from backend/ directory:
    uv run python scripts/generate_figures.py

Outputs:
    report-weekly/figures/*.png       - benchmark charts
    report-weekly/Images/coord-flow.png
    report-weekly/Images/real-time-data-pipeline.png
"""

import sys
import math
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

BACKEND = pathlib.Path(__file__).parent.parent
FIGURES = BACKEND.parent / "report-weekly" / "figures"
IMAGES  = BACKEND.parent / "report-weekly" / "Images"
FIGURES.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BACKEND))

from app.simulation.target_simulator import (
    PedestrianTrajectory, MotorcycleTrajectory, DroneTrajectory,
)
from app.simulation.sensor_noise import SensorNoiseModel
from app.algorithms.kalman_filter import KalmanFilter, KalmanFilter3D
from app.algorithms.alpha_beta_filter import AlphaBetaFilter
from app.algorithms.sensor_fusion import fuse_sensors

# --- Parameters (mirror benchmark_rmse.py) ------------------------------------
SEED      = 42
DT        = 0.1       # 10 Hz
N_STEPS   = 1200      # 120 s
OBS_LAT, OBS_LON, OBS_ALT = 10.762622, 106.660172, 10.0

ORANGE = '#E07B39'
BLUE = '#4A8FD4'
RED = '#C0392B'
GREEN = '#27ae60'
DARK   = '#2c3e50'
BG   = '#f9f9f9'


def style_ax(ax):
    ax.set_facecolor(BG)
    ax.grid(linestyle='--', alpha=0.45)


def run_scenario(target_type, collect_axis=False):
    """
    Returns dict with:
        raw_err, ab_err, kf_err  : arrays of 2D position errors (m)
        raw_pos, ab_pos, kf_pos  : arrays of (E, N) positions
        gt_pos                   : ground-truth (E, N) arrays
    """
    rng = np.random.default_rng(SEED)
    TRAJ_MAP = {
        "pedestrian": PedestrianTrajectory,
        "motorcycle": MotorcycleTrajectory,
        "drone":      DroneTrajectory,
    }
    traj  = TRAJ_MAP[target_type](rng=rng, dt=DT)
    noise = SensorNoiseModel.from_target_type(target_type, seed=SEED)
    is_3d = (target_type == "drone")

    kf = KalmanFilter3D(dt=DT) if is_3d else KalmanFilter(dt=DT, target_type=target_type)
    ab = AlphaBetaFilter(alpha=0.4, dt=DT)

    raw_err = np.zeros(N_STEPS)
    ab_err = np.zeros(N_STEPS)
    kf_err = np.zeros(N_STEPS)
    gt_pos  = np.zeros((N_STEPS, 2))
    raw_pos = np.zeros((N_STEPS, 2))
    ab_pos  = np.zeros((N_STEPS, 2))
    kf_pos  = np.zeros((N_STEPS, 2))

    if collect_axis:
        raw_eE = np.zeros(N_STEPS)
        raw_eN = np.zeros(N_STEPS)
        ab_eE  = np.zeros(N_STEPS)
        ab_eN  = np.zeros(N_STEPS)
        kf_eE  = np.zeros(N_STEPS)
        kf_eN  = np.zeros(N_STEPS)

    for i in range(N_STEPS):
        gt_e, gt_n, gt_u = traj.step()
        gt_pos[i] = [gt_e, gt_n]

        true_az  = math.degrees(math.atan2(gt_e, gt_n)) % 360
        true_rng = math.sqrt(gt_e**2 + gt_n**2 + gt_u**2)
        horiz    = math.sqrt(gt_e**2 + gt_n**2)
        true_el  = math.degrees(math.atan2(gt_u, horiz))

        noisy_az  = noise.apply_azimuth_noise(true_az)
        noisy_el  = noise.apply_elevation_noise(true_el)
        noisy_rng = noise.apply_range_noise(true_rng)

        fused = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, noisy_az, noisy_el, noisy_rng)

        raw_pos[i] = [fused.east, fused.north]
        raw_err[i] = math.sqrt((fused.east - gt_e)**2 + (fused.north - gt_n)**2)

        ab_state = ab.step(fused.east, fused.north)
        ab_pos[i] = ab_state[:2]
        ab_err[i] = math.sqrt((ab_state[0] - gt_e)**2 + (ab_state[1] - gt_n)**2)

        if is_3d:
            kf_state = kf.step(fused.east, fused.north, fused.up, sigma_pos_m=fused.sigma_pos_m)
        else:
            kf_state = kf.step(fused.east, fused.north, sigma_pos_m=fused.sigma_pos_m)
        kf_pos[i] = kf_state[:2]
        kf_err[i] = math.sqrt((kf_state[0] - gt_e)**2 + (kf_state[1] - gt_n)**2)

        if collect_axis:
            raw_eE[i] = fused.east  - gt_e
            raw_eN[i] = fused.north - gt_n
            ab_eE[i]  = ab_state[0] - gt_e
            ab_eN[i]  = ab_state[1] - gt_n
            kf_eE[i]  = kf_state[0] - gt_e
            kf_eN[i]  = kf_state[1] - gt_n

    result = dict(raw_err=raw_err, ab_err=ab_err, kf_err=kf_err,
                  gt_pos=gt_pos, raw_pos=raw_pos, ab_pos=ab_pos, kf_pos=kf_pos)
    if collect_axis:
        result.update(raw_eE=raw_eE, raw_eN=raw_eN,
                      ab_eE=ab_eE,   ab_eN=ab_eN,
                      kf_eE=kf_eE,   kf_eN=kf_eN)
    return result


def cumulative_rmse(err):
    return np.sqrt(np.cumsum(err**2) / np.arange(1, len(err)+1))


# --- Run all scenarios --------------------------------------------------------
print("Running simulations using actual engine (seed=42, 10 Hz, 120 s) ...")
ped  = run_scenario("pedestrian", collect_axis=True)
moto = run_scenario("motorcycle")
dron = run_scenario("drone")

# --- Print verification -------------------------------------------------------
print("\n=== RMSE VERIFICATION ===")
for label, d in [("Pedestrian", ped), ("Motorcycle", moto), ("Drone", dron)]:
    r = math.sqrt(np.mean(d["raw_err"]**2))
    a = math.sqrt(np.mean(d["ab_err"]**2))
    k = math.sqrt(np.mean(d["kf_err"]**2))
    print(f"  {label:12s}: raw={r:.3f}  ab={a:.3f}  kf={k:.3f}  m")

print("\n=== Pedestrian sigma_E / sigma_N ===")
print(f"  Raw:        sigE={np.std(ped['raw_eE']):.3f}  sigN={np.std(ped['raw_eN']):.3f}")
print(f"  Alpha-beta: sigE={np.std(ped['ab_eE']):.3f}  sigN={np.std(ped['ab_eN']):.3f}")
print(f"  Kalman:     sigE={np.std(ped['kf_eE']):.3f}  sigN={np.std(ped['kf_eN']):.3f}")

print("\n=== Cross-over range ===")
saz = math.radians(0.3)
sel = math.radians(0.2)
sg = 5.0
sl = 0.5
Rcross = sg / math.sqrt(math.sin(saz)**2 + math.sin(sel)**2)
print(f"  R_cross = {Rcross:.1f} m")

print("\n=== Pipeline timing percentages ===")
times = [("LLA->ECEF", 2.1), ("ECEF->ENU", 3.8), ("SensorFusion", 1.2),
         ("Kalman", 48.5), ("ENU->LLA", 3.4)]
total_us = sum(t for _, t in times)
for name, t in times:
    print(f"  {name:20s}: {100*t/total_us:.1f}%")

print("\n=== Histogram (pedestrian, pgfplots format) ===")
bins = np.arange(0, 5.1, 0.2)
centers = (bins[:-1] + bins[1:]) / 2
ab_h, _ = np.histogram(ped["ab_err"], bins=bins)
kf_h, _ = np.histogram(ped["kf_err"], bins=bins)
print("  AB:", " ".join(f"({c:.1f},{h})" for c, h in zip(centers, ab_h) if h > 0))
print("  KF:", " ".join(f"({c:.1f},{h})" for c, h in zip(centers, kf_h) if h > 0))
print(f"  AB total={ab_h.sum()}  KF total={kf_h.sum()}")

print("\n=== Beta formula ===")
alpha_v = 0.4
beta_code   = (2 - alpha_v) - 2 * math.sqrt(1 - alpha_v)
beta_simple = alpha_v**2 / (2 - alpha_v)
print(f"  Code  (2-a)-2*sqrt(1-a) => beta = {beta_code:.5f}")
print(f"  Report a^2/(2-a)         => beta = {beta_simple:.5f}")

# --- Figure 1: RMSE Bar Comparison -------------------------------------------
raw_f = [math.sqrt(np.mean(d["raw_err"]**2)) for d in [ped, moto, dron]]
ab_f  = [math.sqrt(np.mean(d["ab_err"]**2))  for d in [ped, moto, dron]]
kf_f  = [math.sqrt(np.mean(d["kf_err"]**2))  for d in [ped, moto, dron]]

x = np.arange(3)
w = 0.26
fig, ax = plt.subplots(figsize=(10, 5.5))
fig.patch.set_facecolor(BG)
style_ax(ax)
b1 = ax.bar(x-w, raw_f, w, label='Do tho',     color=ORANGE, edgecolor='#B5612B', zorder=3)
b2 = ax.bar(x,   ab_f,  w, label='Alpha-beta', color=BLUE,   edgecolor='#2E6FA3', zorder=3)
b3 = ax.bar(x+w, kf_f,  w, label='Kalman',     color=RED,    edgecolor='#96281B', zorder=3)
ax.axhline(5.0, color='black', linestyle='dotted', linewidth=1.5, label='Yeu cau < 5 m')
ax.set_xticks(x)
ax.set_xticklabels(["Nguoi di bo", "Xe may", "Drone (3D)"], fontsize=12)
ax.set_ylabel('RMSE cuoi phien (m)', fontsize=11)
ax.set_title('So sanh RMSE cuoi phien - Seed 42, T = 120 s, R = 400 m', fontsize=12)
ax.legend(fontsize=10)
ax.set_ylim(0, 3.5)
for bar in [*b1, *b2, *b3]:
    h = bar.get_height()
    ax.text(bar.get_x()+bar.get_width()/2, h+0.05, f'{h:.2f}',
            ha='center', va='bottom', fontsize=9, fontweight='bold')
plt.tight_layout()
plt.savefig(FIGURES/"rmse_bar_comparison.png", dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved rmse_bar_comparison.png")

# --- Figure 2: RMSE Convergence -----------------------------------------------
t_ax = np.arange(N_STEPS) * DT
datasets = [
    ("Nguoi di bo", ped["raw_err"],  ped["ab_err"],  ped["kf_err"]),
    ("Xe may",      moto["raw_err"], moto["ab_err"], moto["kf_err"]),
    ("Drone (3D)",  dron["raw_err"], dron["ab_err"], dron["kf_err"]),
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
print("Saved rmse_convergence.png")

# --- Figure 3: Error vs Range --------------------------------------------------
R_arr = np.linspace(0, 1200, 500)
k_imu = math.sin(saz)**2 + math.sin(sel)**2
fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor(BG)
style_ax(ax)
sigma_total = np.sqrt(sg**2 + sl**2 + k_imu * R_arr**2)
ax.fill_between(R_arr, 0, sigma_total, alpha=0.06, color='gray')
ax.plot(R_arr, np.full_like(R_arr, math.sqrt(sg**2+sl**2)), color=GREEN, linewidth=2.0,
        label='$\\sigma_{GPS}$ + $\\sigma_{Laser}$ (hang so)')
ax.plot(R_arr, math.sqrt(k_imu)*R_arr, color='#8e44ad', linewidth=2.0, linestyle='--',
        label='$\\sigma_{IMU}(R)$ (tuyen tinh)')
ax.plot(R_arr, np.full_like(R_arr, sl), color='#e67e22', linewidth=1.5, linestyle=':',
        label='$\\sigma_{Laser}$ = 0.5 m')
ax.plot(R_arr, sigma_total, color=DARK, linewidth=2.5, label='$\\sigma_{pos}$ tong (RSS)')
ax.axvline(Rcross, color='red', linestyle='-.', linewidth=1.8,
           label=f'Cross-over R ~ {Rcross:.0f} m')
ax.text(Rcross+20, 1.5, f'~{Rcross:.0f} m', color='red', fontsize=11)
ax.set_xlabel('Khoang cach R (m)', fontsize=11)
ax.set_ylabel('Sai so chuan sigma (m)', fontsize=11)
ax.set_title('Mo hinh lan truyen sai so - $\\sigma_{pos}$ theo khoang cach', fontsize=12)
ax.legend(fontsize=10, loc='upper left')
ax.set_xlim(0, 1200)
ax.set_ylim(0, 9.5)
plt.tight_layout()
plt.savefig(FIGURES/"error_vs_range.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved error_vs_range.png")

# --- Figure 4: Trajectory Top View --------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
fig.patch.set_facecolor(BG)
traj_sets = [
    ("Nguoi di bo", ped),
    ("Xe may",      moto),
    ("Drone (3D)",  dron),
]
for ax, (title, d) in zip(axes, traj_sets):
    style_ax(ax)
    ax.plot(d["gt_pos"][:,0],  d["gt_pos"][:,1],  color=GREEN, linewidth=2.0, label='Ground truth', zorder=3)
    ax.plot(d["kf_pos"][:,0],  d["kf_pos"][:,1],  color=RED,   linewidth=1.0, linestyle='--', label='Kalman', alpha=0.8)
    ax.plot(d["ab_pos"][:,0],  d["ab_pos"][:,1],  color=BLUE,  linewidth=1.0, linestyle='-.', label='Alpha-beta', alpha=0.8)
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
print("Saved trajectory_topview.png")

# --- Figure 5: Error Time Series (motorcycle) ---------------------------------
fig, ax = plt.subplots(figsize=(11, 4.5))
fig.patch.set_facecolor(BG)
style_ax(ax)
ax.plot(t_ax, moto["raw_err"], color=ORANGE, alpha=0.6, linewidth=0.8, label='Do tho')
ax.plot(t_ax, moto["ab_err"],  color=BLUE,   linewidth=1.2,            label='Alpha-beta')
ax.plot(t_ax, moto["kf_err"],  color=RED,    linewidth=1.2, linestyle='--', label='Kalman')
ax.axhline(5.0, color='black', linestyle='dotted', linewidth=1.5, label='Nguong 5 m')
ax.set_xlabel('Thoi gian (s)', fontsize=11)
ax.set_ylabel('Sai so vi tri (m)', fontsize=11)
ax.set_title('Sai so vi tri theo thoi gian - kich ban xe may (120 s)', fontsize=12)
ax.legend(fontsize=10)
ax.set_xlim(0, 120)
ax.set_ylim(0)
plt.tight_layout()
plt.savefig(FIGURES/"error_timeseries.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved error_timeseries.png")

# --- Figure 6: Error Histogram (pedestrian) -----------------------------------
fig, ax = plt.subplots(figsize=(9, 4.5))
fig.patch.set_facecolor(BG)
style_ax(ax)
bins_h = np.arange(0, 5.1, 0.2)
ab_rmse_v = math.sqrt(np.mean(ped["ab_err"]**2))
kf_rmse_v = math.sqrt(np.mean(ped["kf_err"]**2))
ax.hist(ped["ab_err"], bins=bins_h, color=BLUE, alpha=0.65, edgecolor='#2E6FA3',
        label=f'Alpha-beta (RMSE={ab_rmse_v:.2f} m)')
ax.hist(ped["kf_err"], bins=bins_h, color=RED,  alpha=0.65, edgecolor='#96281B',
        label=f'Kalman (RMSE={kf_rmse_v:.2f} m)')
ax.set_xlabel('Sai so tuc thoi (m)', fontsize=11)
ax.set_ylabel('So luong mau', fontsize=11)
ax.set_title('Phan bo sai so tuc thoi - kich ban nguoi di bo (n=1200)', fontsize=11)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig(FIGURES/"error_histogram_pedestrian.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved error_histogram_pedestrian.png")

# --- Images: coord-flow.png --------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 3.6))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.set_xlim(0, 11)
ax.set_ylim(0, 3.0)
ax.axis('off')

BOX_COLOR = ['#AED6F1', '#A9DFBF', '#FAD7A0', '#F9E79F', '#AED6F1']
BOX_ITEMS = [
    (1.0,  "WGS84\nObserver"),
    (3.0,  "ECEF\n(geocentric)"),
    (5.5,  "ENU\n(local frame)"),
    (8.0,  "ENU Target\n(after fusion)"),
    (10.0, "WGS84\nTarget"),
]
for (xc, txt), col in zip(BOX_ITEMS, BOX_COLOR):
    rect = mpatches.FancyBboxPatch((xc-0.85, 1.15), 1.7, 0.85,
                                    boxstyle="round,pad=0.08",
                                    facecolor=col, edgecolor='#555', linewidth=1.5)
    ax.add_patch(rect)
    ax.text(xc, 1.575, txt, ha='center', va='center', fontsize=9.5, fontweight='bold')

ARROW_STEPS = [
    (1.85, 2.15, "(1)\nWGS84->ECEF"),
    (3.85, 4.65, "(2)\nR_ecef^enu"),
    (6.35, 7.15, "(3)\np + d*v_unit"),
    (8.85, 9.15, "(4)\nECEF->WGS84"),
]
for x0, x1, lbl in ARROW_STEPS:
    ax.annotate('', xy=(x1, 1.575), xytext=(x0, 1.575),
                arrowprops=dict(arrowstyle='->', color='#333', lw=2.0))
    xm = (x0+x1)/2
    ax.text(xm, 2.15, lbl, ha='center', va='bottom', fontsize=8.5, color='#555')

# Polar input arrow
ax.annotate('', xy=(5.5, 1.15), xytext=(5.5, 0.45),
            arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=1.5))
ax.text(5.5, 0.25, 'Polar (az, el, d) + sigma_pos',
        ha='center', va='top', fontsize=8.5, color='#e74c3c')

ax.set_title('Pipeline chuyen doi toa do  LLA - ECEF - ENU',
             fontsize=12, fontweight='bold', pad=6)
plt.tight_layout()
plt.savefig(IMAGES/"coord-flow.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved coord-flow.png -> Images/")

# --- Images: real-time-data-pipeline.png -------------------------------------
fig, ax = plt.subplots(figsize=(13, 5.0))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.set_xlim(0, 13)
ax.set_ylim(0, 5.0)
ax.axis('off')

def draw_box(ax, xc, yc, w, h, txt, fc, ec='#555', fs=9):
    rect = mpatches.FancyBboxPatch((xc-w/2, yc-h/2), w, h,
                                    boxstyle="round,pad=0.08",
                                    facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(rect)
    ax.text(xc, yc, txt, ha='center', va='center', fontsize=fs, fontweight='bold')

# Sensor boxes
for xc, lbl in [(0.8, "GPS"), (1.9, "IMU"), (3.0, "Laser")]:
    draw_box(ax, xc, 3.8, 0.85, 0.6, lbl, '#F1948A', '#922B21', 10)

draw_box(ax, 1.9, 2.9, 1.0, 0.55, "JSON\npack", '#F8C471', '#B7950B', 9)

for xc in [0.8, 1.9, 3.0]:
    xdst = 1.5 if xc < 1.9 else (1.9 if abs(xc-1.9) < 0.2 else 2.3)
    ax.annotate('', xy=(xdst, 3.175), xytext=(xc, 3.5),
                arrowprops=dict(arrowstyle='->', color='#aaa', lw=1.0,
                                connectionstyle='arc3,rad=0.2'))

ax.annotate('', xy=(4.3, 2.9), xytext=(2.4, 2.9),
            arrowprops=dict(arrowstyle='->', color='#1a5276', lw=2.0))
ax.text(3.35, 3.15, 'WebSocket', ha='center', va='bottom', fontsize=8.5, color='#1a5276')

# Server pipeline
srv = [("Coord\nConvert", 4.95), ("Sensor\nFusion", 6.35),
       ("Kalman /\nAlpha-b.", 7.75), ("WGS84\nout", 9.15)]
for lbl, xc in srv:
    draw_box(ax, xc, 2.9, 1.1, 0.7, lbl, '#A9DFBF', '#1E8449', 9)

for i in range(len(srv)-1):
    ax.annotate('', xy=(srv[i+1][1]-0.55, 2.9),
                xytext=(srv[i][1]+0.55, 2.9),
                arrowprops=dict(arrowstyle='->', color='#1E8449', lw=1.5))

ax.annotate('', xy=(10.6, 2.9), xytext=(9.7, 2.9),
            arrowprops=dict(arrowstyle='->', color='#1a5276', lw=2.0))
ax.text(10.15, 3.15, 'WebSocket', ha='center', va='bottom', fontsize=8.5, color='#1a5276')

draw_box(ax, 11.5, 2.9, 1.5, 0.7, "React\nLeaflet\nMap", '#AED6F1', '#1A5276', 9)

# Layer labels
for xc, txt, fc, ec in [
    (1.9, 'Tang cam bien (Raspberry Pi)', '#FADBD8', '#922B21'),
    (7.0, 'Tang may chu (FastAPI, Python)', '#D5F5E3', '#1E8449'),
    (11.5, 'Tang giao dien', '#D6EAF8', '#1A5276'),
]:
    ax.text(xc, 4.4, txt, ha='center', fontsize=9.5, fontweight='bold',
            color=ec, bbox=dict(boxstyle='round', facecolor=fc, alpha=0.8))

ax.text(6.5, 0.4, 'Chu ky xu ly: 10 Hz (100 ms / buoc)  |  Tre truyen dat qua LAN <= 12 ms',
        ha='center', va='center', fontsize=9, style='italic', color='#555',
        bbox=dict(boxstyle='round', facecolor='#FDFEFE', edgecolor='#BFC9CA'))

ax.set_title('Pipeline du lieu thoi gian thuc tu cam bien den giao dien',
             fontsize=12, fontweight='bold', pad=8)
plt.tight_layout()
plt.savefig(IMAGES/"real-time-data-pipeline.png", dpi=150, bbox_inches='tight')
plt.close()
print("Saved real-time-data-pipeline.png -> Images/")

print("\n=== All figures saved successfully. ===")
