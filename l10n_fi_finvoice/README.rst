.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================
Account invoice Finvoice
========================

Converts between Odoo invoice and Finvoice 2.01



Based on the documentation (static files also in `docs/`)

http://www.finanssiala.fi/finvoice/dokumentit/Finvoice_2_1_soveltamisohje.pdf
http://www.finanssiala.fi/finvoice/dokumentit/Finvoice_def_2_1_18102013.xls

Configuration
=============
Install py-finvoice

.. code-block:: bash

   pip install git+https://github.com/Tawasta/py-finvoice

   # This should be fine too, but use with own risk
   pip install py-finvoice

Usage
=====
- This module only adds a field `finvoice_xml` and the logic behind it.
- Field is supposed to be used as a helper for methods. Please avoid adding it directly to any views, as it is a large non-stored computed field. Using it in views will increase view load times.

Known issues / Roadmap
======================
- Does not separate different VAT classes on invoice details level
- Does not support payment overdue fine
- Does not support partial payments (PaymentStatusCode)
- Does not add discounts to Finvoice (discounts work, but they arent separated from the amount
- Only supports domestic invoices
- Error when there is no due date

Credits
=======

Contributors
------------

* Jarmo Kortetjärvi <jarmo.kortetjarvi@tawasta.fi>

Maintainer
----------

.. image:: http://tawasta.fi/templates/tawastrap/images/logo.png
   :alt: Oy Tawasta OS Technologies Ltd.
   :target: http://tawasta.fi/

This module is maintained by Oy Tawasta OS Technologies Ltd.
