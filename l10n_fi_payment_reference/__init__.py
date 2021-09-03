import logging

from odoo import SUPERUSER_ID

from. import models
from odoo.api import Environment


_logger = logging.getLogger(__name__)


def uninstall_hook(cr, registry):
    with Environment.manage(), cr.savepoint():
        env = Environment(cr, SUPERUSER_ID, {}, su=True)
        fix_journal_invoice_reference_models(env)


def fix_journal_invoice_reference_models(env: Environment):
    _logger.info(
        "Migrating journal reference models to use l10n_fi counterparts if "
        "available"
    )
    AccountJournal = env["account.journal"]
    ref_model_field = AccountJournal._fields["invoice_reference_model"]
    available_selections = [technical for (technical, _) in ref_model_field.selection]
    if "fi" in available_selections:
        _logger.info("Migrating 'finnish' -> 'fi'")
        finnish_journals = AccountJournal.search([
            ("invoice_reference_model", "=", "finnish"),
        ])
        finnish_journals.write({
            "invoice_reference_model": "fi",
        })
    if "fi_rf" in available_selections:
        _logger.info("Migrating 'finnish_rf' -> 'fi_rf'")
        finnish_rf_journals = AccountJournal.search([
            ("invoice_reference_model", "=", "finnish_rf"),
        ])
        finnish_rf_journals.write({
            "invoice_reference_model": "fi_rf",
        })
    _logger.info("Done migrating reference models")
