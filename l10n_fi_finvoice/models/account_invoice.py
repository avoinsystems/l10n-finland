# -*- coding: utf-8 -*-
import logging
import sys
import datetime
import StringIO
import re

from dateutil.tz import tzlocal
from odoo import api, fields, models

# Finvoice imports
from finvoice.finvoice201 import Finvoice

# Message transmission details
from finvoice.finvoice201 import MessageTransmissionDetailsType
from finvoice.finvoice201 import MessageSenderDetailsType
from finvoice.finvoice201 import MessageReceiverDetailsType
from finvoice.finvoice201 import MessageDetailsType

# Seller party details
from finvoice.finvoice201 import SellerPartyDetailsType
from finvoice.finvoice201 import SellerPostalAddressDetailsType

# Seller information details
from finvoice.finvoice201 import SellerInformationDetailsType
from finvoice.finvoice201 import SellerAccountDetailsType
from finvoice.finvoice201 import SellerAccountIDType
from finvoice.finvoice201 import SellerBicType

# Buyer party details
from finvoice.finvoice201 import BuyerPartyDetailsType
from finvoice.finvoice201 import BuyerPostalAddressDetailsType

# Delivery party details
from finvoice.finvoice201 import DeliveryPartyDetailsType
from finvoice.finvoice201 import DeliveryPostalAddressDetailsType

# Invoice details
from finvoice.finvoice201 import InvoiceDetailsType
from finvoice.finvoice201 import InvoiceTypeCodeType
from finvoice.finvoice201 import VatSpecificationDetailsType
from finvoice.finvoice201 import PaymentTermsDetailsType
from finvoice.finvoice201 import PaymentOverDueFineDetailsType

# Payment status details
from finvoice.finvoice201 import PaymentStatusDetailsType

# Invoice rows
from finvoice.finvoice201 import InvoiceRowType
from finvoice.finvoice201 import QuantityType

# EPI details
from finvoice.finvoice201 import EpiDetailsType
from finvoice.finvoice201 import EpiIdentificationDetailsType
from finvoice.finvoice201 import EpiPartyDetailsType
from finvoice.finvoice201 import EpiBfiPartyDetailsType
from finvoice.finvoice201 import EpiBeneficiaryPartyDetailsType
from finvoice.finvoice201 import EpiAccountIDType
from finvoice.finvoice201 import EpiBfiIdentifierType
from finvoice.finvoice201 import EpiPaymentInstructionDetailsType
from finvoice.finvoice201 import EpiRemittanceInfoIdentifierType
from finvoice.finvoice201 import EpiChargeType

