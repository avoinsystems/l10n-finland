# Copyright Avoin.Systems 2018
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "[DEPRECATED] Finnish Sales Invoice Payment Reference",
    "summary": "You should uninstall this module if it is installed. Hooks "
               "ensure that settings will be migrated to use l10n_fi if "
               "available.",
    "version": "13.0.X.X.X",
    "category": "Localization",
    "website": "https://github.com/OCA/l10n-finland",
    "author": "Avoin.Systems, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        "account",
    ],
    "installable": False,
    "data": [
    ],
    "uninstall_hook": "uninstall_hook",
}
