# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Avoin.Systems.
#    Copyright 2019 Avoin.Systems.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see http://www.gnu.org/licenses/agpl.html
#
##############################################################################

import logging

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import float_round, float_compare

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def _get_auto_reconcile_queries(self, params, match_amount=True):
        sql_queries = list()

        # If no reference is present, return empty list
        if not params['ref']:
            return sql_queries

        if match_amount:
            amount_sql = "AND ({amount} = %(amount)s " \
                         "OR (acc.internal_type = 'liquidity' " \
                         "AND {liquidity} = %(amount)s)) " \
                .format(
                    amount=params['amount_field'],
                    liquidity=params['liquidity_field'])
        else:
            amount_sql = ''

        specific_query = \
            " AND (LTRIM(aml.payment_reference, '0') = LTRIM(%(ref)s, '0') " \
            "OR LTRIM(aml.ref, '0') = LTRIM(%(ref)s, '0')) " \
            "{amount_sql} ORDER BY date_maturity asc, aml.id asc".format(
                amount_sql=amount_sql)

        # Look for structured communication match
        sql_queries.append(
            self._get_common_sql_query() + specific_query)

        # Look for structured communication match, overlook partner
        sql_queries.append(
            self._get_common_sql_query(overlook_partner=True) +
            specific_query)

        return sql_queries

    def _get_auto_reconcile_params(self):
        # Produce parameters for SQL query
        #
        # Note: Odoo's float_round method contains floating point arithmetic that can produce incorrect results
        # due to the limitations of float data type; e.g. 80.60 is 'rounded' to 80.60000000000001.
        # (float_round does a final, un-rounded multiplication at the end)
        # Re-rounding the result with Python's round method rectifies the issue.
        # Call to float_round is needed to get the desired half-up rounding.
        # Rounding needs to be precise because the resulting values are passed as-is to Postgresql.
        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        precision = st_line_currency and st_line_currency.decimal_places or \
                    company_currency.decimal_places
        currency = (st_line_currency and st_line_currency !=
                    company_currency) and st_line_currency.id or False
        amount_field = currency and 'amount_residual_currency' or \
                       'amount_residual'
        liquidity_field = currency and 'amount_currency' or \
                          amount > 0 and 'debit' or 'credit'
        params = {'company_id': self.env.user.company_id.id,
                  'account_payable_receivable': (
                      self.journal_id.default_credit_account_id.id,
                      self.journal_id.default_debit_account_id.id),
                  'amount': round(float_round(amount, precision_digits=precision), precision),
                  'partner_id': self.partner_id.id,
                  'ref': self.ref,
                  'currency': currency,
                  'amount_field': amount_field,
                  'liquidity_field': liquidity_field
                  }
        return params

    def _get_match_recs(self):
        match_recs = self.env['account.move.line']
        params = self._get_auto_reconcile_params()
        for sql_query in self._get_auto_reconcile_queries(params):
            self.env.cr.execute(sql_query, params)
            match_recs = self.env.cr.dictfetchall()
            if len(match_recs) == 1:
                break
        if len(match_recs) != 1:
            return False
        return self.env['account.move.line'].browse(
            [aml.get('id') for aml in match_recs])

    def _get_auto_reconcile_new_aml_dicts(self, match_recs):
        """
        It is some times necessary to create new account.move.line(s) when
        auto reconciling complex situations, e.g. cash discounts.
        This stub method may be extended to handle those situations.
        """
        return []

    def is_valid_finnish_match(self, match_recs, new_aml_dicts):
        """
        Check if this is a valid match and can be reconciled. This method is intended to be
        extended by other modules to add domain specific checks.
        - Motivation: Finnish auto reconciliation can get much more complex than Odoo standard
          auto reconciliation, so extra checks are nice to have.
        - The word "finnish" in the method name comes from the fact that this is part of the
          Finnish reconciliation package and to make it clear this is not part of standard Odoo.
        - This base version of the method checks that the monetary balance of the arguments matches
          with the amount on this line.
        - This method is called by auto_reconcile method, so extending modules need not worry
          about calling this, unless they extend/override auto_reconcile too.
        :param match_recs: a set of account.move.line(s) to be reconciled with self
        :param new_aml_dicts: a list of dicts from which a set of account.move.lines will be
        created and reconciled with self
        :return: True, if validation passes, else False. Note that extending methods should
        always return False or super()
        """
        balance = sum(m.balance for m in match_recs) + \
                  sum(d['credit'] - d['debit'] for d in new_aml_dicts)
        prec_ac = self.env['decimal.precision'].precision_get('Account')
        if float_compare(self.amount, balance, precision_digits=prec_ac) != 0:
            _logger.debug("Match validation fail: balance mismatch.\n"
                          "Own balance {}, match balance {}".format(self.amount, balance))
            return False
        return True

    @api.multi
    def auto_reconcile(self):
        """
        Try to automatically reconcile the statement.line return the
        counterpart journal entry/ies if the automatic reconciliation
        succeeded, False otherwise.
        """
        if self.company_id.auto_reconcile_method != 'finnish':
            return super(AccountBankStatementLine, self).auto_reconcile()

        self.ensure_one()

        match_recs = self._get_match_recs()
        if not match_recs:
            _logger.info('No reconciliation match found for %s' % self)
            return False
        # Now reconcile
        counterpart_aml_dicts = []
        payment_aml_rec = self.env['account.move.line']
        for aml in match_recs:
            if aml.account_id.internal_type == 'liquidity':
                payment_aml_rec = (payment_aml_rec | aml)
            else:
                amount = aml.currency_id and aml.amount_residual_currency or \
                    aml.amount_residual
                counterpart_aml_dicts.append({
                    'name': aml.name if aml.name != '/' else aml.move_id.name,
                    'debit': amount < 0 and -amount or 0,
                    'credit': amount > 0 and amount or 0,
                    'move_line': aml
                })

        try:
            new_aml_dicts = self._get_auto_reconcile_new_aml_dicts(match_recs)
            if not self.is_valid_finnish_match(match_recs, new_aml_dicts):
                return False
            with self._cr.savepoint():
                counterpart = self.process_reconciliation(
                    counterpart_aml_dicts=counterpart_aml_dicts,
                    payment_aml_rec=payment_aml_rec,
                    new_aml_dicts=new_aml_dicts)
                _logger.info('Reconciled %s with %s' % (self, counterpart))
            return counterpart
        except UserError:
            # A configuration / business logic error that makes it impossible
            # to auto-reconcile should not be raised since automatic
            # reconciliation is just an amenity and the user will get the same
            # exception when manually reconciling. Other types of exception
            # are (hopefully) programmation errors and should cause a
            # stacktrace.
            _logger.info('Reconciliation failed for %s' % self)
            self.invalidate_cache()
            self.env['account.move'].invalidate_cache()
            self.env['account.move.line'].invalidate_cache()
            return False

    def get_reconciliation_proposition(self, excluded_ids=None):

        self.ensure_one()

        if not excluded_ids:
            excluded_ids = []
        amount = self.amount_currency or self.amount
        company_currency = self.journal_id.company_id.currency_id
        st_line_currency = self.currency_id or self.journal_id.currency_id
        currency = (
                               st_line_currency and st_line_currency != company_currency) and st_line_currency.id or False
        precision = st_line_currency and st_line_currency.decimal_places or company_currency.decimal_places
        field = currency and 'amount_residual_currency' or 'amount_residual'
        liquidity_field = currency and 'amount_currency' or amount > 0 and 'debit' or 'credit'
        liquidity_amt_clause = currency and '%(amount)s::numeric' or 'abs(%(amount)s::numeric)'
        # See comment in _get_auto_reconcile_params for explanation of usage of round and float_round.
        params = {'company_id': self.env.user.company_id.id,
                  'account_payable_receivable': (
                      self.journal_id.default_credit_account_id.id,
                      self.journal_id.default_debit_account_id.id),
                  'amount': round(float_round(amount, precision_digits=precision), precision),
                  'partner_id': self.partner_id.id,
                  'excluded_ids': tuple(excluded_ids),
                  'ref': self.ref,
                  }

        if self.ref:
            # Check for both matching reference and amount
            add_to_select = ", CASE WHEN LTRIM(aml.payment_reference, '0') = %(ref)s \
                            THEN 1 ELSE 2 END as temp_field_order "
            add_to_from = " JOIN account_move m ON m.id = aml.move_id "
            select_clause, from_clause, where_clause = self._get_common_sql_query(
                overlook_partner=True,
                excluded_ids=excluded_ids, split=True)
            sql_query = select_clause + add_to_select + from_clause + add_to_from + where_clause
            add_to_where = " AND (LTRIM(aml.payment_reference, '0') = LTRIM(%(ref)s, '0') or m.name = %(ref)s) \
                            AND (" + field + " = %(amount)s::numeric OR (acc.internal_type = 'liquidity' \
                            AND " + liquidity_field + \
                            " = " + liquidity_amt_clause + ")) \
                            ORDER BY temp_field_order, date_maturity desc, aml.id desc"

            self.env.cr.execute(sql_query + add_to_where, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

            # Check for just a matching reference
            add_to_where = " AND (LTRIM(aml.payment_reference, '0') = LTRIM(%(ref)s, '0') or m.name = %(ref)s) \
                            ORDER BY temp_field_order, date_maturity desc, aml.id desc"
            self.env.cr.execute(sql_query + add_to_where, params)
            results = self.env.cr.fetchone()
            if results:
                return self.env['account.move.line'].browse(results[0])

        # Return super if our queries yielded nothing
        return super(AccountBankStatementLine,
                     self).get_reconciliation_proposition(
            excluded_ids=excluded_ids)

    def get_statement_line_for_reconciliation_widget(self):
        res = super(AccountBankStatementLine,
                    self).get_statement_line_for_reconciliation_widget()

        # The partner_name key holds a name of an actual res.partner connected to the bank statement.
        # If we can find an existing res.partner on an invoice that matches to the bank statement line's
        # payment_reference, we use that.
        #
        # The bank statement line's partner_name field is used by bank statement importer to store
        # bank statement's field's `partner`-column that has some sort of description of the other party of the
        # payment. This might be just a name, name and description of the transaction or something else.
        # The `self.partner_name`-field has a slightly misleading name because of the way the importer uses it.
        #  We are showing this field as a separate column on the reconciliation view since it often contains
        # the most descriptive information about the payment.
        #
        # The dict is returned to a Qweb view and not to create any records, so the keys' names don't
        # have to match any existing fields. Since `partner_name` is used to store the name of
        # an actual partner, we create a new key `partner_note` that contains the bank statement line's
        # partner_name -field.

        if self.partner_name:
            res['partner_note'] = self.partner_name

        invoice_model = self.env['account.invoice']

        reference = res['ref']

        invoice = invoice_model.search([
            ('state', '=', 'open'),
            '|', ('payment_reference', '=', reference),
            ('reference', '=', reference)
        ], limit=1) if reference else False

        if invoice:
            res['partner_name'] = invoice.partner_id.name
            res['partner_id'] = invoice.partner_id.id
            res['has_no_partner'] = False
        return res
