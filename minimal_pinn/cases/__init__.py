from .allen_cahn import AllenCahnCase
from .burgers import BurgersCase
from .fisher_kpp import FisherKPPCase
from .heat_equation import HeatEquationCase
from .kdv_double_soliton import KdVDoubleSolitonCase
from .kdv_soliton import KdVSolitonCase
from .nls_soliton import NLSSolitonCase
from .poisson import PoissonCase
from .stokes_poiseuille import StokesPoiseuilleCase
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
        "burgers": BurgersCase,
        "fisher_kpp": FisherKPPCase,
        "heat_equation": HeatEquationCase,
        "kdv_double_soliton": KdVDoubleSolitonCase,
        "kdv_soliton": KdVSolitonCase,
        "nls_soliton": NLSSolitonCase,
        "poisson": PoissonCase,
        "stokes_poiseuille": StokesPoiseuilleCase,
        "wave_equation": WaveEquationCase,
    }
    if case_name not in table:
        raise ValueError(f"Unsupported case: {case_name}")
    return table[case_name](**case_kwargs)
