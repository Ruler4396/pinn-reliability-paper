from .burgers import BurgersCase
from .fisher_kpp import FisherKPPCase
from .helmholtz import HelmholtzCase
from .lid_driven_cavity import LidDrivenCavityCase
from .advection_diffusion import AdvectionDiffusionCase
from .advection_dominated_diffusion import AdvectionDominatedDiffusionCase
from .allen_cahn import AllenCahnCase
from .allen_cahn_circular import AllenCahnCircularCase
from .burgers import BurgersCase
from .fisher_kpp import FisherKPPCase
from .heat_equation import HeatEquationCase
from .helmholtz import HelmholtzCase
from .kdv_soliton import KdVSolitonCase
from .lid_driven_cavity import LidDrivenCavityCase
from .nls_soliton import NLSSolitonCase
from .poisson import PoissonCase
from .stokes_poiseuille import StokesPoiseuilleCase
from .taylor_green import TaylorGreenCase
from .variable_coefficient_diffusion import VariableCoefficientDiffusionCase
from .wave_equation import WaveEquationCase


def build_case(case_spec):
    if isinstance(case_spec, str):
        case_name = case_spec
        case_kwargs = {}
    else:
        case_name = str(case_spec["name"])
        case_kwargs = {key: value for key, value in case_spec.items() if key != "name"}

    table = {
        "allen_cahn": AllenCahnCase,
        "allen_cahn_circular": AllenCahnCircularCase,
        "heat_equation": HeatEquationCase,
        "kdv_soliton": KdVSolitonCase,
        "nls_soliton": NLSSolitonCase,
        "poisson": PoissonCase,
        "fisher_kpp": FisherKPPCase,
        "helmholtz": HelmholtzCase,
        "advection_diffusion": AdvectionDiffusionCase,
        "advection_dominated_diffusion": AdvectionDominatedDiffusionCase,
        "variable_coefficient_diffusion": VariableCoefficientDiffusionCase,
        "burgers": BurgersCase,
        "stokes_poiseuille": StokesPoiseuilleCase,
        "taylor_green": TaylorGreenCase,
        "wave_equation": WaveEquationCase,
        "lid_driven_cavity": LidDrivenCavityCase,
    }
    if case_name not in table:
        raise ValueError(f"Unsupported case: {case_name}")
    return table[case_name](**case_kwargs)
