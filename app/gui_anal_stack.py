import numpy as np
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox, QHBoxLayout, QVBoxLayout, QGridLayout, QLineEdit, QSpacerItem, \
    QSizePolicy, QComboBox, QPushButton, QProgressBar, QStackedWidget, QDoubleSpinBox
from lmfit import Model
from scipy import optimize
import pyqtgraph as pg
from app.deuteron_fits import DFits

class StandardBase(QWidget):
    '''Layout and method for standard baseline subtract based on selected baseline from baseline tab.  Base type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Baseline Selected from Baseline Tab"
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 0))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 0))

    def result(self, event):
        '''Perform standard baseline subtraction,

        Arguments:
            event: Event instance with sweeps to subtract

        Returns:
            baseline sweep, baseline subtracted sweep
        '''
        basesweep = event.baseline
        self.message.setText(f"Baseline from {event.base_time.strftime('%D %H:%M:%S')} UTC")
        return basesweep, event.scan.phase - basesweep


class PolyFitBase(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits.  Base type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Polynomial Fit to Wings"
        self.wings = self.parent.event.config.settings['analysis']['wings']

        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.poly_label = QLabel("Polynomial order:")
        self.grid.addWidget(self.poly_label, 0, 0)
        self.poly_combo = QComboBox()
        self.grid.addWidget(self.poly_combo, 0, 1)
        self.poly_opts = ['2nd Order', '3rd Order', '4th Order']
        self.poly_combo.addItems(self.poly_opts)
        self.poly_combo.currentIndexChanged.connect(self.change_poly)
        self.change_poly(1)
        self.poly_combo.setCurrentIndex(1)

        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):  # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)

            self.grid2.addWidget(self.bounds_sb[i], 0, i + 1)
        self.change_wings()

        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 20))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 20))

    def change_poly(self, i):
        '''Choose polynomial order method'''
        if i == 0:
            self.poly = self.poly2
            self.pi = [0.01, 0.8, 0.01]
        elif i == 1:
            self.poly = self.poly3
            self.pi = [0.01, 0.8, 0.01, 0.001]
        elif i == 2:
            self.poly = self.poly4
            self.pi = [0.01, 0.8, 0.01, 0.001, 0.00001]
        self.parent.run_analysis()

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]
        self.wings = sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max()

        bounds = [w * (max - min) + min for w in self.wings]
        self.parent.base_region1.setRegion(bounds[:2])
        self.parent.base_region2.setRegion(bounds[2:])
        self.parent.run_analysis()

    def result(self, event):
        '''Perform standard polyfit baseline subtraction

        Arguments:
            event: Event instance with sweeps to subtract

        Returns:
            polyfit used, baseline subtracted sweep
        '''
        sweep = event.scan.phase
        freqs = event.scan.freq_list
        bounds = [x * len(sweep) for x in self.wings]
        data = [z for x, z in enumerate(zip(freqs, sweep)) if (bounds[0] < x < bounds[1] or bounds[2] < x < bounds[3])]
        X = np.array([x for x, y in data])
        Y = np.array([y for x, y in data])
        pf, pcov = optimize.curve_fit(self.poly, X, Y, p0=self.pi)
        pstd = np.sqrt(np.diag(pcov))
        fit = self.poly(freqs, *pf)
        sub = sweep - fit

        residuals = Y - self.poly(X, *pf)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((Y - np.mean(Y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)

        text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        self.message.setText(f"Fit coefficients: \t \t \t R-squared: {r_squared:.2f}\n" + "\n".join(text_list))
        return fit, sub

    def poly2(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2)

    def poly3(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3)

    def poly4(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3) + p[4] * np.power(x, 4)


class CircuitBase(QWidget):
    '''Layout for circuit model fit to the background wings, including methods to produce fits.  Base type.

    NOT IMPLEMENTED. Fits not quite converging, slow.

    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Circuit Model Fit"
        self.wings = self.parent.event.config.settings['analysis']['wings']

        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.grid = QGridLayout()

        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):  # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)

            self.grid2.addWidget(self.bounds_sb[i], 0, i + 1)
        self.change_wings()

        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 0))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 0))

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]
        self.wings = sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max()

        bounds = [w * (max - min) + min for w in self.wings]
        self.parent.base_region1.setRegion(bounds[:2])
        self.parent.base_region2.setRegion(bounds[2:])
        self.parent.run_analysis()

    def result(self, event):
        '''Perform circuit model fit baseline subtraction

        Arguments:
            event: Event instance with sweeps to subtract

        Returns:
            fit used, baseline subtracted sweep
        '''
        sweep = event.scan.phase
        bounds = [x * len(sweep) for x in self.wings]
        data = [(x, y) for x, y in enumerate(sweep) if (bounds[0] < x < bounds[1] or bounds[2] < x < bounds[3])]
        f = np.array([x for x, y in data])
        Y = np.array([y for x, y in data])

        mod = Model(self.real_curve)
        params = mod.make_params()
        params.add('cap', value=18.62, min=1.0, max=60.0)
        params.add('phase', value=-140, min=-180, max=180)
        params.add('coil_l', value=30, min=1.0, max=120)
        params.add('offset', value=0.19, min=-10, max=10)
        params.add('scale', value=5, min=4.99, max=5.001)

        result = mod.fit(Y, params, f=f)
        # print(result.best_values)
        fit = self.real_curve(range(len(event.scan.phase)), **result.best_values)
        sub = sweep - fit
        # text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        # self.message.setText("Fit coefficients:\n"+"\n".join(text_list))
        return fit, sub

    def full_curve(self, f, cap, phase, coil_l):
        '''
        Returns full complex voltage out of Q-curve.

        Arguments:
            f: frequency f in MHz
            cap: tuning capacitance in pF
            phase: phase in degrees
            coil_l: coil inductance in nanoHenries
        '''
        w = 2 * np.pi * f * 1e6  # angular frequency
        c = cap * 1e-12  # Cap in F
        u = 0.6  # Input RF voltage
        r_cc = 681  # Constant current resistor
        i = u / r_cc  # Constant current
        c_stray = 0.0000001e-12  # Stray capacitance
        l_coil = coil_l * 1e-9  # Inductance of coil
        r_coil = 0.3  # Resistance of coil
        r_amp = 50  # Impedance of detector
        r = 10  # Damping resistor

        zc = 1 / np.complex(0, w * c)  # impedance of cap
        zc_stray = 1 / np.complex(0, w * c_stray)  # impedance of stray cap
        zl_pure = np.complex(r_coil, w * l_coil)  # impedance of coil only
        zl = zl_pure * zc_stray / (zl_pure + zc_stray)  # impedance of coil and stray capacitance
        z_leg = r + zc + zl  # impedance of the damping resistor, cap, coil
        z_tot = r_amp / (1 + r_amp / z_leg)  # total impedance of coil, trans line and detector (voltage divider)

        phi = phase * np.pi / 180  # phase bet. constant current and output voltage
        v_out = i * z_tot * np.exp(np.complex(0, phi))
        return (v_out)

    def mag_curve(self, f, cap, phase, coil_l, offset=0, scale=1):
        ''' Passed list of frequency points, calls full_curve at each point to get magnitude of Q-curve'''
        v_out = [np.absolute(self.full_curve(k, cap, phase, coil_l)) for k in f]
        return ([vout * scale + offset for vout in v_out])

    def real_curve(self, f, cap, phase, coil_l, offset=0, scale=1):
        ''' Passed list of frequency points, calls full_curve at each point to get real portion of Q-curve'''
        v_out = [-np.real(self.full_curve(k, cap, phase, coil_l)) for k in f]
        return ([vout * scale + offset for vout in v_out])


