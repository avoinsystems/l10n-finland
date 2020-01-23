from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('standard', 'at_install')
class MovePostTest(TransactionCase):

    def setUp(self):
        super(MovePostTest, self).setUp()
        partner_id = self.env.ref('base.res_partner_1')
        self.company = self.env.ref('base.main_company')
        self.company.write({'payment_reference_type': 'fi'})
        account_revenue = self.env['account.account'].search(
            [('user_type_id',
              '=',
              self.env.ref('account.data_account_type_revenue').id)],
            limit=1)

        self.move = self.env['account.move'].create({
            'partner_id': partner_id.id,
            'type': 'out_invoice',
            'company_id': self.company.id,
        })

        self.env['account.move.line'].with_context(check_move_validity=False) \
            .create({
                'move_id': self.move.id,
                'account_id': account_revenue.id,
            })

    def test_post(self):
        self.assertIsNone(self.move.post())
        prev_reference = self.move.payment_reference
        self.assertIsNone(self.move.post())
        self.assertEquals(prev_reference, self.move.payment_reference)
        self.move.write({'payment_reference': None})
        self.company.write({'payment_reference_type': 'rf'})
        self.assertIsNone(self.move.post())
        self.company.write({'payment_reference_type': 'none'})
        self.assertIsNone(self.move.post())
        self.assertEquals(None, self.env['account.move'].search(
            [], limit=2)._compute_payment_reference())
