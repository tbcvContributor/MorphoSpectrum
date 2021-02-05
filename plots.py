import time

import matplotlib.pyplot as plt
import matplotlib.ticker as tick
from parameters import *


def format_freq(x, pos, f):
    n = int(round(x))
    if 0 <= n < f.size:
        if PLOT_UNITS:
            return str(f[n].astype(int)) + " Hz"
        else:
            return str(f[n].astype(int))
    else:
        return ""


def format_time(x, pos, t):
    n = int(round(x))
    if 0 <= n < t.size:
        if PLOT_UNITS:
            return str(round(t[n], 3)) + " s"
        else:
            return time.strftime('%M:%S', time.gmtime(round(t[n], 3)))
            # return str(round(t[n], 3))
    else:
        return ""


def plot_cqt(a, t, f=FREQUENCIES):
    fig = plt.figure(figsize=(2*320/DPI, 2*240/DPI), dpi=DPI)
    ax = fig.add_subplot(111)

    plt.imshow(a, cmap='hot', aspect='auto', vmin=V_MIN, vmax=V_MAX, origin='lower')

    # Freq axis
    ax.yaxis.set_major_formatter(tick.FuncFormatter(lambda x, pos: format_freq(x, pos, f)))

    # Time axis
    ax.xaxis.set_major_formatter(tick.FuncFormatter(lambda x, pos: format_time(x, pos, t)))

    if FULL_SCREEN:
        manager = plt.get_current_fig_manager()
        manager.resize(*manager.window.maxsize())

    plt.xlabel('Time (mm:ss)')
    plt.ylabel('Frequency (Hz)')

    plt.show()


def plot_morphology(a_dilation, t, f=FREQUENCIES):
    # a_dilation_log = 20 * np.log10(a_dilation + EPS)
    fig = plt.figure(figsize=(2*320/DPI, 2*240/DPI), dpi=DPI)
    ax = fig.add_subplot(111)

    plt.imshow(a_dilation, cmap='Greys', aspect='auto', origin='lower', vmin=V_MIN_MOR, vmax=V_MAX_MOR)

    # Freq axis
    ax.yaxis.set_major_formatter(tick.FuncFormatter(lambda x, pos: format_freq(x, pos, f)))

    # Time axis
    ax.xaxis.set_major_formatter(tick.FuncFormatter(lambda x, pos: format_time(x, pos, t)))

    if FULL_SCREEN:
        manager = plt.get_current_fig_manager()
        manager.resize(*manager.window.maxsize())

    plt.xlabel('Time (mm:ss)')
    plt.ylabel('Frequency (Hz)')


def plot_both(a, a_dilation, t, f=FREQUENCIES):
    # a_log = 20 * np.log10(a + EPS)
    # a_dilation_log = 20 * np.log10(a_dilation + EPS)

    fig = plt.figure(figsize=(2*320/DPI, 2*240/DPI), dpi=DPI)
    ax_1 = fig.add_subplot(211)
    ax_2 = fig.add_subplot(212, sharex=ax_1, sharey=ax_1)

    ax_1.imshow(a, cmap='hot', aspect='auto', vmin=V_MIN, vmax=V_MAX, origin='lower')
    ax_2.imshow(a_dilation, cmap='Greys', aspect='auto', origin='lower', vmin=V_MIN_MOR, vmax=V_MAX_MOR)

    # Freq axis
    ax_1.yaxis.set_major_formatter(tick.FuncFormatter(lambda x, pos: format_freq(x, pos, f)))

    # Time axis
    ax_1.xaxis.set_major_formatter(tick.FuncFormatter(lambda x, pos: format_time(x, pos, t)))

    if FULL_SCREEN:
        manager = plt.get_current_fig_manager()
        manager.resize(*manager.window.maxsize())

    # Labels
    ax_1.set_xlabel('Time (mm:ss)')
    ax_1.set_ylabel('Frequency (Hz)')
    ax_2.set_xlabel('Time (mm:ss)')
    ax_2.set_ylabel('Frequency (Hz)')
