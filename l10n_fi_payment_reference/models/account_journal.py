# See LICENSE for licensing information

import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    invoice_reference_model = fields.Selection(selection_add=[
        ('finnish', 'Finnish Standard Reference'),
        ('finnish_rf', 'Finnish Creditor Reference (RF)'),
    ])