class NoBase(QWidget):
    '''Layout for no fit to the background wings, including methods to produce fits. Base type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "No Baseline Subtraction"
        self.poly_label = QLabel("No baseline subtraction")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.base_region1.setBrush(pg.mkBrush(0, 0, 180, 0))
        self.parent.base_region2.setBrush(pg.mkBrush(0, 0, 180, 0))

    def result(self, event):
        '''Only performs sum
        '''
        sweep = event.scan.phase
        fitcurve = np.zeros(len(sweep))
        sub = sweep - fitcurve
        area = sub.sum()
        return fitcurve, sub


class PolyFitSub(QWidget):
    '''Layout for polynomial fit to the background wings, including methods to produce fits. Sub type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Polynomial Fit to Wings"
        self.wings = self.parent.event.config.settings['analysis']['wings']

        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.poly_label = QLabel("Polynomial order:")
        self.grid.addWidget(self.poly_label, 0, 0)
        self.poly_combo = QComboBox()
        self.grid.addWidget(self.poly_combo, 0, 1)
        self.poly_opts = ['2nd Order', '3rd Order', '4th Order', '6th Order', '8th Order']
        self.poly_combo.addItems(self.poly_opts)
        self.poly_combo.currentIndexChanged.connect(self.change_poly)
        self.change_poly(1)
        self.poly_combo.setCurrentIndex(1)

        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):  # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)

            self.grid2.addWidget(self.bounds_sb[i], 0, i + 1)
        self.change_wings()

        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def change_poly(self, i):
        '''Choose polynomial order method'''
        if i == 0:
            self.poly = self.poly2
            self.pi = [0.01, 0.8, 0.01]
        elif i == 1:
            self.poly = self.poly3
            self.pi = [0.01, 0.8, 0.01, 0.001]
        elif i == 2:
            self.poly = self.poly4
            self.pi = [0.01, 0.8, 0.01, 0.001, 0.00001]
        elif i == 3:
            self.poly = self.poly6
            self.pi = [0.01, 0.8, 0.01, 0.001, 0.00001, 0.00001, 0.00001]
        elif i == 4:
            self.poly = self.poly8
            self.pi = [0.01, 0.8, 0.01, 0.001, 0.00001, 0.00001, 0.00001, 0.00001, 0.00001]
        self.parent.run_analysis()

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.sub_region1.setBrush(pg.mkBrush(0, 0, 180, 20))
        self.parent.sub_region2.setBrush(pg.mkBrush(0, 0, 180, 20))

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]
        self.wings = sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max()

        bounds = [w * (max - min) + min for w in self.wings]
        self.parent.sub_region1.setRegion(bounds[:2])
        self.parent.sub_region2.setRegion(bounds[2:])
        self.parent.run_analysis()

    def result(self, event):
        '''Perform standard polyfit baseline subtraction

        Arguments:
            event: Event instance with sweeps to subtract

        Returns:
            polyfit used, baseline subtracted sweep
        '''

        sweep = event.basesub
        freqs = event.scan.freq_list
        bounds = [x * len(sweep) for x in self.wings]
        data = [z for x, z in enumerate(zip(freqs, sweep)) if (bounds[0] < x < bounds[1] or bounds[2] < x < bounds[3])]
        X = np.array([x for x, y in data])
        Y = np.array([y for x, y in data])
        pf, pcov = optimize.curve_fit(self.poly, X, Y, p0=self.pi)
        try:
            pstd = np.sqrt(np.diag(pcov))
        except:
            pass
        fit = self.poly(freqs, *pf)
        sub = sweep - fit

        area = sub.sum()

        residuals = Y - self.poly(X, *pf)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((Y - np.mean(Y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)

        text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        self.message.setText(f"Fit coefficients: \t \t \t R-squared: {r_squared:.2f}\n" + "\n".join(text_list))
        return fit, sub

    def poly2(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2)

    def poly3(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3)

    def poly4(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3) + p[4] * np.power(x, 4)

    def poly6(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3) + p[4] * np.power(x, 4) + p[
            5] * np.power(x, 5) + p[6] * np.power(x, 6)

    def poly8(self, x, *p):
        return p[0] + p[1] * x + p[2] * np.power(x, 2) + p[3] * np.power(x, 3) + p[4] * np.power(x, 4) + p[
            5] * np.power(x, 5) + p[6] * np.power(x, 6) + p[7] * np.power(x, 7) + p[8] * np.power(x, 8)


class NoFitSub(QWidget):
    '''Layout for no fit to the background wings, including methods. Sub type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "No Fit Subtraction"
        self.poly_label = QLabel("No fit subtraction")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.sub_region1.setBrush(pg.mkBrush(0, 0, 180, 20))
        self.parent.sub_region2.setBrush(pg.mkBrush(0, 0, 180, 20))

    def result(self, event):
        '''Only performs sum
        '''
        sweep = event.basesub
        fitcurve = np.zeros(len(sweep))
        sub = sweep - fitcurve
        area = sub.sum()
        return fitcurve, sub


class SumAllRes(QWidget):
    '''Layout and methods for integrtation over full signal range.  Results type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Integrate Full Range"
        self.poly_label = QLabel("Sum Full Range")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 0, 180, 0))

    def result(self, event):
        '''Only performs sum
        '''
        sweep = event.fitsub
        fitcurve = np.zeros(len(sweep))
        sub = sweep - fitcurve
        area = sub.sum()
        pol = area * event.cc
        self.message.setText(f"Area: {area}")
        data = [0 for x in event.config.freq_list]
        return data, area, pol


