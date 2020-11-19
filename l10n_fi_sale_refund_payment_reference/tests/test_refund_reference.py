from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRefundGeneratesReference(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        # super will skip this test if l10n_generic_coa is not installed
        super().setUpClass()

        cls.invoice = cls.init_invoice('out_refund')

    def test_get_reference_odoo_refund(self):
        self.assertFalse(self.invoice.invoice_payment_ref)
        self.invoice.journal_id.invoice_reference_model = 'odoo'
        self.invoice.post()
        self.assertTrue(self.invoice.invoice_payment_ref)

    def test_get_reference_odoo_partner(self):
        self.assertFalse(self.invoice.invoice_payment_ref)
        self.invoice.journal_id.invoice_reference_type = 'partner'
        self.invoice.journal_id.invoice_reference_model = 'odoo'
        self.invoice.post()
        self.assertTrue(self.invoice.invoice_payment_ref)
