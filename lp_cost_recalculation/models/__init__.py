# -*- coding: utf-8 -*-

# updated models
from . import account_move
from . import product
from . import res_config_settings

# abstract recalculation model
from . import cost_recalculation_abstract

# specific new models
from . import material_loss_allocation
from . import labor_cost_allocation
from . import click_charge_allocation
from . import overhead_cost_allocation