class SumRangeRes(QWidget):
    '''Layout and methods for integration within a given range.  Results type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.name = "Integrate within Range"
        self.range = self.parent.event.config.settings['analysis']['sum_range']

        self.space = QVBoxLayout()
        self.setLayout(self.space)

        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Integration bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.range):  # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)

            self.grid2.addWidget(self.bounds_sb[i], 0, i + 1)
        self.change_wings()
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 180, 0, 20))

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]
        self.wings = sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max()

        bounds = [w * (max - min) + min for w in self.wings]
        self.parent.res_region.setRegion(bounds)
        self.parent.run_analysis()

    def result(self, event):
        '''Perform standard polyfit baseline subtraction

        Arguments:
            event: Event instance with sweeps to subtract

        Returns:
            polyfit used, baseline subtracted sweep
        '''

        sweep = event.fitsub
        bounds = [x * len(sweep) for x in self.wings]
        data = [(x, y) if bounds[0] < x < bounds[1] else (x, 0) for x, y in enumerate(sweep)]
        Y = np.array([y for x, y in data])
        area = Y.sum()
        pol = area * event.cc
        self.message.setText(f"Area: {area}")
        return Y, area, pol


class PeakHeightRes(QWidget):
    '''Layout and methods for peak height results method. Area attribute is filled with peak height instead.  Results type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Peak Height"
        self.poly_label = QLabel(
            "When using this method, the peak height replaces\nthe area throughout the application.")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 0, 180, 0))

    def result(self, event):
        '''Find peak height
        '''
        sweep = event.fitsub
        max = np.max(sweep)
        min = np.min(sweep)
        area = max if abs(max) > abs(min) else min  # Using peak height represent area
        data = [area for x in event.config.freq_list]

        pol = area * event.cc
        self.message.setText(f"Peak height: {area}")
        return data, area, pol


