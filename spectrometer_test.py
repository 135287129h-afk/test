"""
高利通光纤光谱仪测试程序 (GUI版)
SDK: Glit_Demo_Support_libs_20250106
功能: 设备连接、积分时间、平均次数、测量模式、光谱实时显示、日志
"""

import csv
import ctypes
import os
import sys
import time
import queue
import threading
import logging
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ======================== 日志配置 ========================
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"spec_{datetime.datetime.now():%Y%m%d_%H%M%S}.log")

logger = logging.getLogger("Spectrometer")
logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
_fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(_fh)

# ======================== SDK 路径配置 ========================
SDK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "Glit_Demo_Support_libs_20250106")
LIB_DIR = os.path.join(SDK_DIR, "lib", "x64")

os.environ['PATH'] = LIB_DIR + ';' + os.environ.get('PATH', '')
ftd2xx = ctypes.CDLL(os.path.join(LIB_DIR, "ftd2xx64.dll"))
xgusb = ctypes.CDLL(os.path.join(LIB_DIR, "xGUSB64.dll"))
glaDevSys = ctypes.CDLL(os.path.join(LIB_DIR, "glaDevSys64.dll"))

# ======================== 常量 ========================
NOERROR = 0
MAX_PIXELS = 4096
IFS_USB_FT = 0
MSM_IRRAD = 0
MSM_TRAN = 1
MSM_REF = 2
MSM_ABS = 3
MODE_NAMES = {0: '辐照度', 1: '透射率', 2: '反射率', 3: '吸光度'}

# ======================== CIE 1931 2° 标准观察者 ========================
# [wl_nm, x_bar, y_bar, z_bar]  380-780nm, 5nm step
_CIE_RAW = np.array([
    [380,0.001368,0.000039,0.006450],[385,0.002236,0.000064,0.010550],
    [390,0.004243,0.000120,0.020050],[395,0.007650,0.000217,0.036210],
    [400,0.014310,0.000396,0.067850],[405,0.023190,0.000640,0.110200],
    [410,0.043510,0.001210,0.207400],[415,0.077630,0.002180,0.371300],
    [420,0.134380,0.004000,0.645600],[425,0.214770,0.007300,1.039050],
    [430,0.283900,0.011600,1.385600],[435,0.328500,0.016840,1.622960],
    [440,0.348280,0.023000,1.747060],[445,0.348060,0.029800,1.782600],
    [450,0.336200,0.038000,1.772110],[455,0.318700,0.048000,1.744100],
    [460,0.290800,0.060000,1.669200],[465,0.251100,0.073900,1.528100],
    [470,0.195360,0.090980,1.287640],[475,0.142100,0.112600,1.041900],
    [480,0.095640,0.139020,0.812950],[485,0.058950,0.169300,0.616200],
    [490,0.032010,0.208020,0.465180],[495,0.014700,0.258600,0.353300],
    [500,0.004900,0.323000,0.272000],[505,0.002400,0.407300,0.212300],
    [510,0.009300,0.503000,0.158200],[515,0.029100,0.608200,0.111700],
    [520,0.063270,0.710000,0.078250],[525,0.109600,0.793200,0.057250],
    [530,0.165500,0.862000,0.042160],[535,0.225750,0.914850,0.029840],
    [540,0.290400,0.954000,0.020300],[545,0.359700,0.980300,0.013400],
    [550,0.433450,0.994950,0.008750],[555,0.512050,1.000000,0.005750],
    [560,0.594500,0.995000,0.003900],[565,0.678400,0.978600,0.002750],
    [570,0.762100,0.952000,0.002100],[575,0.842500,0.915400,0.001800],
    [580,0.916300,0.870000,0.001650],[585,0.978600,0.816300,0.001400],
    [590,1.026300,0.757000,0.001100],[595,1.056700,0.694900,0.001000],
    [600,1.062200,0.631000,0.000800],[605,1.045600,0.566800,0.000600],
    [610,1.002600,0.503000,0.000340],[615,0.938400,0.441200,0.000240],
    [620,0.854450,0.381000,0.000190],[625,0.751400,0.321000,0.000100],
    [630,0.642400,0.265000,0.000050],[635,0.541900,0.217000,0.000030],
    [640,0.447900,0.175000,0.000020],[645,0.360800,0.138200,0.000010],
    [650,0.283500,0.107000,0.000000],[655,0.218700,0.081600,0.000000],
    [660,0.164900,0.061000,0.000000],[665,0.121200,0.044580,0.000000],
    [670,0.087400,0.032000,0.000000],[675,0.063600,0.023200,0.000000],
    [680,0.046770,0.017000,0.000000],[685,0.032900,0.011920,0.000000],
    [690,0.022700,0.008210,0.000000],[695,0.015840,0.005723,0.000000],
    [700,0.011359,0.004102,0.000000],[705,0.008111,0.002929,0.000000],
    [710,0.005790,0.002091,0.000000],[715,0.004109,0.001484,0.000000],
    [720,0.002899,0.001047,0.000000],[725,0.002049,0.000740,0.000000],
    [730,0.001440,0.000520,0.000000],[735,0.001000,0.000361,0.000000],
    [740,0.000690,0.000249,0.000000],[745,0.000476,0.000172,0.000000],
    [750,0.000332,0.000120,0.000000],[755,0.000235,0.000085,0.000000],
    [760,0.000166,0.000060,0.000000],[765,0.000117,0.000042,0.000000],
    [770,0.000083,0.000030,0.000000],[775,0.000059,0.000021,0.000000],
    [780,0.000042,0.000015,0.000000],
], dtype=np.float64)
_CIE_WL = _CIE_RAW[:, 0]
_CIE_X = _CIE_RAW[:, 1]
_CIE_Y = _CIE_RAW[:, 2]
_CIE_Z = _CIE_RAW[:, 3]
# D65 标准光源白点
_D65_X, _D65_Y = 0.31272, 0.32903
# 光谱轨迹端点 (用于色品图绘制)
_SLOCUS_X = np.array([0.1741,0.1740,0.1738,0.1736,0.1733,0.1730,0.1726,0.1721,0.1714,0.1703,0.1689,0.1669,0.1644,0.1611,0.1566,0.1510,0.1440,0.1355,0.1241,0.1096,0.0913,0.0687,0.0454,0.0235,0.0082,0.0039,0.0139,0.0389,0.0743,0.1142,0.1547,0.1929,0.2296,0.2658,0.3016,0.3373,0.3731,0.4087,0.4441,0.4788,0.5125,0.5448,0.5752,0.6029,0.6270,0.6482,0.6658,0.6801,0.6915,0.7006,0.7079,0.7140,0.7190,0.7230,0.7260,0.7283,0.7300,0.7311,0.7320,0.7327,0.7334,0.7340,0.7344,0.7346,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347,0.7347])
_SLOCUS_Y = np.array([0.0050,0.0050,0.0049,0.0049,0.0048,0.0048,0.0048,0.0051,0.0058,0.0069,0.0086,0.0109,0.0138,0.0177,0.0227,0.0297,0.0399,0.0578,0.0868,0.1327,0.2007,0.2950,0.4127,0.5384,0.6548,0.7502,0.8120,0.8338,0.8262,0.8059,0.7816,0.7543,0.7243,0.6923,0.6589,0.6245,0.5896,0.5547,0.5202,0.4866,0.4544,0.4242,0.3965,0.3725,0.3514,0.3340,0.3197,0.3083,0.2993,0.2920,0.2859,0.2809,0.2770,0.2740,0.2717,0.2700,0.2689,0.2680,0.2673,0.2666,0.2660,0.2656,0.2654,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653,0.2653])
_SLOCUS_WL = np.linspace(380, 780, len(_SLOCUS_X))

def _interp_cie(wavelengths):
    """将 CIE 色匹配函数插值到光谱仪波长网格"""
    x = np.interp(wavelengths, _CIE_WL, _CIE_X)
    y = np.interp(wavelengths, _CIE_WL, _CIE_Y)
    z = np.interp(wavelengths, _CIE_WL, _CIE_Z)
    return x, y, z

def _compute_chromaticity(spectrum, wavelengths):
    """计算色坐标 x, y 和亮度 Y"""
    x_bar, y_bar, z_bar = _interp_cie(wavelengths)
    dw = np.diff(wavelengths)
    dw = np.append(dw, dw[-1])
    X = np.sum(spectrum * x_bar * dw)
    Y = np.sum(spectrum * y_bar * dw)
    Z = np.sum(spectrum * z_bar * dw)
    s = X + Y + Z
    if s == 0:
        return 0.0, 0.0, 0.0
    return X / s, Y / s, Y

