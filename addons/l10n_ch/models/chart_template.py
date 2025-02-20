# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    # Write paperformat and report template used on company
    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        if self == self.env.ref('l10n_ch.l10nch_chart_template'):
            company.write({
                'external_report_layout_id': self.env.ref('l10n_din5008.external_layout_din5008').id,
                'paperformat_id': self.env.ref('l10n_din5008.paperformat_euro_din').id
            })
        return res