class FitPeakRes(QWidget):
    '''Layout and methods for fitting Gaussian  on subtracted signal. Results type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Fit Gaussian and Integrate"
        self.wings = self.parent.event.config.settings['analysis']['sum_range']
        self.poly_label = QLabel("Fit Peak")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):  # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)
            self.grid2.addWidget(self.bounds_sb[i], 0, i + 1)
        self.change_wings()

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 180, 0, 20))

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]
        self.wings = sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max()

        bounds = [w * (max - min) + min for w in self.wings]
        self.parent.res_region.setRegion(bounds)
        self.parent.run_analysis()

    def result(self, event):
        '''Perform Gaussian fit and sum.

        Arguments:
            event: Event instance with sweeps to fit

        Returns:
            area and polarization from sum under gaussian
        '''

        self.pi = [-0.1, self.parent.config.channel['cent_freq'], self.parent.config.channel['mod_freq'] * 1E-3 / 10]

        sweep = event.fitsub
        freqs = event.scan.freq_list
        bounds = [x * len(sweep) for x in self.wings]
        data = [z for x, z in enumerate(zip(freqs, sweep)) if bounds[0] < x < bounds[1]]
        X = np.array([x for x, y in data])
        Y = np.array([y for x, y in data])
        pf, pcov = optimize.curve_fit(self.gaussian, X, Y, p0=self.pi)
        pstd = np.sqrt(np.diag(pcov))
        fit = self.gaussian(freqs, *pf)

        residuals = Y - self.gaussian(X, *pf)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((Y - np.mean(Y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)

        area = fit.sum()
        pol = area * event.cc
        text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        self.message.setText(
            f"Fit coefficients: \t \t \t R-squared: {r_squared:.2f}\n" + "\n".join(text_list) + "\n" + f"Area: {area}")
        return fit, area, pol

    def gaussian(self, x, *p):
        return p[0] * np.exp(-np.power((x - p[1]), 2) / (2 * np.power(p[2], 2)))

    def gaussian(self, x, *p):
        return p[0] * np.exp(-np.power((x - p[1]), 2) / (2 * np.power(p[2], 2)))

    def lorentzian(self, x, *p):
        return p[1] / np.pi / ((x - p[0]) ** 2 + p[1] ** 2)


class FitPeakRes2(QWidget):
    '''Layout and methods for fitting sum of Gaussians  on subtracted signal. Results type.
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.name = "Fit 2 Gaussians and Integrate"
        self.wings = self.parent.event.config.settings['analysis']['sum_range']
        self.poly_label = QLabel("Fit Peak")
        self.space.addWidget(self.poly_label)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

        self.grid2 = QGridLayout()
        self.space.addLayout(self.grid2)
        self.bounds_label = QLabel("Fit bounds (0 to 1):")
        self.grid2.addWidget(self.bounds_label, 0, 0)
        self.bounds_sb = []
        for i, n in enumerate(self.wings):  # setup spin boxes for each bound
            self.bounds_sb.append(QDoubleSpinBox())
            self.bounds_sb[i].setValue(n)
            self.bounds_sb[i].setSingleStep(0.01)
            self.bounds_sb[i].valueChanged.connect(self.change_wings)
            self.grid2.addWidget(self.bounds_sb[i], 0, i + 1)
        self.change_wings()

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 180, 0, 20))

    def change_wings(self):
        '''Choose fit frequency bounds'''
        wings = [n.value() for n in self.bounds_sb]
        self.wings = sorted(wings)
        for w, b in zip(self.wings, self.bounds_sb):
            b.setValue(w)
        min = self.parent.parent.event.scan.freq_list.min()
        max = self.parent.parent.event.scan.freq_list.max()

        bounds = [w * (max - min) + min for w in self.wings]
        self.parent.res_region.setRegion(bounds)
        self.parent.run_analysis()

    def result(self, event):
        '''Perform fit to sum of two gaussians, intergrate

        Arguments:
            event: Event instance with sweeps to fit

        Returns:
            area and polarization from sum under gaussian
        '''

        self.pi = [-0.1, self.parent.config.channel['cent_freq'], self.parent.config.channel['mod_freq'] * 1E-3 / 10,
                   -0.01, self.parent.config.channel['cent_freq'], self.parent.config.channel['mod_freq'] * 1E-3 / 10]

        sweep = event.fitsub
        freqs = event.scan.freq_list
        bounds = [x * len(sweep) for x in self.wings]
        data = [z for x, z in enumerate(zip(freqs, sweep)) if bounds[0] < x < bounds[1]]
        X = np.array([x for x, y in data])
        Y = np.array([y for x, y in data])
        pf, pcov = optimize.curve_fit(self.sum_gaussians, X, Y, p0=self.pi)
        pstd = np.sqrt(np.diag(pcov))
        fit = self.sum_gaussians(freqs, *pf)

        residuals = Y - self.sum_gaussians(X, *pf)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((Y - np.mean(Y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot)

        area = fit.sum()
        pol = area * event.cc
        text_list = [f"{f:.2e} ± {s:.2e}" for f, s in zip(pf, pstd)]
        self.message.setText(
            f"Fit coefficients: \t \t \t R-squared: {r_squared:.2f}\n" + "\n".join(text_list) + "\n" + f"Area: {area}")
        return fit, area, pol

    def sum_gaussians(self, x, *p):
        return p[0] * np.exp(-np.power((x - p[1]), 2) / (2 * np.power(p[2], 2))) + p[3] * np.exp(
            -np.power((x - p[4]), 2) / (2 * np.power(p[5], 2)))


class FitDeuteron(QWidget):
    '''Layout and methods for Dulya fits from deuteron_fits.py
    '''

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent

        d_fit_params = self.parent.event.config.settings['analysis']['d_fit_params']

        self.space = QVBoxLayout()
        self.setLayout(self.space)
        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.name = "Deuteron Peak Fit"
        self.init_label = QLabel("Deutron Lineshape Fit")
        self.grid.addWidget(self.init_label, 0, 0)
        self.message = QLabel()
        self.space.layout().addWidget(self.message)

        self.grid = QGridLayout()
        self.space.addLayout(self.grid)
        self.bounds_label = QLabel("Initial Parameters:")
        self.grid.addWidget(self.bounds_label, 0, 0)
        self.param_label = []
        self.param_edit = []
        for i, key in enumerate(d_fit_params.keys()):  # setup line edits for each parameter
            self.param_label.append(QLabel(key))
            self.grid.addWidget(self.param_label[i], i + 1, 0)
            self.param_edit.append(QLineEdit())
            self.param_edit[i].setText(str(d_fit_params[key]))
            self.grid.addWidget(self.param_edit[i], i + 1, 1)

        try:
            self.params
        except AttributeError:
            self.params = self.parent.event.config.settings['analysis']['d_fit_params']

    def switch_here(self):
        '''Things to do when this stack is chosen'''
        self.parent.res_region.setBrush(pg.mkBrush(0, 0, 180, 0))

    def result(self, event):
        '''Perform Dueteron fit and calculate polarization

        Arguments:
            event: Event instance with sweeps to fit

        Returns:
            fit, resulting r asymmetry (instead of area) and polarization
        '''

        sweep = event.fitsub
        freqs = event.scan.freq_list

        labels = [e.text() for e in self.param_label]
        values = [float(e.text()) for e in self.param_edit]

        self.params = dict(zip(labels, values))
        print(self.params)

        res = DFits(freqs, sweep, self.params)

        r = res.result.params['r'].value
        fit = res.result.best_fit
        if res.result.success:  # if successful, set these params for next time
            self.params = res.result.params.valuesdict()

        pol = (r * r - 1) / (r * r + r + 1)
        area = fit.sum()
        cc = pol / area
        text = '\n'
        i = 0
        for name, param in res.result.params.items():
            i += 1
            text = text + f'{name} {param.value:.3e}+-{param.stderr:.3e} '
            if i == 4:
                text = text + "\n"
        self.message.setText(f"Polarization: {pol * 100:.2f}%, Area:  {area:.2f}, CC:  {cc:.2f}\n {text}")
        return fit, r, pol