def _compute_dominant_wavelength(cx, cy):
    """计算主波长 (nm)，通过 D65→测试点直线与光谱轨迹求交"""
    dx, dy = cx - _D65_X, cy - _D65_Y
    if abs(dx) < 1e-10 and abs(dy) < 1e-10:
        return None, None

    best_t = None
    best_wl = None
    # 遍历光谱轨迹的每一段，找直线交点
    for i in range(len(_SLOCUS_X) - 1):
        # 光谱轨迹线段: P + s*(Q-P)
        px, py = _SLOCUS_X[i] - _D65_X, _SLOCUS_Y[i] - _D65_Y
        qx, qy = _SLOCUS_X[i+1] - _D65_X, _SLOCUS_Y[i+1] - _D65_Y
        ex, ey = qx - px, qy - py
        denom = dx * ey - dy * ex
        if abs(denom) < 1e-15:
            continue
        t = (px * ey - py * ex) / denom
        s = (px * dy - py * dx) / denom if abs(ex) > abs(ey) else (t * dx - px) / ex
        if t > 1e-6 and 0 <= s <= 1:
            if best_t is None or t < best_t:
                best_t = t
                best_wl = _SLOCUS_WL[i] + s * (_SLOCUS_WL[i+1] - _SLOCUS_WL[i])

    if best_wl is None:
        return None, None

    # 色纯度
    d_center = np.sqrt(dx**2 + dy**2)
    iseg = int((best_wl - 380) / 5)
    iseg = max(0, min(iseg, len(_SLOCUS_X) - 2))
    frac = (best_wl - _SLOCUS_WL[iseg]) / (_SLOCUS_WL[iseg+1] - _SLOCUS_WL[iseg])
    ix = _SLOCUS_X[iseg] + frac * (_SLOCUS_X[iseg+1] - _SLOCUS_X[iseg])
    iy = _SLOCUS_Y[iseg] + frac * (_SLOCUS_Y[iseg+1] - _SLOCUS_Y[iseg])
    d_locus = np.sqrt((ix - _D65_X)**2 + (iy - _D65_Y)**2)
    purity = d_center / d_locus if d_locus > 0 else 0.0
    return float(best_wl), purity

COLORS = {
    'bg': '#1a1a2e',
    'panel': '#16213e',
    'accent': '#0f9b8e',
    'accent_hover': '#0d8a7f',
    'accent_light': '#1a3a4a',
    'success': '#4caf50',
    'danger': '#ef5350',
    'warning': '#ffb74d',
    'text': '#e0e0e0',
    'text_sec': '#9e9e9e',
    'text_bright': '#ffffff',
    'border': '#2a3a5a',
    'chart_bg': '#0f1a30',
    'chart_grid': '#1e2d4a',
    'btn_face': '#1e2d4a',
    'header_bg': '#0f1a30',
    'log_bg': '#0a0f1a',
}


class DEVLST(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_ulong),
        ("locid", ctypes.c_ulong),
        ("devnums", ctypes.c_ulong),
        ("serialnumber", ctypes.c_char * 16),
        ("description", ctypes.c_char * 64),
    ]


# ======================== SDK 初始化 ========================
glaDevSys.USB_GetDeviceList.argtypes = [
    ctypes.POINTER(DEVLST), ctypes.POINTER(ctypes.c_uint)]
glaDevSys.USB_GetDeviceList.restype = ctypes.c_int

glaDevSys.glaDevOpen.argtypes = [
    ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
glaDevSys.glaDevOpen.restype = ctypes.c_int

glaDevSys.glaDevClose.argtypes = [ctypes.c_int, ctypes.c_int]
glaDevSys.glaDevClose.restype = ctypes.c_int

glaDevSys.glaSetExposure.argtypes = [ctypes.c_int, ctypes.c_double, ctypes.c_uint]
glaDevSys.glaSetExposure.restype = ctypes.c_int

glaDevSys.glaGetExposure.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
glaDevSys.glaGetExposure.restype = ctypes.c_int

glaDevSys.glaSetCollectTimesMode_Firmware.argtypes = [ctypes.c_int, ctypes.c_uint]
glaDevSys.glaSetCollectTimesMode_Firmware.restype = ctypes.c_int

glaDevSys.glaGetCollectTimesMode_Firmware.argtypes = [
    ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
glaDevSys.glaGetCollectTimesMode_Firmware.restype = ctypes.c_int

glaDevSys.glaDataCollection.argtypes = [
    ctypes.c_int, ctypes.POINTER(ctypes.c_double),
    ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
glaDevSys.glaDataCollection.restype = ctypes.c_int

glaDevSys.glaGetPixelCnts.argtypes = [ctypes.c_int]
glaDevSys.glaGetPixelCnts.restype = ctypes.c_int

glaDevSys.glaGetWavelength.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double)]
glaDevSys.glaGetWavelength.restype = ctypes.c_int

glaDevSys.glaGetTemperature.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_float)]
glaDevSys.glaGetTemperature.restype = ctypes.c_int


# ======================== 光谱仪控制类 ========================
class Spectrometer:
    def __init__(self):
        self.fd = 0
        self.connected = False
        self.pixel_cnts = 0
        self.wavelengths = None
        self.spectrum_data = None
        self.running = False
        self._thread = None
        self._data_queue = queue.Queue(maxsize=2)

    def scan_devices(self):
        logger.info("扫描设备...")
        dev_lst = (DEVLST * 16)()
        dev_cnts = ctypes.c_uint(0)
        rslt = glaDevSys.USB_GetDeviceList(dev_lst, dev_cnts)
        if rslt != NOERROR:
            logger.error(f"扫描设备失败, 错误码: {rslt}")
            return []
        devices = []
        for i in range(dev_cnts.value):
            desc = dev_lst[i].description.decode('utf-8', errors='ignore').strip('\x00')
            sn = dev_lst[i].serialnumber.decode('utf-8', errors='ignore').strip('\x00')
            devices.append({'index': i, 'desc': desc, 'sn': sn})
            logger.info(f"  发现设备 [{i}]: {desc}  SN:{sn}")
        logger.info(f"扫描完成, 共 {len(devices)} 个设备")
        return devices

    def connect(self, dev_num=0, ver=6):
        if self.connected:
            return None
        logger.info(f"连接设备: devNum={dev_num}, ver={ver}")
        rslt = glaDevSys.glaDevOpen(self.fd, IFS_USB_FT, dev_num, ver, 0)
        if rslt != NOERROR:
            logger.error(f"打开设备失败, 错误码: {rslt}")
            return f"打开设备失败 (错误码 {rslt})"
        self.connected = True
        self.pixel_cnts = glaDevSys.glaGetPixelCnts(self.fd)
        if self.pixel_cnts <= 0:
            logger.error("获取像素数失败")
            self.disconnect()
            return "获取像素数失败"
        wave_buf = (ctypes.c_double * MAX_PIXELS)()
        rslt = glaDevSys.glaGetWavelength(self.fd, wave_buf)
        if rslt == NOERROR:
            self.wavelengths = np.ctypeslib.as_array(wave_buf)[:self.pixel_cnts].copy()
        else:
            self.wavelengths = np.arange(self.pixel_cnts, dtype=float)
            logger.warning(f"获取波长失败 (错误码 {rslt}), 使用像素索引代替")
        self.spectrum_data = np.zeros(self.pixel_cnts)
        logger.info(f"设备已连接, 像素数: {self.pixel_cnts}")
        return None

    def disconnect(self):
        if self.running:
            self.stop_continuous()
        if self.connected:
            logger.info("断开设备")
            glaDevSys.glaDevClose(self.fd, IFS_USB_FT)
            self.connected = False

    def set_exposure(self, ms):
        logger.info(f"设置积分时间: {ms} ms")
        rslt = glaDevSys.glaSetExposure(self.fd, ctypes.c_double(ms), 0)
        if rslt != NOERROR:
            logger.error(f"设置积分时间失败, 错误码: {rslt}")
        return rslt == NOERROR

    def get_exposure(self):
        v = ctypes.c_double(0)
        rslt = glaDevSys.glaGetExposure(self.fd, ctypes.byref(v))
        return v.value if rslt == NOERROR else None

    def set_avg_times(self, n):
        logger.info(f"设置平均次数: {n}")
        rslt = glaDevSys.glaSetCollectTimesMode_Firmware(self.fd, n)
        if rslt != NOERROR:
            logger.error(f"设置平均次数失败, 错误码: {rslt}")
        return rslt == NOERROR

    def get_avg_times(self):
        v = ctypes.c_uint(0)
        rslt = glaDevSys.glaGetCollectTimesMode_Firmware(self.fd, ctypes.byref(v))
        return v.value if rslt == NOERROR else None

    def get_temperature(self):
        v = ctypes.c_float(0)
        rslt = glaDevSys.glaGetTemperature(self.fd, ctypes.byref(v))
        return v.value if rslt == NOERROR else None

    def acquire_once(self, mode=MSM_IRRAD, avg=1):
        if not self.connected:
            return None
        buf = (ctypes.c_double * MAX_PIXELS)()
        rslt = glaDevSys.glaDataCollection(self.fd, buf, mode, avg, 1, 0, 0)
        if rslt != NOERROR:
            logger.error(f"数据采集失败, 错误码: {rslt}")
            return None
        data = np.ctypeslib.as_array(buf)[:self.pixel_cnts].copy()
        self.spectrum_data = data
        return data

    def start_continuous(self, mode=MSM_IRRAD, avg=1):
        """启动连续采集线程，数据推入队列，不做任何 sleep"""
        if self.running:
            return
        self.running = True
        # 清空旧数据
        while not self._data_queue.empty():
            try:
                self._data_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("开始连续采集")

        def _loop():
            while self.running:
                t0 = time.perf_counter()
                data = self.acquire_once(mode, avg)
                elapsed = time.perf_counter() - t0
                if data is not None:
                    # 丢弃旧帧，只保留最新
                    if self._data_queue.full():
                        try:
                            self._data_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self._data_queue.put_nowait((data, elapsed))
                elif not self.running:
                    break

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop_continuous(self):
        if self.running:
            self.running = False
            logger.info("停止连续采集")
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=3)

    def get_latest_data(self):
        """非阻塞取最新一帧数据，返回 (data, elapsed_sec) 或 None"""
        latest = None
        while not self._data_queue.empty():
            try:
                latest = self._data_queue.get_nowait()
            except queue.Empty:
                break
        return latest

    def get_spectrum(self):
        if self.spectrum_data is not None:
            return self.spectrum_data.copy()
        return None


