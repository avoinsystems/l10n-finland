from odoo import api, fields, models
from odoo.osv import expression


class ResPartnerOperatorEinvoice(models.Model):
    _name = "res.partner.operator.einvoice"
    _description = "eInvoice Operator"
    _order = "sequence, id"


    name = fields.Char(string="Operator", required=True)
    active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer("Sequence")
    identifier = fields.Char(
        string="Identifier",
        required=True,
        size=35,
        help="Monetary Institution Identifier (see https://tieke.fi)",
    )
    ttype = fields.Selection(
        [
            ("bank", "Bank with Finvoice brokerage service"),
            ("broker", "Carrier broker"),  # default
        ],
        "Type",
        default="broker",
    )

    _sql_constraints = [
        (
            "operator_identifier_uniq",
            "unique(identifier)",
            '"Identifier" should be unique!',
        ),
    ]

    def name_get(self):
        """
        Overwrite core method to add value of `identifier` ("Identifier") field
        into name of recors.
        """
        result = []
        for operator in self:
            name = " - ".join([operator.identifier, operator.name])
            result.append((operator.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("identifier", operator, name),
                      ("name", operator, name)]
        einvoice_operators = self.search(domain + args, limit=limit)
        return einvoice_operators.name_get()