# General imports
from finvoice.finvoice201 import date
from finvoice.finvoice201 import amount
from finvoice.soap.envelope import Envelope, Header, Body
from finvoice.soap.msgheader import MessageHeader, From, To, PartyId, Service, MessageData
from finvoice.soap.msgheader import Manifest, Reference, Schema

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    # Please do not add this field to any view, as the computation is resource-intense
    # This is only to act as a helper
    invoice_number = fields.Char(
        string='Invoice number',
        compute='compute_invoice_number',
    )

    finvoice_xml = fields.Text(
        string='Finvoice XML',
        compute='compute_finvoice_xml'
    )

    def compute_invoice_number(self):
        for record in self:
            if record.number:
                record.invoice_number = re.sub(r'\D', '', record.number)

    def compute_finvoice_xml(self):
        for record in self:
            _logger.debug('Generating Finvoice for %s', self.name)

            finvoice_xml = record._get_finvoice_xml()
            record.finvoice_xml = finvoice_xml

    def _get_finvoice_object(self):

        finvoice_object = Finvoice('2.01')

        self.add_finvoice_message_transmission_details(finvoice_object)

        self.add_finvoice_seller_party_details(finvoice_object)
        self.add_finvoice_seller_information_details(finvoice_object)

        self.add_finvoice_buyer_party_details(finvoice_object)

        self.add_finvoice_delivery_party_details(finvoice_object)

        self.add_finvoice_invoice_details(finvoice_object)

        self.add_finvoice_invoice_rows(finvoice_object)

        self.add_finvoice_epi_details(finvoice_object)

        self.add_finvoice_invoice_url_name_text(finvoice_object)
        self.add_finvoice_invoice_url_text(finvoice_object)

        return finvoice_object

    def _get_finvoice_xml(self, encoding='ISO-8859-15'):
        finvoice_object = self._get_finvoice_object()
        output = StringIO.StringIO()

        finvoice_object.export(output, 0, name_='Finvoice', pretty_print=True)

        # Finvoice export doesn't support encoding in write. Add it here
        xml_declaration = "<?xml version='1.0' encoding='%s'?>\n" % encoding
        finvoice_xml = xml_declaration + output.getvalue().encode(encoding)

        return finvoice_xml

    def add_finvoice_message_transmission_details(self, finvoice_object):

        MessageSenderDetails = MessageSenderDetailsType(
            FromIdentifier=self.company_id.company_registry,  # Business id
            FromIntermediator='',
        )

        MessageSenderDetails = self._get_finvoice_message_sender_details()

        MessageReceiverDetails = self._get_finvoice_message_receiver_details()

        message_timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')

        MessageDetails = MessageDetailsType(
            MessageIdentifier=self.invoice_number,
            MessageTimeStamp=message_timestamp,
        )

        MessageTransmissionDetails = MessageTransmissionDetailsType(
            MessageSenderDetails=MessageSenderDetails,
            MessageReceiverDetails=MessageReceiverDetails,
            MessageDetails=MessageDetails,
        )

        finvoice_object.set_MessageTransmissionDetails(MessageTransmissionDetails)

    def add_finvoice_seller_party_details(self, finvoice_object):
        company = self.company_id

        SellerPostalAddressDetails = SellerPostalAddressDetailsType(
            SellerStreetName=[company.street, company.street2],
            SellerTownName=company.city,
            SellerPostCodeIdentifier=company.zip,
            CountryCode=company.country_id.code,
            CountryName=company.country_id.name,
        )

        SellerPartyDetails = SellerPartyDetailsType(
            SellerPartyIdentifier=company.company_registry,  # Business id
            SellerPartyIdentifierUrlText=company.website,
            SellerOrganisationName=[company.name],
            SellerOrganisationTaxCode=company.vat,
            SellerOrganisationTaxCodeUrlText='',
            SellerPostalAddressDetails=SellerPostalAddressDetails,
        )

        finvoice_object.set_SellerPartyDetails(SellerPartyDetails)

    def add_finvoice_seller_information_details(self, finvoice_object):
        SellerAccountID = SellerAccountIDType(
            IdentificationSchemeName='IBAN',
            valueOf_=self.partner_bank_id.acc_number,
        )
        SellerBic = SellerBicType(
            IdentificationSchemeName='BIC',
            valueOf_=self.partner_bank_id.bank_bic,
        )

        SellerAccountDetails = SellerAccountDetailsType(
            SellerAccountID=SellerAccountID,
            SellerBic=SellerBic,
        )

        SellerInformationDetails = SellerInformationDetailsType(
            SellerAccountDetails=[SellerAccountDetails],
        )

        finvoice_object.set_SellerInformationDetails(SellerInformationDetails)

    def add_finvoice_buyer_party_details(self, finvoice_object):
        partner = self.partner_id

        BuyerPostalAddressDetails = BuyerPostalAddressDetailsType(
            BuyerStreetName=[partner.street, partner.street2],
            BuyerTownName=partner.city,
            BuyerPostCodeIdentifier=partner.zip,
            CountryCode=partner.country_id.code,
            CountryName=partner.country_id.name,
        )

        BuyerPartyDetails = BuyerPartyDetailsType(
            BuyerPartyIdentifier=partner.business_id,
            BuyerOrganisationName=[partner.name],
            BuyerOrganisationDepartment='',
            BuyerOrganisationTaxCode=partner.vat,
            BuyerPostalAddressDetails=BuyerPostalAddressDetails,
        )

        finvoice_object.set_BuyerPartyDetails(BuyerPartyDetails)

    def add_finvoice_delivery_party_details(self, finvoice_object):
        partner = self.partner_shipping_id or self.partner_id

        DeliveryPostalAddressDetails = DeliveryPostalAddressDetailsType(
            DeliveryStreetName=[partner.street, partner.street2],
            DeliveryTownName=partner.city,
            DeliveryPostCodeIdentifier=partner.zip,
            CountryCode=partner.country_id.code,
            CountryName=partner.country_id.name,
        )

        DeliveryPartyDetails = DeliveryPartyDetailsType(
            DeliveryPartyIdentifier=partner.business_id,
            DeliveryOrganisationName=[partner.name],
            DeliveryPostalAddressDetails=DeliveryPostalAddressDetails,
        )

        finvoice_object.set_DeliveryPartyDetails(DeliveryPartyDetails)

    def add_finvoice_invoice_details(self, finvoice_object):

        # Normal invoices
        CodeListAgencyIdentifier = None
        TypeCode = 'INV01'
        OriginCode = 'Original'

        # Refund invoice
        if self.type == 'out_refund':
            TypeCode = 'INV02'
            CodeListAgencyIdentifier = 'SPY'
            OriginCode = 'Cancel'

        InvoiceTypeCode = InvoiceTypeCodeType(
            CodeListAgencyIdentifier=CodeListAgencyIdentifier,
            valueOf_=TypeCode,
        )

        InvoiceTotalVatExcludedAmount = amount(
            AmountCurrencyIdentifier=self.currency_id.name,
            valueOf_=self.amount_untaxed,
        )

        InvoiceTotalVatAmount = amount(
            AmountCurrencyIdentifier=self.currency_id.name,
            valueOf_=self.amount_tax,
        )

        InvoiceTotalVatIncludedAmount = amount(
            AmountCurrencyIdentifier=self.currency_id.name,
            valueOf_=self.amount_total,
        )

        # TODO: separate different VAT rates
        VatSpecificationDetails = VatSpecificationDetailsType(
            VatBaseAmount=InvoiceTotalVatExcludedAmount,
            VatRateAmount=InvoiceTotalVatAmount,
        )

        PaymentTermsDetails = PaymentTermsDetailsType(
            PaymentTermsFreeText=[self.payment_term_id.name],
            InvoiceDueDate=date('CCYYMMDD', self.get_date_unhyphenated(self.date_due)),
        )

        PaymentOverDueFineDetails = PaymentOverDueFineDetailsType(
            PaymentOverDueFineFreeText='',  # TODO
            PaymentOverDueFinePercent='',  # TODO
        )

        InvoiceDetails = InvoiceDetailsType(
            InvoiceTypeCode=InvoiceTypeCode,
            InvoiceTypeText=self.get_invoice_finvoice_type_text(TypeCode),
            OriginCode=OriginCode,
            InvoiceNumber=self.invoice_number,
            InvoiceDate=date('CCYYMMDD', self.get_date_unhyphenated(self.date_invoice)),
            OrderIdentifier=self.invoice_number,
            InvoiceTotalVatExcludedAmount=InvoiceTotalVatExcludedAmount,
            InvoiceTotalVatAmount=InvoiceTotalVatAmount,
            InvoiceTotalVatIncludedAmount=InvoiceTotalVatIncludedAmount,
            VatSpecificationDetails=[VatSpecificationDetails],
            PaymentTermsDetails=[PaymentTermsDetails],
            # PaymentOverDueFineDetails = PaymentOverDueFineDetails,
        )

        finvoice_object.set_InvoiceDetails(InvoiceDetails)

    def add_finvoice_payment_status_details(self, finvoice_object):
        # TODO: get PaymentStatusCode based on invoice payments and reconcile state

        PaymentStatusDetails = PaymentStatusDetailsType(
            PaymentStatusCode='NOTPAID',
        )

        finvoice_object.set_PaymentStatusDetails(PaymentStatusDetails)

    def add_finvoice_invoice_rows(self, finvoice_object):
        InvoiceRows = list()

        for line in self.invoice_line_ids:
            DeliveredQuantity = QuantityType(
                QuantityUnitCode=line.uom_id.name.encode('utf-8'),  # TODO: fix this in the library
                valueOf_=line.quantity,
            )

            UnitPriceAmount = amount(
                AmountCurrencyIdentifier=self.currency_id.name,
                valueOf_=line.price_unit,
            )

            RowVatExcludedAmount = amount(
                AmountCurrencyIdentifier=self.currency_id.name,
                valueOf_=(line.quantity * line.price_unit),
            )

            InvoiceRow = InvoiceRowType(
                ArticleIdentifier=line.product_id.default_code,
                ArticleName=line.product_id.name,
                DeliveredQuantity=[DeliveredQuantity],
                UnitPriceAmount=UnitPriceAmount,
                RowFreeText=[line.name],
                RowVatExcludedAmount=RowVatExcludedAmount,
            )

            InvoiceRows.append(InvoiceRow)

        finvoice_object.set_InvoiceRow([InvoiceRow])

    def add_finvoice_epi_details(self, finvoice_object):
        EpiIdentificationDetails = EpiIdentificationDetailsType(
            EpiDate=date('CCYYMMDD', datetime.datetime.now().strftime("%Y%m%d")),
        )

        EpiDetails = EpiDetailsType(
            EpiIdentificationDetails=EpiIdentificationDetails,
            EpiPartyDetails=self._get_finvoice_epi_party_details(),
            EpiPaymentInstructionDetails=self._get_finvoice_epi_payment_instruction_details(),
        )

        finvoice_object.set_EpiDetails(EpiDetails)

    def add_finvoice_invoice_url_name_text(self, finvoice_object):
        # Override this to match your need
        # finvoice_object.set_InvoiceUrlNameText('InvoiceUrlNameText value here')
        pass

    def add_finvoice_invoice_url_text(self, finvoice_object):
        # Override this to match your need
        # finvoice_object.set_InvoiceUrlText('InvoiceUrlText value here')
        pass

    def _get_finvoice_message_sender_details(self):
        MessageSenderDetails = MessageSenderDetailsType(
            FromIdentifier=self.company_id.company_registry,  # Business id
            FromIntermediator='',
        )

        return MessageSenderDetails

    def _get_finvoice_message_receiver_details(self):
        MessageReceiverDetails = MessageReceiverDetailsType(
            ToIdentifier=self.partner_id.edicode,
            ToIntermediator=self.partner_id.einvoice_operator_identifier,
        )
        return MessageReceiverDetails

    def _get_finvoice_epi_party_details(self):
        BfiEpiAccountID = EpiBfiIdentifierType(
            IdentificationSchemeName='BIC',
            valueOf_=self.partner_bank_id.bank_bic,
        )

        # Sellers bank
        EpiBfiPartyDetails = EpiBfiPartyDetailsType(
            EpiBfiIdentifier=BfiEpiAccountID,
        )

        BeneficiaryEpiAccountID = EpiAccountIDType(
            IdentificationSchemeName='IBAN',
            valueOf_=self.partner_bank_id.acc_number,
        )

        # Seller
        EpiBeneficiaryPartyDetails=EpiBeneficiaryPartyDetailsType(
            EpiNameAddressDetails=self.partner_id.name,
            EpiBei=self.company_id.company_registry,
            EpiAccountID=BeneficiaryEpiAccountID,
        )

        EpiPartyDetails = EpiPartyDetailsType(
            EpiBfiPartyDetails=EpiBfiPartyDetails,
            EpiBeneficiaryPartyDetails=EpiBeneficiaryPartyDetails,
        )

        return EpiPartyDetails

    def _get_finvoice_epi_payment_instruction_details(self):
        EpiRemittanceInfoIdentifier = EpiRemittanceInfoIdentifierType(
            IdentificationSchemeName='ISO',
            valueOf_=self.invoice_number and self.invoice_number.zfill(20)  # TODO: change to invoice ref number
        )

        EpiInstructedAmount = amount(
            AmountCurrencyIdentifier=self.currency_id.name,
            valueOf_=self.amount_total,
        )

        EpiCharge = EpiChargeType(
            ChargeOption='SHA',  # TODO: add SLEV-option for non-domestic invoices
            valueOf_='SHA',
        )

        EpiPaymentInstructionDetails = EpiPaymentInstructionDetailsType(
            EpiPaymentInstructionId=self.invoice_number,  # TODO: change this to invoice ref number and add a sequence?
            EpiRemittanceInfoIdentifier=EpiRemittanceInfoIdentifier,
            EpiInstructedAmount=EpiInstructedAmount,
            EpiCharge=EpiCharge,
            EpiDateOptionDate=date('CCYYMMDD', self.get_date_unhyphenated(self.date_due)),
        )

        return EpiPaymentInstructionDetails

    @staticmethod
    def get_invoice_finvoice_type_text(InvoiceTypeCode):
        # Returns Finvoice 2.01 InvoiceTypeText if applicable

        InvoiceTypeText = False

        InvoiceTypes = {
            'REQ01': 'TARJOUSPYYNTÖ',
            'QUO01': 'TARJOUS',
            'ORD01': 'TILAUS',
            'ORC01': 'TILAUSVAHVISTUS',
            'DEV01': 'TOIMITUSILMOITUS',
            'INV01': 'LASKU',
            'INV02': 'HYVITYSLASKU',
            'INV03': 'KORKOLASKU',
            'INV04': 'SISÄINEN LASKU',
            'INV05': 'PERINTÄLASKU',
            'INV06': 'PROFORMALASKU',
            'INV07': 'ITSELASKUTUS',
            'INV08': 'HUOMAUTUSLASKU',
            'INV09': 'SUORAMAKSU',
            'TES01': 'TESTILASKU',
            'PRI01': 'HINNASTO',
            'INF01': 'TIEDOTE',
            'DEN01': 'TOIMITUSVIRHEILMOITUS',
            'SEI01-09': 'TURVALASKU',
        }

        if InvoiceTypeCode in InvoiceTypes:
            InvoiceTypeText = InvoiceTypes[InvoiceTypeCode]

        return InvoiceTypeText

    @staticmethod
    def get_date_unhyphenated(date_string):
        # Returns unhyphenated ISO-8601 date
        # CCYY-MM-DD becomes CCYYMMDD
        # 2020-01-02 becomes 20200102

        if not date_string:
            return False

        # This only validates the format. Not if the string is actually a valid date
        iso_8601_format = re.compile('[0-9]{4}[-][0-9]{2}[-][0-9]{2}')

        if not iso_8601_format.match(date_string):
            return False

        return date_string.replace('-', '')
