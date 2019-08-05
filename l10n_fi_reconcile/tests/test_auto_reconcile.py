from odoo.tests.common import SavepointCase
import logging

_logger = logging.getLogger(__name__)


class ReconciliationPropositionTestCase(SavepointCase):
    # To run this test case, install a chart of account in the same test run
    # before running tests on this module

    post_install = True
    at_install = False

    @classmethod
    def setUpClass(cls):
        super(ReconciliationPropositionTestCase, cls).setUpClass()
        cls.env.user.company_id.auto_reconcile_method = "finnish"
        domain = [('company_id', '=', cls.env.ref('base.main_company').id)]
        if not cls.env['account.account'].search_count(domain):
            cls.skipTest("No Chart of account found")

        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'sale')], limit=1)
        assert cls.journal, "There isn't a single sale journal in the system"
        cls.reference = "000111222333999"
        cls.invoice = cls.env['account.invoice'].create({
            'type': 'out_invoice',
            'journal_id': cls.journal.id,
            'partner_id': cls.env['res.partner'].search([('customer', '=', True)], limit=1).id,
            'payment_reference': cls.reference,
            'invoice_line_ids': [(0, 0, {
                'name': 'An invoice line',
                'account_id': cls.env['account.account'].search([], limit=1).id,
                'quantity': 1,
                'price_unit': 100,
            })]
        })
        cls.invoice.action_invoice_open()
        cls.to_reconcile = cls.invoice.move_id.line_ids

        bank_account = cls.env['account.bank.statement'].with_context(
            journal_type='bank')._default_journal()
        assert bank_account, "No bank account"
        cls.statement = cls.env['account.bank.statement'].create({'journal_id': bank_account.id})

    def test_010_auto_reconcile_should_find_match_from_invoice(self):
        statement_line = self.env['account.bank.statement.line'].create({
            'statement_id': self.statement.id,
            'name': "Some kind of payment",
            'ref': self.reference,
            'amount': 100,
        })
        match = statement_line._get_match_recs()
        self.assertEqual(len(match), 1,
                         msg="Logic should have found exactly one match")
        self.assertIn(match, self.to_reconcile)

    def test_020_auto_reconcile_should_not_match_if_ref_mismatch(self):
        statement_line = self.env['account.bank.statement.line'].create({
            'statement_id': self.statement.id,
            'name': "Some kind of payment",
            'ref': "some_fake_reference_that_should_not_exist",
            'amount': 100,
        })
        match = statement_line._get_match_recs()
        # Use is to differentiate falsy values: we expect the boolean False
        self.assertIs(match, False)

    def test_030_auto_reconcile_should_not_match_if_price_mismatch(self):
        statement_line = self.env['account.bank.statement.line'].create({
            'statement_id': self.statement.id,
            'name': "Some kind of payment",
            'ref': self.reference,
            'amount': 100 - 20,
        })
        match = statement_line._get_match_recs()
        # Use is to differentiate falsy values: we expect the boolean False
        self.assertIs(match, False)
