# Copyright 2017 Oy Tawasta OS Technologies Ltd.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    business_id = fields.Char(
        string='Business ID',
        compute=lambda s: s._compute_nonstored_identification(
            'business_id', 'business_id',
        ),
        inverse=lambda s: s._inverse_identification(
            'business_id', 'business_id',
        ),
        search=lambda s, *a: s._search_identification(
            'business_id', *a
        ),
    )

    # copy of _compute_identification method with a fix for nonstored fields
    @api.depends("id_numbers")
    def _compute_nonstored_identification(self, field_name, category_code):
        """ Compute a field that indicates a certain ID type.

        Use this on a field that represents a certain ID type. It will compute
        the desired field as that ID(s).

        This ID can be worked with as if it were a Char field, but it will
        be relating back to a ``res.partner.id_number`` instead.

        Example:

            .. code-block:: python

            social_security = fields.Char(
                compute=lambda s: s._compute_identification(
                    'social_security', 'SSN',
                ),
                inverse=lambda s: s._inverse_identification(
                    'social_security', 'SSN',
                ),
                search=lambda s, *a: s._search_identification(
                    'SSN', *a
                ),
            )

        Args:
            field_name (str): Name of field to set.
            category_code (str): Category code of the Identification type.
        """
        for record in self:
            id_numbers = record.id_numbers.filtered(
                lambda r: r.category_id.code == category_code
            )
            if not id_numbers:
                record[field_name] = False
                continue
            value = id_numbers[0].name
            record[field_name] = value
