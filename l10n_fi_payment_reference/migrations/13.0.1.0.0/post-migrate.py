import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('Migrating invoice payment references')
    cr.execute("""
    UPDATE account_move AS m
    SET invoice_payment_ref = i.payment_reference
    FROM account_invoice AS i
    WHERE m.id = i.move_id;
    """)

    _logger.info('Migrated invoice payment references')
