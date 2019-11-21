from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    einvoice_operator_id = fields.Many2one(
        comodel_name="res.partner.operator.einvoice",
        related="company_id.partner_id.einvoice_operator_id",
        string="eInvoice Operator",
        readonly=False,
    )
