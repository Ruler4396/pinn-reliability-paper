from .advection_diffusion import AdvectionDiffusionCase
from .advection_dominated_diffusion import AdvectionDominatedDiffusionCase
from .allen_cahn import AllenCahnCase
from .burgers import BurgersCase
from .fisher_kpp import FisherKPPCase
from .heat_equation import HeatEquationCase
from .helmholtz import HelmholtzCase
from .kdv_double_soliton import KdVDoubleSolitonCase
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
        "advection_diffusion": AdvectionDiffusionCase,
        "advection_dominated_diffusion": AdvectionDominatedDiffusionCase,
        "allen_cahn": AllenCahnCase,
        "burgers": BurgersCase,
        "fisher_kpp": FisherKPPCase,
        "heat_equation": HeatEquationCase,
        "helmholtz": HelmholtzCase,
        "kdv_double_soliton": KdVDoubleSolitonCase,
        "kdv_soliton": KdVSolitonCase,
        "lid_driven_cavity": LidDrivenCavityCase,
        "nls_soliton": NLSSolitonCase,
        "poisson": PoissonCase,
        "stokes_poiseuille": StokesPoiseuilleCase,
        "taylor_green": TaylorGreenCase,
        "variable_coefficient_diffusion": VariableCoefficientDiffusionCase,
        "wave_equation": WaveEquationCase,
    }
    if case_name not in table:
        raise ValueError(f"Unsupported case: {case_name}")
    return table[case_name](**case_kwargs)
