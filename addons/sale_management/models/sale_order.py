# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import is_html_empty


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self, fields_list):
        default_vals = super(SaleOrder, self).default_get(fields_list)
        if "sale_order_template_id" in fields_list and not default_vals.get("sale_order_template_id"):
            company_id = default_vals.get('company_id', False)
            company = self.env["res.company"].browse(company_id) if company_id else self.env.company
            default_vals['sale_order_template_id'] = company.sale_order_template_id.id
        return default_vals

    sale_order_template_id = fields.Many2one(
        'sale.order.template', 'Quotation Template',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    sale_order_option_ids = fields.One2many(
        'sale.order.option', 'order_id', 'Optional Products Lines',
        copy=True, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

    @api.constrains('company_id', 'sale_order_option_ids')
    def _check_optional_product_company_id(self):
        for order in self:
            companies = order.sale_order_option_ids.product_id.company_id
            if companies and companies != order.company_id:
                bad_products = order.sale_order_option_ids.product_id.filtered(lambda p: p.company_id and p.company_id != order.company_id)
                raise ValidationError(_(
                    "Your quotation contains products from company %(product_company)s whereas your quotation belongs to company %(quote_company)s. \n Please change the company of your quotation or remove the products from other companies (%(bad_products)s).",
                    product_company=', '.join(companies.mapped('display_name')),
                    quote_company=order.company_id.display_name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if self.sale_order_template_id and self.sale_order_template_id.number_of_days > 0:
            default = dict(default or {})
            default['validity_date'] = fields.Date.context_today(self) + timedelta(self.sale_order_template_id.number_of_days)
        return super(SaleOrder, self).copy(default=default)

    @api.depends('partner_id', 'sale_order_template_id')
    def _compute_note(self):
        super()._compute_note()
        for order in self.filtered('sale_order_template_id'):
            template = order.sale_order_template_id.with_context(lang=order.partner_id.lang)
            order.note = template.note if not is_html_empty(template.note) else order.note

    def _compute_line_data_for_template_change(self, line):
        return {
            'display_type': line.display_type,
            'name': line.name,
            'state': 'draft',
        }

    def _compute_option_data_for_template_change(self, option):
        price = option.product_id.lst_price
        discount = 0

        if self.pricelist_id:
            pricelist_price = self.pricelist_id._get_product_price(option.product_id, 1, uom=option.uom_id)

            if self.pricelist_id.discount_policy == 'without_discount' and price:
                discount = max(0, (price - pricelist_price) * 100 / price)
            else:
                price = pricelist_price

        return {
            'product_id': option.product_id.id,
            'name': option.name,
            'quantity': option.quantity,
            'uom_id': option.uom_id.id,
            'price_unit': price,
            'discount': discount
        }

    def update_prices(self):
        self.ensure_one()
        super().update_prices()
        # Special case: we want to overwrite the existing discount on update_prices call
        # i.e. to make sure the discount is correctly reset
        # if pricelist discount_policy is different than when the price was first computed.
        self.sale_order_option_ids.discount = 0.0
        self.sale_order_option_ids._compute_price_unit()
        self.sale_order_option_ids._compute_discount()

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):

        if not self.sale_order_template_id:
            self.require_signature = self._get_default_require_signature()
            self.require_payment = self._get_default_require_payment()
            return

        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)

        # --- first, process the list of products from the template
        order_lines = [(5, 0, 0)]
        for line in template.sale_order_template_line_ids:
            data = self._compute_line_data_for_template_change(line)

            if line.product_id:
                price = line.product_id.lst_price
                discount = 0

                if self.pricelist_id:
                    pricelist_price = self.pricelist_id._get_product_price(line.product_id, 1, uom=line.product_uom_id)

                    if self.pricelist_id.discount_policy == 'without_discount' and price:
                        discount = max(0, (price - pricelist_price) * 100 / price)
                    else:
                        price = pricelist_price

                data.update({
                    'price_unit': price,
                    'discount': discount,
                    'product_uom_qty': line.product_uom_qty,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                })

            order_lines.append((0, 0, data))

        self.order_line = order_lines

        # then, process the list of optional products from the template
        option_lines = [(5, 0, 0)]
        for option in template.sale_order_template_option_ids:
            data = self._compute_option_data_for_template_change(option)
            option_lines.append((0, 0, data))

        self.sale_order_option_ids = option_lines

        if template.number_of_days > 0:
            self.validity_date = fields.Date.context_today(self) + timedelta(template.number_of_days)

        self.require_signature = template.require_signature
        self.require_payment = template.require_payment

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.sale_order_template_id and order.sale_order_template_id.mail_template_id:
                self.sale_order_template_id.mail_template_id.send_mail(order.id)
        return res

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online quote if it exists. """
        self.ensure_one()
        user = access_uid and self.env['res.users'].sudo().browse(access_uid) or self.env.user

        if not self.sale_order_template_id or (not user.share and not self.env.context.get('force_website')):
            return super(SaleOrder, self).get_access_action(access_uid)
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'self',
            'res_id': self.id,
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _description = "Sales Order Line"

    sale_order_option_ids = fields.One2many('sale.order.option', 'line_id', 'Optional Products Lines')

    @api.depends('product_id')
    def _compute_name(self):
        # Take the description on the order template if the product is present in it
        super()._compute_name()
        for line in self:
            if line.product_id and line.order_id.sale_order_template_id:
                for template_line in line.order_id.sale_order_template_id.sale_order_template_line_ids:
                    if line.product_id == template_line.product_id:
                        line.name = template_line.with_context(lang=line.order_id.partner_id.lang).name + line._get_sale_order_line_multiline_description_variants()
                        break


class SaleOrderOption(models.Model):
    _name = "sale.order.option"
    _description = "Sale Options"
    _order = 'sequence, id'

    is_present = fields.Boolean(
        string="Present on Quotation",
        compute="_compute_is_present", search="_search_is_present",
        help="This field will be checked if the option line's product is "
             "already present in the quotation.")
    order_id = fields.Many2one('sale.order', 'Sales Order Reference', ondelete='cascade', index=True)
    line_id = fields.Many2one('sale.order.line', ondelete="set null", copy=False)
    name = fields.Text(
        'Description', required=True,
        compute='_compute_name', store=True, readonly=False, precompute=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[('sale_ok', '=', True)])
    price_unit = fields.Float(
        'Unit Price', required=True, digits='Product Price',
        compute='_compute_price_unit', store=True, readonly=False, precompute=True)
    discount = fields.Float(
        'Discount (%)', digits='Discount',
        compute='_compute_discount', store=True, readonly=False, precompute=True)
    uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure ', required=True,
        compute='_compute_uom_id', store=True, readonly=False, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', readonly=True)
    quantity = fields.Float('Quantity', required=True, digits='Product Unit of Measure', default=1)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of optional products.")

    @api.depends('line_id', 'order_id.order_line', 'product_id')
    def _compute_is_present(self):
        # NOTE: this field cannot be stored as the line_id is usually removed
        # through cascade deletion, which means the compute would be false
        for option in self:
            option.is_present = bool(option.order_id.order_line.filtered(lambda l: l.product_id == option.product_id))

    def _search_is_present(self, operator, value):
        if (operator, value) in [('=', True), ('!=', False)]:
            return [('line_id', '=', False)]
        return [('line_id', '!=', False)]

    @api.depends('product_id')
    def _compute_name(self):
        for option in self:
            if not option.product_id:
                continue
            product_lang = option.product_id.with_context(lang=option.order_id.partner_id.lang)
            option.name = product_lang.get_product_multiline_description_sale()

    @api.depends('product_id')
    def _compute_uom_id(self):
        for option in self:
            if not option.product_id or option.uom_id:
                continue
            option.uom_id = option.product_id.uom_id

    @api.depends('product_id', 'uom_id', 'quantity')
    def _compute_price_unit(self):
        for option in self:
            if not option.product_id or not option.order_id.pricelist_id:
                continue
            # To compute the price_unit a so line is created in cache
            values = option._get_values_to_add_to_order()
            new_sol = self.env['sale.order.line'].new(values)
            new_sol._compute_price_unit()
            option.price_unit = new_sol.price_unit

    @api.depends('product_id', 'uom_id', 'quantity')
    def _compute_discount(self):
        for option in self:
            if not option.product_id:
                continue
            # To compute the discount a so line is created in cache
            values = option._get_values_to_add_to_order()
            new_sol = self.env['sale.order.line'].new(values)
            new_sol._compute_discount()
            option.discount = new_sol.discount

    def button_add_to_order(self):
        self.add_option_to_order()

    def add_option_to_order(self):
        self.ensure_one()

        sale_order = self.order_id

        if sale_order.state not in ['draft', 'sent']:
            raise UserError(_('You cannot add options to a confirmed order.'))

        values = self._get_values_to_add_to_order()
        order_line = self.env['sale.order.line'].create(values)

        self.write({'line_id': order_line.id})
        if sale_order:
            sale_order.add_option_to_order_with_taxcloud()


    def _get_values_to_add_to_order(self):
        self.ensure_one()
        return {
            'order_id': self.order_id.id,
            'price_unit': self.price_unit,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'discount': self.discount,
            'company_id': self.order_id.company_id.id,
        }
