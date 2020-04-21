from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('Removing invalid l10n_fi_payment_reference views')

    env = api.Environment(cr, SUPERUSER_ID, {})

    view = env['ir.ui.view'].search([
        ('arch_fs', '=', 'l10n_fi_payment_reference/views/res_config.xml')]
    )

    if not view:
        _logger.info('Broken view have already been removed. Doing nothing.')
        return

    view.unlink()

    _logger.info('Removed invalid l10n_fi_payment_reference views')