# ======================== GUI 主窗口 ========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("高利通光纤光谱仪测试程序")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self.configure(bg=COLORS['bg'])

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "spectrometer.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._closing = False
        self.spec = Spectrometer()
        self._cont = False
        self._peak_hold_data = None
        self._acq_count = 0
        self._last_plot_time = 0.0
        self._PLOT_INTERVAL = 0.05  # 最小刷新间隔 50ms (20 FPS)
        self._poll_id = None
        self._var_fill = tk.BooleanVar(value=True)
        self._last_fill_state = True
        self._fill_frame_count = 0
        self._stab_running = False
        self._stab_thread = None
        self._stab_stop_event = threading.Event()
        self._stab_results = []
        self._bgd_data = None

        self._setup_style()
        self._build_ui()
        logger.info("程序已启动")
        self.log("程序已启动, 等待操作...")

    # ---------- 样式 ----------
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure('.', background=COLORS['bg'], foreground=COLORS['text'],
                        font=('Microsoft YaHei UI', 9))
        style.configure('TFrame', background=COLORS['bg'])
        style.configure('Card.TFrame', background=COLORS['panel'], relief='flat')
        style.configure('Header.TFrame', background=COLORS['header_bg'])
        style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'])
        style.configure('Card.TLabel', background=COLORS['panel'])
        style.configure('Sec.TLabel', foreground=COLORS['text_sec'], background=COLORS['panel'])
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 10, 'bold'),
                        background=COLORS['panel'], foreground=COLORS['text_bright'])
        style.configure('Status.TLabel', background=COLORS['bg'],
                        foreground=COLORS['text_sec'], font=('Microsoft YaHei UI', 8))
        style.configure('Header.TLabel', background=COLORS['header_bg'])

        style.configure('TLabelframe', background=COLORS['panel'],
                        foreground=COLORS['text'], relief='flat', borderwidth=1,
                        bordercolor=COLORS['border'])
        style.configure('TLabelframe.Label', background=COLORS['panel'],
                        foreground=COLORS['accent'], font=('Microsoft YaHei UI', 9, 'bold'))

        style.configure('TButton', padding=(12, 5), font=('Microsoft YaHei UI', 9),
                        background=COLORS['btn_face'], foreground=COLORS['text'],
                        borderwidth=0, relief='flat')
        style.map('TButton',
                  background=[('active', COLORS['border']), ('!active', COLORS['btn_face'])],
                  foreground=[('active', COLORS['text_bright']), ('!active', COLORS['text'])])

        style.configure('Accent.TButton', padding=(12, 6),
                        font=('Microsoft YaHei UI', 9, 'bold'),
                        background=COLORS['accent'], foreground=COLORS['text_bright'],
                        borderwidth=0)
        style.map('Accent.TButton',
                  background=[('active', COLORS['accent_hover']),
                              ('!active', COLORS['accent'])],
                  foreground=[('active', 'white'), ('!active', 'white')])

        style.configure('Danger.TButton', padding=(12, 6),
                        font=('Microsoft YaHei UI', 9, 'bold'),
                        background=COLORS['danger'], foreground=COLORS['text_bright'],
                        borderwidth=0)
        style.map('Danger.TButton',
                  background=[('active', '#c62828'), ('!active', COLORS['danger'])],
                  foreground=[('active', 'white'), ('!active', 'white')])

        style.configure('TEntry', padding=4, font=('Consolas', 10),
                        fieldbackground=COLORS['log_bg'], foreground=COLORS['text_bright'],
                        bordercolor=COLORS['border'], insertcolor=COLORS['text_bright'])
        style.configure('TRadiobutton', background=COLORS['panel'],
                        font=('Microsoft YaHei UI', 9), foreground=COLORS['text'])
        style.configure('TCheckbutton', background=COLORS['panel'],
                        font=('Microsoft YaHei UI', 9), foreground=COLORS['text'])
        style.configure('TCombobox', fieldbackground=COLORS['log_bg'],
                        foreground=COLORS['text_bright'], bordercolor=COLORS['border'])

    # ---------- UI 构建 ----------
    def _build_ui(self):
        header = tk.Frame(self, bg=COLORS['header_bg'], height=56)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        header_inner = tk.Frame(header, bg=COLORS['header_bg'])
        header_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        ttk.Label(header_inner, text="高利通光纤光谱仪",
                  font=('Microsoft YaHei UI', 15, 'bold'),
                  foreground=COLORS['accent'],
                  background=COLORS['header_bg']).pack(side=tk.LEFT)
        ttk.Label(header_inner, text="Spectrometer Test Utility",
                  font=('Segoe UI', 9),
                  foreground=COLORS['text_sec'],
                  background=COLORS['header_bg']).pack(side=tk.LEFT, padx=(12, 0))
        sep = tk.Frame(self, bg=COLORS['accent'], height=2)
        sep.pack(fill=tk.X)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        left_outer = tk.Frame(body, bg=COLORS['bg'], width=280)
        left_outer.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left_outer.pack_propagate(False)

        left_canvas = tk.Canvas(left_outer, bg=COLORS['bg'], highlightthickness=0)
        left_scrollbar = ttk.Scrollbar(left_outer, orient=tk.VERTICAL, command=left_canvas.yview)
        self._left_frame = ttk.Frame(left_canvas)

        self._left_frame.bind("<Configure>",
                              lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        self._canvas_win = left_canvas.create_window((0, 0), window=self._left_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        def _on_canvas_resize(event):
            left_canvas.itemconfig(self._canvas_win, width=event.width)
        left_canvas.bind("<Configure>", _on_canvas_resize)

        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._build_left_panels()

        right = ttk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_chart(right)
        self._build_log_panel(right)

    def _card_frame(self, parent, title):
        f = ttk.LabelFrame(parent, text=f"  {title}  ", padding=10)
        f.pack(fill=tk.X, padx=4, pady=(0, 6))
        return f

    def _build_left_panels(self):
        p = self._left_frame

        # ---- 设备连接 ----
        grp = self._card_frame(p, "设备连接")

        self._dev_combo = ttk.Combobox(grp, state='readonly', font=('Consolas', 9))
        self._dev_combo.pack(fill=tk.X, pady=(0, 6))

        btn_row = ttk.Frame(grp)
        btn_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_row, text="扫描设备", command=self._on_scan).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        self._btn_conn = ttk.Button(btn_row, text="连接", style='Accent.TButton',
                                    command=self._on_connect)
        self._btn_conn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
        self._btn_disconn = ttk.Button(btn_row, text="断开", command=self._on_disconnect,
                                       state=tk.DISABLED, style='Danger.TButton')
        self._btn_disconn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        self._lbl_conn_status = ttk.Label(grp, text="  未连接", style='Sec.TLabel',
                                          font=('Microsoft YaHei UI', 9))
        self._lbl_conn_status.pack(fill=tk.X)

        # ---- 设备信息 ----
        grp = self._card_frame(p, "设备信息")
        info_grid = ttk.Frame(grp)
        info_grid.pack(fill=tk.X)
        ttk.Label(info_grid, text="像素数", style='Sec.TLabel').grid(
            row=0, column=0, sticky=tk.W, pady=1)
        self._lbl_pixels = ttk.Label(info_grid, text="--", style='Card.TLabel',
                                     font=('Consolas', 10, 'bold'))
        self._lbl_pixels.grid(row=0, column=1, sticky=tk.E, pady=1)
        ttk.Label(info_grid, text="温度", style='Sec.TLabel').grid(
            row=1, column=0, sticky=tk.W, pady=1)
        self._lbl_temp = ttk.Label(info_grid, text="--", style='Card.TLabel',
                                   font=('Consolas', 10, 'bold'))
        self._lbl_temp.grid(row=1, column=1, sticky=tk.E, pady=1)
        info_grid.columnconfigure(1, weight=1)

        # ---- 参数设置 ----
        grp = self._card_frame(p, "参数设置")

        ttk.Label(grp, text="积分时间 (ms)", style='Sec.TLabel').pack(anchor=tk.W)
        f_exp = ttk.Frame(grp)
        f_exp.pack(fill=tk.X, pady=(2, 6))
        self._var_expo = tk.StringVar(value="1.0")
        ttk.Entry(f_exp, textvariable=self._var_expo, width=10,
                  font=('Consolas', 10)).pack(side=tk.LEFT)
        ttk.Button(f_exp, text="应用", width=6,
                   command=self._on_set_expo).pack(side=tk.LEFT, padx=(6, 0))
        self._lbl_expo_cur = ttk.Label(f_exp, text="", style='Sec.TLabel')
        self._lbl_expo_cur.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(grp, text="平均次数", style='Sec.TLabel').pack(anchor=tk.W)
        f_avg = ttk.Frame(grp)
        f_avg.pack(fill=tk.X, pady=(2, 6))
        self._var_avg = tk.StringVar(value="1")
        ttk.Entry(f_avg, textvariable=self._var_avg, width=10,
                  font=('Consolas', 10)).pack(side=tk.LEFT)
        ttk.Button(f_avg, text="应用", width=6,
                   command=self._on_set_avg).pack(side=tk.LEFT, padx=(6, 0))
        self._lbl_avg_cur = ttk.Label(f_avg, text="", style='Sec.TLabel')
        self._lbl_avg_cur.pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(grp, text="测量模式", style='Sec.TLabel').pack(anchor=tk.W, pady=(0, 2))
        self._var_mode = tk.IntVar(value=MSM_IRRAD)
        mode_frame = ttk.Frame(grp)
        mode_frame.pack(fill=tk.X, pady=(0, 4))
        for i, (val, txt) in enumerate(MODE_NAMES.items()):
            ttk.Radiobutton(mode_frame, text=txt, variable=self._var_mode,
                            value=val).grid(row=i // 2, column=i % 2, sticky=tk.W, pady=1)

        self._var_bgd = tk.BooleanVar(value=False)
        bgd_row = ttk.Frame(grp)
        bgd_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Checkbutton(bgd_row, text="背景扣除", variable=self._var_bgd).pack(side=tk.LEFT)
        self._btn_bgd = ttk.Button(bgd_row, text="采集背景", width=8,
                                    command=self._on_acquire_bgd)
        self._btn_bgd.pack(side=tk.RIGHT)
        self._lbl_bgd_status = ttk.Label(grp, text="背景: 未采集", style='Sec.TLabel')
        self._lbl_bgd_status.pack(anchor=tk.W)

        # ---- 采集控制 ----
        grp = self._card_frame(p, "采集控制")

        self._btn_acq = ttk.Button(grp, text="单次采集", style='Accent.TButton',
                                   command=self._on_acquire)
        self._btn_acq.pack(fill=tk.X, pady=(0, 4))

        f_cont = ttk.Frame(grp)
        f_cont.pack(fill=tk.X, pady=(0, 4))
        self._btn_cont = ttk.Button(f_cont, text="连续采集", command=self._on_toggle_cont)
        self._btn_cont.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        self._btn_stop = ttk.Button(f_cont, text="停止", command=self._on_stop_cont,
                                    state=tk.DISABLED)
        self._btn_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        self._lbl_acq_count = ttk.Label(grp, text="采集次数: 0", style='Sec.TLabel')
        self._lbl_acq_count.pack(anchor=tk.W)

        # ---- 稳定性测试 ----
        grp = self._card_frame(p, "稳定性测试")

        f_stab1 = ttk.Frame(grp)
        f_stab1.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(f_stab1, text="测试次数", style='Sec.TLabel').pack(side=tk.LEFT)
        self._var_stab_count = tk.StringVar(value="100")
        ttk.Entry(f_stab1, textvariable=self._var_stab_count, width=8,
                  font=('Consolas', 10)).pack(side=tk.RIGHT)

        f_stab2 = ttk.Frame(grp)
        f_stab2.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(f_stab2, text="间隔 (ms)", style='Sec.TLabel').pack(side=tk.LEFT)
        self._var_stab_interval = tk.StringVar(value="1000")
        ttk.Entry(f_stab2, textvariable=self._var_stab_interval, width=8,
                  font=('Consolas', 10)).pack(side=tk.RIGHT)

        f_stab3 = ttk.Frame(grp)
        f_stab3.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(f_stab3, text="亮度RSD阈值 (%)", style='Sec.TLabel').pack(side=tk.LEFT)
        self._var_stab_rsd = tk.StringVar(value="2.0")
        ttk.Entry(f_stab3, textvariable=self._var_stab_rsd, width=8,
                  font=('Consolas', 10)).pack(side=tk.RIGHT)

        f_stab4 = ttk.Frame(grp)
        f_stab4.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(f_stab4, text="波长Std阈值 (nm)", style='Sec.TLabel').pack(side=tk.LEFT)
        self._var_stab_wlstd = tk.StringVar(value="0.1")
        ttk.Entry(f_stab4, textvariable=self._var_stab_wlstd, width=8,
                  font=('Consolas', 10)).pack(side=tk.RIGHT)

        f_stab_btn = ttk.Frame(grp)
        f_stab_btn.pack(fill=tk.X, pady=(0, 4))
        self._btn_stab_start = ttk.Button(f_stab_btn, text="开始测试",
                                           style='Accent.TButton',
                                           command=self._on_stab_start)
        self._btn_stab_start.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        self._btn_stab_stop = ttk.Button(f_stab_btn, text="停止",
                                          style='Danger.TButton',
                                          command=self._on_stab_stop,
                                          state=tk.DISABLED)
        self._btn_stab_stop.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        self._lbl_stab_progress = ttk.Label(grp, text="进度: --/--",
                                             style='Sec.TLabel')
        self._lbl_stab_progress.pack(anchor=tk.W)

        # ---- 显示选项 ----
        grp = self._card_frame(p, "显示选项")

        self._var_peak = tk.BooleanVar(value=False)
        ttk.Checkbutton(grp, text="峰值保持", variable=self._var_peak).pack(anchor=tk.W)

        f_peak = ttk.Frame(grp)
        f_peak.pack(fill=tk.X, pady=4)
        ttk.Button(f_peak, text="清除峰值", command=self._on_clear_peak).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        self._var_grid = tk.BooleanVar(value=True)
        ttk.Checkbutton(grp, text="显示网格", variable=self._var_grid,
                        command=self._on_grid_toggle).pack(anchor=tk.W)

        ttk.Checkbutton(grp, text="显示填充", variable=self._var_fill).pack(anchor=tk.W)

        # ---- 数据保存 ----
        grp = self._card_frame(p, "数据")
        ttk.Button(grp, text="保存光谱 (CSV)", command=self._on_save).pack(fill=tk.X)

    def _build_chart(self, parent):
        chart_frame = tk.Frame(parent, bg=COLORS['panel'])
        chart_frame.pack(fill=tk.BOTH, expand=True)

        self._fig = Figure(figsize=(8, 5), dpi=100, facecolor=COLORS['chart_bg'])
        self._ax = self._fig.add_subplot(111)
        self._ax.set_facecolor(COLORS['chart_bg'])
        self._ax.set_xlabel('Wavelength (nm)', fontsize=10, color=COLORS['text_sec'])
        self._ax.set_ylabel('Intensity', fontsize=10, color=COLORS['text_sec'])
        self._ax.set_title('Spectrum', fontsize=12, fontweight='bold',
                           color=COLORS['text_bright'], pad=10)
        self._ax.tick_params(colors=COLORS['text_sec'], labelsize=9)
        for spine in self._ax.spines.values():
            spine.set_color(COLORS['border'])
        self._ax.grid(True, alpha=0.3, color=COLORS['chart_grid'])

        self._line, = self._ax.plot([], [], color=COLORS['accent'], linewidth=1.8,
                                    label='Spectrum', alpha=0.95)
        self._fill = self._ax.fill_between([], [], [], color=COLORS['accent'], alpha=0.15)
        self._peak_line, = self._ax.plot([], [], color=COLORS['danger'],
                                         linewidth=1.2, linestyle='--',
                                         alpha=0.8, label='Peak Hold')
        self._ax.legend(loc='upper right', fontsize=8, framealpha=0.9,
                        facecolor=COLORS['panel'], edgecolor=COLORS['border'],
                        labelcolor=COLORS['text'])
        self._fig.subplots_adjust(left=0.1, right=0.95, top=0.92, bottom=0.12)

        self._canvas = FigureCanvasTkAgg(self._fig, master=chart_frame)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._lbl_plot_info = ttk.Label(chart_frame, text="波长范围: --  |  峰值: --",
                                        style='Status.TLabel',
                                        background=COLORS['panel'])
        self._lbl_plot_info.pack(anchor=tk.W, padx=6, pady=(0, 4))

    def _build_log_panel(self, parent):
        log_frame = ttk.LabelFrame(parent, text="  运行日志  ", padding=4)
        log_frame.pack(fill=tk.X, pady=(4, 0))

        self._log_text = tk.Text(log_frame, height=6, wrap=tk.WORD,
                                 font=('Consolas', 9), bg=COLORS['log_bg'],
                                 fg=COLORS['text'],
                                 insertbackground=COLORS['text_bright'], relief='flat',
                                 selectbackground=COLORS['accent'],
                                 selectforeground=COLORS['text_bright'],
                                 padx=6, pady=4,
                                 borderwidth=0, highlightthickness=0)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL,
                                   command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(fill=tk.BOTH, expand=True)
        self._log_text.config(state=tk.DISABLED)

        self._log_text.tag_configure('INFO', foreground='#4fc3f7')
        self._log_text.tag_configure('WARN', foreground=COLORS['warning'])
        self._log_text.tag_configure('ERROR', foreground=COLORS['danger'])
        self._log_text.tag_configure('OK', foreground=COLORS['success'])
        self._log_text.tag_configure('TIME', foreground='#546e7a')

    def log(self, msg, level='INFO'):
        ts = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
        tag = level.upper() if level.upper() in ('INFO', 'WARN', 'ERROR', 'OK') else 'INFO'

        self._log_text.config(state=tk.NORMAL)
        self._log_text.insert(tk.END, f"[{ts}] ", 'TIME')
        self._log_text.insert(tk.END, f"{msg}\n", tag)
        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

        log_func = getattr(logger, tag.lower() if tag != 'OK' else 'info', logger.info)
        log_func(msg)

    # ---------- 设备操作 ----------
    def _on_scan(self):
        self.log("正在扫描设备...")
        devices = self.spec.scan_devices()
        self._dev_combo['values'] = []
        if not devices:
            self.log("未发现设备, 请检查 USB 连接和驱动", 'WARN')
            return
        items = [f"[{d['index']}] {d['desc']}  SN:{d['sn']}" for d in devices]
        self._dev_combo['values'] = items
        self._dev_combo.current(0)
        self.log(f"发现 {len(devices)} 个设备", 'OK')

    def _on_connect(self):
        sel = self._dev_combo.get()
        if not sel:
            self.log("请先扫描并选择设备", 'WARN')
            return
        dev_num = int(sel.split(']')[0].strip('['))
        self.log(f"正在连接设备 [{dev_num}]...")
        err = self.spec.connect(dev_num)
        if err:
            self.log(f"连接失败: {err}", 'ERROR')
            return
        self._btn_conn.config(state=tk.DISABLED)
        self._btn_disconn.config(state=tk.NORMAL)
        self._dev_combo.config(state=tk.DISABLED)
        self._lbl_conn_status.config(text="  已连接", foreground=COLORS['success'],
                                     background=COLORS['panel'])
        self._lbl_pixels.config(text=str(self.spec.pixel_cnts))

        expo = self.spec.get_exposure()
        avg = self.spec.get_avg_times()
        temp = self.spec.get_temperature()
        if expo is not None:
            self._var_expo.set(f"{expo:.2f}")
            self._lbl_expo_cur.config(text=f"({expo:.2f})")
        if avg is not None:
            self._var_avg.set(str(avg))
            self._lbl_avg_cur.config(text=f"({avg})")
        if temp is not None:
            self._lbl_temp.config(text=f"{temp:.1f} °C")

        self.log(f"设备已连接, 像素数: {self.spec.pixel_cnts}", 'OK')

    def _on_disconnect(self):
        if self._cont:
            self._on_stop_cont()
        if self._stab_running:
            self._stab_stop_event.set()
        self.spec.disconnect()
        self._btn_conn.config(state=tk.NORMAL)
        self._btn_disconn.config(state=tk.DISABLED)
        self._dev_combo.config(state='readonly')
        self._lbl_conn_status.config(text="  未连接", foreground=COLORS['text_sec'],
                                     background=COLORS['panel'])
        self._lbl_pixels.config(text="--")
        self._lbl_temp.config(text="--")
        self._lbl_expo_cur.config(text="")
        self._lbl_avg_cur.config(text="")
        self._bgd_data = None
        self._var_bgd.set(False)
        self._lbl_bgd_status.config(text="背景: 未采集", foreground=COLORS['text_sec'])
        self.log("设备已断开", 'OK')

    # ---------- 参数设置 ----------
    def _on_set_expo(self):
        if not self.spec.connected:
            self.log("请先连接设备", 'WARN')
            return
        try:
            ms = float(self._var_expo.get())
        except ValueError:
            self.log("积分时间格式错误", 'WARN')
            return
        if self.spec.set_exposure(ms):
            self._lbl_expo_cur.config(text=f"({ms:.2f})")
            self.log(f"积分时间已设置: {ms:.2f} ms", 'OK')
        else:
            self.log("设置积分时间失败", 'ERROR')

    def _on_set_avg(self):
        if not self.spec.connected:
            self.log("请先连接设备", 'WARN')
            return
        try:
            n = int(self._var_avg.get())
            if n < 1:
                n = 1
        except ValueError:
            self.log("平均次数格式错误", 'WARN')
            return
        if self.spec.set_avg_times(n):
            self._lbl_avg_cur.config(text=f"({n})")
            self.log(f"平均次数已设置: {n}", 'OK')
        else:
            self.log("设置平均次数失败", 'ERROR')

    # ---------- 背景扣除 ----------
    def _on_acquire_bgd(self):
        if not self.spec.connected:
            self.log("请先连接设备", 'WARN')
            return
        self._btn_bgd.config(state=tk.DISABLED)
        self.log("正在采集背景...")

        def _do():
            data = self.spec.acquire_once(
                mode=self._var_mode.get(),
                avg=int(self._var_avg.get()))
            self.after(0, lambda: _bgd_done(data))

        def _bgd_done(data):
            self._btn_bgd.config(state=tk.NORMAL)
            if data is None:
                self.log("背景采集失败", 'ERROR')
                return
            self._bgd_data = data.copy()
            self._var_bgd.set(True)
            self._lbl_bgd_status.config(
                text=f"背景: 已采集 (范围 [{data.min():.1f}, {data.max():.1f}])",
                foreground=COLORS['success'])
            self.log(f"背景已采集, 范围 [{data.min():.1f}, {data.max():.1f}]", 'OK')

        threading.Thread(target=_do, daemon=True).start()

    def _apply_bgd(self, data):
        """如果背景扣除开启且有背景数据，返回扣除后的数据，否则返回原数据"""
        if self._var_bgd.get() and self._bgd_data is not None:
            return data - self._bgd_data
        return data

    # ---------- 采集 ----------
    def _on_acquire(self):
        if not self.spec.connected:
            self.log("请先连接设备", 'WARN')
            return
        self._btn_acq.config(state=tk.DISABLED)
        self.log("单次采集中...")

        def _do():
            t0 = time.perf_counter()
            data = self.spec.acquire_once(
                mode=self._var_mode.get(),
                avg=int(self._var_avg.get()))
            elapsed = time.perf_counter() - t0
            self.after(0, lambda: self._acq_done(data, elapsed))

        threading.Thread(target=_do, daemon=True).start()

    def _acq_done(self, data, elapsed):
        self._btn_acq.config(state=tk.NORMAL)
        if data is None:
            self.log("数据采集失败", 'ERROR')
            return
        data = self._apply_bgd(data)
        self._acq_count += 1
        self._lbl_acq_count.config(text=f"采集次数: {self._acq_count}")
        self._update_plot(data)
        peak_idx = np.argmax(data)
        self.log(f"采集完成 ({elapsed*1000:.0f}ms) | "
                 f"范围: [{data.min():.1f}, {data.max():.1f}] | "
                 f"峰值: {self.spec.wavelengths[peak_idx]:.1f} nm", 'OK')

    def _on_toggle_cont(self):
        if not self.spec.connected:
            self.log("请先连接设备", 'WARN')
            return
        self._cont = True
        self._btn_cont.config(state=tk.DISABLED)
        self._btn_stop.config(state=tk.NORMAL)
        self._btn_acq.config(state=tk.DISABLED)
        self._last_plot_time = 0.0
        self.log("开始连续采集")

        self.spec.start_continuous(
            mode=self._var_mode.get(),
            avg=int(self._var_avg.get()))

        # 启动 GUI 定时轮询, 30ms 一次
        self._poll_data()

    def _poll_data(self):
        """定时从队列取最新数据并更新图表, 由 GUI 主线程控制刷新节奏"""
        if not self._cont or self._closing:
            return

        t_poll = time.perf_counter()
        result = self.spec.get_latest_data()
        if result is not None:
            data, elapsed = result
            data = self._apply_bgd(data)
            self._acq_count += 1
            self._lbl_acq_count.config(text=f"采集次数: {self._acq_count}")

            now = time.perf_counter()
            if now - self._last_plot_time >= self._PLOT_INTERVAL:
                self._last_plot_time = now
                self._update_plot(data)

        poll_ms = (time.perf_counter() - t_poll) * 1000
        if poll_ms > 100:
            logger.warning(f"_poll_data 耗时: {poll_ms:.0f}ms (数据采集: {elapsed*1000:.0f}ms)")

        # 30ms 后再次轮询 (~33 FPS 轮询上限, 实际刷新受渲染速度限制)
        self._poll_id = self.after(30, self._poll_data)

    def _on_stop_cont(self):
        self._cont = False
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        self.spec.stop_continuous()
        self._btn_cont.config(state=tk.NORMAL)
        self._btn_stop.config(state=tk.DISABLED)
        self._btn_acq.config(state=tk.NORMAL)
        self.log("已停止连续采集", 'OK')

    # ---------- 稳定性测试 ----------
    def _on_stab_start(self):
        if not self.spec.connected:
            self.log("请先连接设备", 'WARN')
            return
        if self._cont:
            self.log("请先停止连续采集", 'WARN')
            return
        try:
            count = int(self._var_stab_count.get())
            interval_ms = int(self._var_stab_interval.get())
            rsd_thresh = float(self._var_stab_rsd.get())
            wlstd_thresh = float(self._var_stab_wlstd.get())
            if count < 1 or interval_ms < 0 or rsd_thresh <= 0 or wlstd_thresh <= 0:
                raise ValueError
        except ValueError:
            self.log("稳定性测试参数格式错误", 'WARN')
            return

        self._stab_running = True
        self._stab_stop_event.clear()
        self._stab_results = []
        self._stab_rsd_thresh = rsd_thresh
        self._stab_wlstd_thresh = wlstd_thresh
        self._btn_stab_start.config(state=tk.DISABLED)
        self._btn_stab_stop.config(state=tk.NORMAL)
        self._btn_acq.config(state=tk.DISABLED)
        self._btn_cont.config(state=tk.DISABLED)
        self._lbl_stab_progress.config(text=f"进度: 0/{count}")
        self.log(f"稳定性测试开始: {count} 次, 间隔 {interval_ms}ms")

        self._stab_thread = threading.Thread(
            target=self._stab_loop,
            args=(count, interval_ms),
            daemon=True)
        self._stab_thread.start()

    def _on_stab_stop(self):
        self._stab_stop_event.set()
        self.log("稳定性测试停止中...")

    def _stab_loop(self, count, interval_ms):
        mode = self._var_mode.get()
        avg = int(self._var_avg.get())
        interval_sec = interval_ms / 1000.0

        for i in range(count):
            if self._stab_stop_event.is_set():
                self.after(0, lambda: self._stab_finished(interrupted=True))
                return

            t0 = time.perf_counter()
            data = self.spec.acquire_once(mode=mode, avg=avg)
            elapsed = time.perf_counter() - t0

            if data is None:
                self.after(0, lambda i=i: self.log(
                    f"稳定性测试第 {i+1} 次采集失败", 'ERROR'))
                time.sleep(interval_sec)
                continue

            # 背景扣除 (在线程中读取 GUI 变量, 但 BooleanVar.get 和 bgd_data 是只读的)
            if self._var_bgd.get() and self._bgd_data is not None:
                data = data - self._bgd_data

            peak_idx = int(np.argmax(data))
            cx, cy, Y = _compute_chromaticity(data, self.spec.wavelengths)
            dom_wl, purity = _compute_dominant_wavelength(cx, cy)
            result = {
                'iteration': i + 1,
                'dominant_wavelength': dom_wl if dom_wl is not None else float('nan'),
                'peak_intensity': float(data[peak_idx]),
                'luminance': Y,
                'cx': cx,
                'cy': cy,
                'purity': purity,
                'spectrum': data.copy(),
                'timestamp': time.time(),
            }
            self._stab_results.append(result)

            self.after(0, lambda c=count: self._stab_update_progress(c))

            sleep_end = time.perf_counter() + interval_sec
            while time.perf_counter() < sleep_end:
                if self._stab_stop_event.is_set():
                    self.after(0, lambda: self._stab_finished(interrupted=True))
                    return
                time.sleep(min(0.1, sleep_end - time.perf_counter()))

        self.after(0, lambda: self._stab_finished(interrupted=False))

    def _stab_update_progress(self, count):
        done = len(self._stab_results)
        self._lbl_stab_progress.config(text=f"进度: {done}/{count}")

    def _stab_finished(self, interrupted=False):
        self._stab_running = False
        self._btn_stab_start.config(state=tk.NORMAL)
        self._btn_stab_stop.config(state=tk.DISABLED)
        self._btn_acq.config(state=tk.NORMAL)
        self._btn_cont.config(state=tk.NORMAL)

        done = len(self._stab_results)
        if interrupted:
            self.log(f"稳定性测试已中断 ({done} 次完成)", 'WARN')
        else:
            self.log(f"稳定性测试完成 ({done} 次)", 'OK')

        if done > 0:
            self._stab_analyze()

    def _stab_analyze(self):
        results = self._stab_results
        n = len(results)

        dwl = np.array([r['dominant_wavelength'] for r in results])
        pi = np.array([r['peak_intensity'] for r in results])
        lum = np.array([r['luminance'] for r in results])
        cx = np.array([r['cx'] for r in results])
        cy = np.array([r['cy'] for r in results])

        def stats(arr):
            m = float(np.nanmean(arr))
            s = float(np.nanstd(arr, ddof=1)) if n > 1 else 0.0
            rsd = (s / m * 100.0) if m != 0 else 0.0
            mn, mx = float(np.nanmin(arr)), float(np.nanmax(arr))
            return {
                'mean': m, 'std': s, 'rsd': rsd,
                'min': mn, 'max': mx,
                'range': mx - mn,
            }

        analysis = {
            'count': n,
            'dominant_wavelength': stats(dwl),
            'peak_intensity': stats(pi),
            'luminance': stats(lum),
            'cx': stats(cx),
            'cy': stats(cy),
        }

        lum_rsd = analysis['luminance']['rsd']
        wl_std = analysis['dominant_wavelength']['std']
        rsd_thresh = self._stab_rsd_thresh
        wlstd_thresh = self._stab_wlstd_thresh
        analysis['pass'] = (lum_rsd < rsd_thresh) and (wl_std < wlstd_thresh)
        analysis['rsd_thresh'] = rsd_thresh
        analysis['wlstd_thresh'] = wlstd_thresh
        analysis['criteria'] = (f"亮度 RSD < {rsd_thresh}% (实际 {lum_rsd:.2f}%) "
                                f"且 主波长 Std < {wlstd_thresh}nm (实际 {wl_std:.4f}nm)")

        self.log(f"稳定性分析: {'通过' if analysis['pass'] else '未通过'}")
        self.log(f"  主波长: {analysis['dominant_wavelength']['mean']:.2f} nm, "
                 f"Std={wl_std:.4f}")
        self.log(f"  亮度: RSD={lum_rsd:.2f}%")
        self.log(f"  色坐标: x={np.mean(cx):.4f}, y={np.mean(cy):.4f}")

        self._stab_show_results(analysis)

    def _stab_show_results(self, analysis):
        popup = tk.Toplevel(self)
        popup.title("稳定性测试结果")
        popup.geometry("900x1000")
        popup.configure(bg=COLORS['bg'])
        popup.transient(self)
        popup.grab_set()

        # ---- 统计表格 ----
        table_frame = tk.Frame(popup, bg=COLORS['panel'], padx=10, pady=10)
        table_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        pf_text = "通过 PASS" if analysis['pass'] else "未通过 FAIL"
        pf_color = COLORS['success'] if analysis['pass'] else COLORS['danger']
        tk.Label(table_frame, text=pf_text,
                 font=('Microsoft YaHei UI', 14, 'bold'),
                 fg=pf_color, bg=COLORS['panel']).pack(anchor=tk.W, pady=(0, 8))

        tk.Label(table_frame, text=analysis['criteria'],
                 font=('Microsoft YaHei UI', 9), fg=COLORS['text_sec'],
                 bg=COLORS['panel']).pack(anchor=tk.W, pady=(0, 8))

        # Grid-based stats table in its own frame
        grid_frame = tk.Frame(table_frame, bg=COLORS['panel'])
        grid_frame.pack(fill=tk.X)

        headers = ['指标', '均值', '标准差', 'RSD (%)', '最小值', '最大值', '极差']
        for c, h in enumerate(headers):
            tk.Label(grid_frame, text=h, font=('Microsoft YaHei UI', 9, 'bold'),
                     fg=COLORS['accent'], bg=COLORS['panel'],
                     padx=6, pady=2).grid(row=0, column=c, sticky=tk.W)

        rows = [
            ('主波长 (nm)', analysis['dominant_wavelength']),
            ('峰值强度', analysis['peak_intensity']),
            ('亮度', analysis['luminance']),
            ('色坐标 x', analysis['cx']),
            ('色坐标 y', analysis['cy']),
        ]
        for r, (name, s) in enumerate(rows, start=1):
            vals = [name, f"{s['mean']:.4f}", f"{s['std']:.4f}",
                    f"{s['rsd']:.4f}", f"{s['min']:.4f}", f"{s['max']:.4f}",
                    f"{s['range']:.4f}"]
            for c, v in enumerate(vals):
                tk.Label(grid_frame, text=v, font=('Consolas', 9),
                         fg=COLORS['text'], bg=COLORS['panel'],
                         padx=6, pady=1).grid(row=r, column=c, sticky=tk.W)

        # ---- 图表 (3x2) ----
        fig = Figure(figsize=(8.5, 8.5), dpi=100, facecolor=COLORS['chart_bg'])
        results = self._stab_results
        iterations = [r['iteration'] for r in results]
        dwl_vals = [r['dominant_wavelength'] for r in results]
        cx_vals = [r['cx'] for r in results]
        cy_vals = [r['cy'] for r in results]

        dwl_mean = analysis['dominant_wavelength']['mean']
        wlstd_t = analysis.get('wlstd_thresh', 0.1)
        rsd_t = analysis.get('rsd_thresh', 2.0)
        wave = self.spec.wavelengths
        n_spectra = len(results)
        cmap = matplotlib.colormaps.get_cmap('coolwarm')

        def _style_ax(ax):
            ax.set_facecolor(COLORS['chart_bg'])
            ax.tick_params(colors=COLORS['text_sec'], labelsize=8)
            for spine in ax.spines.values():
                spine.set_color(COLORS['border'])
            ax.grid(True, alpha=0.3, color=COLORS['chart_grid'])

        # 1) 主波长稳定性
        ax1 = fig.add_subplot(321)
        _style_ax(ax1)
        ax1.plot(iterations, dwl_vals, color=COLORS['accent'],
                 linewidth=1.2, marker='.', markersize=2)
        ax1.axhline(y=dwl_mean, color=COLORS['warning'],
                    linestyle='--', linewidth=0.8, alpha=0.7)
        ax1.axhline(y=dwl_mean + wlstd_t, color=COLORS['danger'],
                    linestyle=':', linewidth=0.8, alpha=0.5)
        ax1.axhline(y=dwl_mean - wlstd_t, color=COLORS['danger'],
                    linestyle=':', linewidth=0.8, alpha=0.5,
                    label=f'±{wlstd_t} nm')
        ax1.set_xlabel('Iteration', fontsize=8, color=COLORS['text_sec'])
        ax1.set_ylabel('Dominant WL (nm)', fontsize=8, color=COLORS['text_sec'])
        ax1.set_title('Dominant Wavelength', fontsize=10, color=COLORS['text_bright'])
        ax1.legend(fontsize=7, facecolor=COLORS['panel'],
                   edgecolor=COLORS['border'], labelcolor=COLORS['text'])

        # 2) 亮度稳定性
        lum_vals = [r['luminance'] for r in results]
        lum_mean = analysis['luminance']['mean']
        ax2 = fig.add_subplot(322)
        _style_ax(ax2)
        ax2.plot(iterations, lum_vals, color=COLORS['danger'],
                 linewidth=1.2, marker='.', markersize=2)
        ax2.axhline(y=lum_mean, color=COLORS['warning'],
                    linestyle='--', linewidth=0.8, alpha=0.7)
        ax2.axhline(y=lum_mean * (1 + rsd_t / 100), color=COLORS['danger'],
                    linestyle=':', linewidth=0.8, alpha=0.5)
        ax2.axhline(y=lum_mean * (1 - rsd_t / 100), color=COLORS['danger'],
                    linestyle=':', linewidth=0.8, alpha=0.5,
                    label=f'±{rsd_t}% RSD')
        ax2.set_xlabel('Iteration', fontsize=8, color=COLORS['text_sec'])
        ax2.set_ylabel('Luminance', fontsize=8, color=COLORS['text_sec'])
        ax2.set_title('Luminance', fontsize=10, color=COLORS['text_bright'])
        ax2.legend(fontsize=7, facecolor=COLORS['panel'],
                   edgecolor=COLORS['border'], labelcolor=COLORS['text'])

        # 3) 色坐标 x 稳定性
        cx_mean = analysis['cx']['mean']
        ax3 = fig.add_subplot(323)
        _style_ax(ax3)
        ax3.plot(iterations, cx_vals, color=COLORS['accent'],
                 linewidth=1.2, marker='.', markersize=2)
        ax3.axhline(y=cx_mean, color=COLORS['warning'],
                    linestyle='--', linewidth=0.8, alpha=0.7)
        ax3.set_xlabel('Iteration', fontsize=8, color=COLORS['text_sec'])
        ax3.set_ylabel('CIE x', fontsize=8, color=COLORS['text_sec'])
        ax3.set_title('Chromaticity x', fontsize=10, color=COLORS['text_bright'])

        # 4) 色坐标 y 稳定性
        cy_mean = analysis['cy']['mean']
        ax4 = fig.add_subplot(324)
        _style_ax(ax4)
        ax4.plot(iterations, cy_vals, color=COLORS['success'],
                 linewidth=1.2, marker='.', markersize=2)
        ax4.axhline(y=cy_mean, color=COLORS['warning'],
                    linestyle='--', linewidth=0.8, alpha=0.7)
        ax4.set_xlabel('Iteration', fontsize=8, color=COLORS['text_sec'])
        ax4.set_ylabel('CIE y', fontsize=8, color=COLORS['text_sec'])
        ax4.set_title('Chromaticity y', fontsize=10, color=COLORS['text_bright'])

        # 5) 光谱叠加
        ax5 = fig.add_subplot(325)
        _style_ax(ax5)
        for idx, r in enumerate(results):
            color = cmap(idx / max(n_spectra - 1, 1))
            ax5.plot(wave, r['spectrum'], color=color, linewidth=0.6, alpha=0.6)
        ax5.set_xlabel('Wavelength (nm)', fontsize=8, color=COLORS['text_sec'])
        ax5.set_ylabel('Intensity', fontsize=8, color=COLORS['text_sec'])
        ax5.set_title(f'Spectra Overlay ({n_spectra} spectra)',
                       fontsize=10, color=COLORS['text_bright'])
        sm = matplotlib.cm.ScalarMappable(cmap=cmap,
              norm=matplotlib.colors.Normalize(vmin=1, vmax=n_spectra))
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax5, pad=0.02, aspect=30)
        cbar.set_label('Iteration', fontsize=8, color=COLORS['text_sec'])
        cbar.ax.tick_params(colors=COLORS['text_sec'], labelsize=7)

        # 6) 色品图 (CIE 1931)
        ax6 = fig.add_subplot(326)
        _style_ax(ax6)
        ax6.plot(_SLOCUS_X, _SLOCUS_Y, color=COLORS['text_sec'],
                 linewidth=0.8, alpha=0.6)
        ax6.plot([_SLOCUS_X[-1], _SLOCUS_X[0]], [_SLOCUS_Y[-1], _SLOCUS_Y[0]],
                 color=COLORS['text_sec'], linewidth=0.8, alpha=0.4,
                 linestyle='--')
        scatter = ax6.scatter(cx_vals, cy_vals, c=iterations, cmap=cmap,
                              s=15, zorder=5, edgecolors='none')
        ax6.plot(_D65_X, _D65_Y, '+', color=COLORS['warning'],
                 markersize=8, markeredgewidth=1.5, label='D65')
        ax6.plot([_D65_X, np.mean(cx_vals)], [_D65_Y, np.mean(cy_vals)],
                 color=COLORS['accent'], linewidth=1.0, alpha=0.5)
        ax6.set_xlabel('CIE x', fontsize=8, color=COLORS['text_sec'])
        ax6.set_ylabel('CIE y', fontsize=8, color=COLORS['text_sec'])
        ax6.set_title('Chromaticity (CIE 1931)', fontsize=10,
                       color=COLORS['text_bright'])
        ax6.set_xlim(0.0, 0.8)
        ax6.set_ylim(0.0, 0.9)
        ax6.legend(fontsize=7, facecolor=COLORS['panel'],
                   edgecolor=COLORS['border'], labelcolor=COLORS['text'])
        cbar2 = fig.colorbar(scatter, ax=ax6, pad=0.02, aspect=30)
        cbar2.set_label('Iteration', fontsize=8, color=COLORS['text_sec'])
        cbar2.ax.tick_params(colors=COLORS['text_sec'], labelsize=7)

        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        canvas.draw()

        # ---- 按钮 ----
        btn_frame = tk.Frame(popup, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        ttk.Button(btn_frame, text="保存报告 (CSV + PNG)",
                   style='Accent.TButton',
                   command=lambda: self._stab_save_report(analysis, fig)
                   ).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="关闭",
                   command=popup.destroy).pack(side=tk.RIGHT)

    def _stab_save_report(self, analysis, fig):
        path = filedialog.askdirectory(title="选择报告保存目录")
        if not path:
            return

        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(path, f"stability_{ts}.csv")
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Iteration', 'Dominant_WL_nm', 'Peak_Intensity',
                             'Luminance', 'CIE_x', 'CIE_y', 'Timestamp'])
            for r in self._stab_results:
                writer.writerow([r['iteration'],
                                 f"{r['dominant_wavelength']:.4f}",
                                 f"{r['peak_intensity']:.4f}",
                                 f"{r['luminance']:.4f}",
                                 f"{r['cx']:.6f}",
                                 f"{r['cy']:.6f}",
                                 f"{r['timestamp']:.3f}"])
            writer.writerow([])
            writer.writerow(['--- Summary ---'])
            for key, label in [('dominant_wavelength', 'Dominant_WL_nm'),
                               ('peak_intensity', 'Peak_Intensity'),
                               ('luminance', 'Luminance'),
                               ('cx', 'CIE_x'),
                               ('cy', 'CIE_y')]:
                s = analysis[key]
                writer.writerow([label, f"Mean={s['mean']:.4f}",
                                 f"Std={s['std']:.4f}", f"RSD%={s['rsd']:.4f}",
                                 f"Min={s['min']:.4f}", f"Max={s['max']:.4f}",
                                 f"Range={s['range']:.4f}"])
            writer.writerow([])
            writer.writerow(['--- Thresholds ---'])
            writer.writerow(['RSD_Threshold_%', f"{analysis.get('rsd_thresh', 2.0)}"])
            writer.writerow(['WL_Std_Threshold_nm', f"{analysis.get('wlstd_thresh', 0.1)}"])
            writer.writerow([])
            writer.writerow(['Result', 'PASS' if analysis['pass'] else 'FAIL'])
            writer.writerow(['Criteria', analysis['criteria']])

        png_path = os.path.join(path, f"stability_{ts}.png")
        fig.savefig(png_path, dpi=150, facecolor=fig.get_facecolor(),
                    bbox_inches='tight')

        self.log(f"稳定性报告已保存: {csv_path}", 'OK')
        self.log(f"稳定性图表已保存: {png_path}", 'OK')

    # ---------- 图表 ----------
    def _update_plot(self, data):
        wave = self.spec.wavelengths
        if wave is None:
            return

        self._line.set_data(wave, data)
        self._ax.set_xlim(wave[0], wave[-1])

        # Update gradient fill (throttled in continuous mode for performance)
        self._fill_frame_count += 1
        fill_now = self._var_fill.get()
        update_fill = (fill_now != self._last_fill_state) or \
                      (fill_now and self._fill_frame_count % 10 == 0)
        if update_fill:
            self._last_fill_state = fill_now
            self._fill.remove()
            if fill_now:
                self._fill = self._ax.fill_between(wave, data, 0,
                                                   color=COLORS['accent'], alpha=0.15)
            else:
                self._fill = self._ax.fill_between([], [], [], color=COLORS['accent'], alpha=0)

        if self._var_peak.get():
            if self._peak_hold_data is None:
                self._peak_hold_data = data.copy()
            else:
                self._peak_hold_data = np.maximum(self._peak_hold_data, data)
            self._peak_line.set_data(wave, self._peak_hold_data)

        all_data = [data]
        if self._var_peak.get() and self._peak_hold_data is not None:
            all_data.append(self._peak_hold_data)
        y_max = max(d.max() for d in all_data) * 1.1
        y_min = min(d.min() for d in all_data)
        self._ax.set_ylim(y_min - abs(y_min) * 0.05, max(y_max, 1))

        peak_idx = np.argmax(data)
        peak_wl = wave[peak_idx]
        peak_val = data[peak_idx]
        self._lbl_plot_info.config(
            text=f"波长范围: {wave[0]:.1f} - {wave[-1]:.1f} nm  |  "
                 f"峰值: {peak_wl:.1f} nm ({peak_val:.1f})  |  "
                 f"数据点: {len(data)}")

        t_draw = time.perf_counter()
        self._canvas.draw_idle()

        draw_time = (time.perf_counter() - t_draw) * 1000
        if draw_time > 50:
            logger.debug(f"draw_idle 耗时: {draw_time:.0f}ms")

    def _on_clear_peak(self):
        self._peak_hold_data = None
        self._peak_line.set_data([], [])
        self._canvas.draw_idle()
        self.log("已清除峰值保持数据")

    def _on_grid_toggle(self):
        self._ax.grid(self._var_grid.get(), alpha=0.4, color=COLORS['chart_grid'])
        self._canvas.draw_idle()

    # ---------- 保存 ----------
    def _on_save(self):
        data = self.spec.get_spectrum()
        if data is None:
            self.log("没有可保存的数据, 请先采集", 'WARN')
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")])
        if not path:
            return
        wave = self.spec.wavelengths
        with open(path, 'w', encoding='utf-8') as f:
            f.write("Pixel,Wavelength(nm),Intensity\n")
            for i in range(len(data)):
                w = wave[i] if wave is not None else i
                f.write(f"{i},{w:.4f},{data[i]:.4f}\n")
        self.log(f"数据已保存: {path} ({len(data)} 点)", 'OK')

    # ---------- 关闭 ----------
    def _on_close(self):
        if self._closing:
            return
        self._closing = True
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        if self._stab_running:
            self._stab_stop_event.set()
        self.log("正在关闭程序...")
        self.spec.stop_continuous()
        self.spec.disconnect()
        logger.info("程序已退出")
        self.destroy()


# ======================== 启动 ========================
if __name__ == '__main__':
    app = App()
    app.mainloop()
