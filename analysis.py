'''PyNMR, J.Maxwell 2020
'''
import numpy as np
from scipy import optimize
from lmfit import Model
from app.deuteron_fits import DFits


def standard_baseline(event, base_event):
    basesweep = base_event.basesweep
    return basesweep, event.phase - basesweep

def poly_fit_sub(event, wings, poly):
    """
    wings: 4 numbers determining fit wings from 0 to 1
    poly: polynomial function
    """
    pi = [0.01, 0.8, 0.01, 0.001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001]

    sweep = event.basesub
    freqs = event.freq_list
    bounds = [x * len(sweep) for x in wings]
    data = [z for x, z in enumerate(zip(freqs, sweep)) if (bounds[0] < x < bounds[1] or bounds[2] < x < bounds[3])]
    X = np.array([x for x, y in data])
    Y = np.array([y for x, y in data])
    pf, pcov = optimize.curve_fit(poly, X, Y, p0=pi)
    try:
        pstd = np.sqrt(np.diag(pcov))
    except:
        pass
    fit = poly(freqs, *pf)
    sub = sweep - fit

    area = sub.sum()

    residuals = Y - poly(X, *pf)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((Y - np.mean(Y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot else 0
    return fit, sub

def poly2(x, *p):
    return p[0] + p[1] * x + p[2] * np.power(x, 2)

def poly3(x, *p):
    return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3)

def poly4(x, *p):
    return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3) + p[4] * np.power(x, 4)



def sum_range(event, wings):
    """Perform standard polyfit baseline subtraction

    Arguments:
        event: Event instance with sweeps to subtract
        wings: 2 numbers between 0 and 1 giving range to sum between

    Returns:
        polyfit used, baseline subtracted sweep
    """

    sweep = event.fitsub
    bounds = [x * len(sweep) for x in wings]
    data = [(x, y) if bounds[0] < x < bounds[1] else (x, 0) for x, y in enumerate(sweep)]
    Y = np.array([y for x, y in data])
    area = Y.sum()
    pol = area * event.cc
    return Y, area, pol


def d_fit(settings, event, params):
    """Perform Dueteron fit and calculate polarization

    Arguments:
        event: Event instance with sweeps to fit

    Returns:
        fit, resulting r asymmetry (instead of area) and polarization
    """

    sweep = event.fitsub
    freqs = event.freq_list
    print("Starting D fit")

    #labels = [e.text() for e in self.param_label]
    #values = [float(e.text()) for e in self.param_edit]
    #self.params = dict(zip(labels, values))

    params = settings['analysis']['d_fit_params']

    res = DFits(freqs, sweep, params)

    r = res.result.params['r'].value
    fit = res.result.best_fit
    if res.result.success:  # if successful, set these params for next time
        params = res.result.params.valuesdict()

    pol = (r * r - 1) / (r * r + r + 1)
    area = fit.sum()
    cc = pol / area
    text = '\n'
    i = 0
    for name, param in res.result.params.items():
        i += 1
        print(f"{name} {param.value:.3f}\t")
        text = text + f"{name}: {param.value:.3f}\t"
        if i == 4:
            text = text + "\n"
    #self.message.setText(f"Polarization: {pol * 100:.4f}%, Area:  {area:.4f}, CC:  {cc:.4f}\n {text}")
    print("Finished D fit")
    return fit, r, pol
