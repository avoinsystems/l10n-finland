from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('Synchronizing res.partner edicode fields '
                 'from parents to children')

    env = api.Environment(cr, SUPERUSER_ID, {})

    partners = env['res.partner'].search(
        ['|',
           ('edicode', '!=', False),
           ('einvoice_operator_id', '!=', False),
         ('is_company', '=', True)]
    )
    for partner in partners:
        partner._commercial_sync_to_children()

    _logger.info('Synchronized res.partner edicode fields '
                 'from parents to children')
