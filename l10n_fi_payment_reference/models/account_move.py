# Copyright (C) Avoin.Systems 2019
import re
from odoo import models, _
from odoo.exceptions import UserError
import logging

log = logging.getLogger(__name__)


def number2numeric(number):

    invoice_number = re.sub(r'\D', '', number)

    if invoice_number == '' or invoice_number is False:
        raise UserError(_('Invoice number must contain numeric characters'))

    # Make sure the base number is 3...19 characters long
    if len(invoice_number) < 3:
        log.warning('Invoice number {} is less than 3 characters long, '
                    'padding to 3 characters with prefix 11.'
                    .format(invoice_number))
        invoice_number = ('11' + invoice_number)[-3:]
    elif len(invoice_number) > 19:
        log.warning('Invoice number {} is over 19 characters long, '
                    'truncating to 19 characters'.format(invoice_number))
        invoice_number = invoice_number[:19]

    return invoice_number


def get_finnish_check_digit(base_number):
    # Multiply digits from end to beginning with 7, 3 and 1 and
    # calculate the sum of the products
    total = sum((7, 3, 1)[idx % 3] * int(val) for idx, val in
                enumerate(base_number[::-1]))

    # Subtract the sum from the next decade. 10 = 0
    return str((10 - (total % 10)) % 10)


def get_rf_check_digits(base_number):
    check_base = base_number + 'RF00'
    # 1. Convert all non-digits to digits
    # 2. Calculate the modulo 97
    # 3. Subtract the remainder from 98
    # 4. Add leading zeros if necessary
    return ''.join(
        ['00', str(98 - (int(''.join(
            [x if x.isdigit() else str(ord(x) - 55) for x in
             check_base])) % 97))])[-2:]


def compute_payment_reference_finnish(number):
    # Drop all non-numeric characters
    invoice_number = number2numeric(number)

    # Calculate the Finnish check digit
    check_digit = get_finnish_check_digit(invoice_number)

    return invoice_number + check_digit


def compute_payment_reference_finnish_rf(number):
    # Drop all non-numeric characters
    invoice_number = number2numeric(number)

    # Calculate the Finnish check digit
    invoice_number += get_finnish_check_digit(invoice_number)

    # Calculate the RF check digits
    rf_check_digits = get_rf_check_digits(invoice_number)

    return 'RF' + rf_check_digits + invoice_number


class AccountInvoiceFinnish(models.Model):
    _inherit = 'account.move'

    def _get_invoice_reference_finnish_rf_invoice(self):
        self.ensure_one()
        return compute_payment_reference_finnish_rf(self.name)

    def _get_invoice_reference_finnish_rf_partner(self):
        self.ensure_one()
        return compute_payment_reference_finnish_rf(str(self.partner_id.id))

    def _get_invoice_reference_finnish_invoice(self):
        self.ensure_one()
        return compute_payment_reference_finnish(self.name)

    def _get_invoice_reference_finnish_partner(self):
        self.ensure_one()
        return compute_payment_reference_finnish(str(self.partner_id.id))
