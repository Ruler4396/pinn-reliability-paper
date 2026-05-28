from .burgers import BurgersCase
from .fisher_kpp import FisherKPPCase
from .helmholtz import HelmholtzCase
from .lid_driven_cavity import LidDrivenCavityCase
from .advection_diffusion import AdvectionDiffusionCase
from .advection_dominated_diffusion import AdvectionDominatedDiffusionCase
from .poisson import PoissonCase
from .stokes_poiseuille import StokesPoiseuilleCase
from .variable_coefficient_diffusion import VariableCoefficientDiffusionCase


def build_case(case_spec):
    if isinstance(case_spec, str):
        case_name = case_spec
        case_kwargs = {}
    else:
        case_name = str(case_spec["name"])
        case_kwargs = {key: value for key, value in case_spec.items() if key != "name"}

    table = {
        "poisson": PoissonCase,
        "fisher_kpp": FisherKPPCase,
        "helmholtz": HelmholtzCase,
        "advection_diffusion": AdvectionDiffusionCase,
        "advection_dominated_diffusion": AdvectionDominatedDiffusionCase,
        "variable_coefficient_diffusion": VariableCoefficientDiffusionCase,
        "burgers": BurgersCase,
        "stokes_poiseuille": StokesPoiseuilleCase,
        "lid_driven_cavity": LidDrivenCavityCase,
    }
    if case_name not in table:
        raise ValueError(f"Unsupported case: {case_name}")
    return table[case_name](**case_kwargs)
