# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, fields, models


class StockPackageLevel(models.Model):
    _name = 'stock.package_level'
    _description = 'Stock Package Level'
    _check_company_auto = True

    package_id = fields.Many2one(
        'stock.quant.package', 'Package', required=True, check_company=True,
        domain="[('location_id', 'child_of', parent.location_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True)
    move_ids = fields.One2many('stock.move', 'package_level_id')
    move_line_ids = fields.One2many('stock.move.line', 'package_level_id')
    location_id = fields.Many2one('stock.location', 'From', compute='_compute_location_id', check_company=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'To', check_company=True,
        domain="[('id', 'child_of', parent.location_dest_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    is_done = fields.Boolean('Done', compute='_compute_is_done', inverse='_set_is_done')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Reserved'),
        ('new', 'New'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ],string='State', compute='_compute_state')
    is_fresh_package = fields.Boolean(compute='_compute_fresh_pack')

    picking_type_code = fields.Selection(related='picking_id.picking_type_code')
    show_lots_m2o = fields.Boolean(compute='_compute_show_lot')
    show_lots_text = fields.Boolean(compute='_compute_show_lot')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True)

    @api.depends('move_line_ids', 'move_line_ids.qty_done')
    def _compute_is_done(self):
        for package_level in self:
            # If it is an existing package
            if package_level.is_fresh_package:
                package_level.is_done = True
            else:
                package_level.is_done = package_level._check_move_lines_map_quant_package(package_level.package_id, 'qty_done')

    def _set_is_done(self):
        for package_level in self:
            if package_level.is_done:
                if not package_level.is_fresh_package:
                    ml_update_dict = defaultdict(float)
                    for quant in package_level.package_id.quant_ids:
                        corresponding_ml = package_level.move_line_ids.filtered(lambda ml: ml.product_id == quant.product_id and ml.lot_id == quant.lot_id)
                        if corresponding_ml:
                            ml_update_dict[corresponding_ml[0]] += quant.quantity
                        else:
                            corresponding_move = package_level.move_ids.filtered(lambda m: m.product_id == quant.product_id)[:1]
                            self.env['stock.move.line'].create({
                                'location_id': package_level.location_id.id,
                                'location_dest_id': package_level.location_dest_id.id,
                                'picking_id': package_level.picking_id.id,
                                'product_id': quant.product_id.id,
                                'qty_done': quant.quantity,
                                'product_uom_id': quant.product_id.uom_id.id,
                                'lot_id': quant.lot_id.id,
                                'package_id': package_level.package_id.id,
                                'result_package_id': package_level.package_id.id,
                                'package_level_id': package_level.id,
                                'move_id': corresponding_move.id,
                                'owner_id': quant.owner_id.id,
                            })
                    for rec, quant in ml_update_dict.items():
                        rec.qty_done = quant
            else:
                package_level.move_line_ids.filtered(lambda ml: ml.reserved_qty == 0).unlink()
                package_level.move_line_ids.filtered(lambda ml: ml.reserved_qty != 0).write({'qty_done': 0})

    @api.depends('move_line_ids', 'move_line_ids.package_id', 'move_line_ids.result_package_id')
    def _compute_fresh_pack(self):
        for package_level in self:
            if not package_level.move_line_ids or all(ml.package_id and ml.package_id == ml.result_package_id for ml in package_level.move_line_ids):
                package_level.is_fresh_package = False
            else:
                package_level.is_fresh_package = True

    @api.depends('move_ids', 'move_ids.state', 'move_line_ids', 'move_line_ids.state')
    def _compute_state(self):
        for package_level in self:
            if not package_level.move_ids and not package_level.move_line_ids:
                package_level.state = 'draft'
            elif not package_level.move_line_ids and package_level.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                package_level.state = 'confirmed'
            elif package_level.move_line_ids and not package_level.move_line_ids.filtered(lambda ml: ml.state == 'done'):
                if package_level.is_fresh_package:
                    package_level.state = 'new'
                elif package_level._check_move_lines_map_quant_package(package_level.package_id, 'reserved_uom_qty'):
                    package_level.state = 'assigned'
                else:
                    package_level.state = 'confirmed'
            elif package_level.move_line_ids.filtered(lambda ml: ml.state =='done'):
                package_level.state = 'done'
            elif package_level.move_line_ids.filtered(lambda ml: ml.state == 'cancel') or package_level.move_ids.filtered(lambda m: m.state == 'cancel'):
                package_level.state = 'cancel'
            else:
                package_level.state = 'draft'

    def _compute_show_lot(self):
        for package_level in self:
            if any(ml.product_id.tracking != 'none' for ml in package_level.move_line_ids):
                if package_level.picking_id.picking_type_id.use_existing_lots or package_level.state == 'done':
                    package_level.show_lots_m2o = True
                    package_level.show_lots_text = False
                else:
                    if self.picking_id.picking_type_id.use_create_lots and package_level.state != 'done':
                        package_level.show_lots_m2o = False
                        package_level.show_lots_text = True
                    else:
                        package_level.show_lots_m2o = False
                        package_level.show_lots_text = False
            else:
                package_level.show_lots_m2o = False
                package_level.show_lots_text = False

    def _generate_moves(self):
        for package_level in self:
            if package_level.package_id:
                for quant in package_level.package_id.quant_ids:
                    self.env['stock.move'].create({
                        'picking_id': package_level.picking_id.id,
                        'name': quant.product_id.display_name,
                        'product_id': quant.product_id.id,
                        'product_uom_qty': quant.quantity,
                        'product_uom': quant.product_id.uom_id.id,
                        'location_id': package_level.location_id.id,
                        'location_dest_id': package_level.location_dest_id.id,
                        'package_level_id': package_level.id,
                        'company_id': package_level.company_id.id,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        package_levels = super().create(vals_list)
        for package_level, vals in zip(package_levels, vals_list):
            if vals.get('location_dest_id'):
                package_level.move_line_ids.write({'location_dest_id': vals['location_dest_id']})
                package_level.move_ids.write({'location_dest_id': vals['location_dest_id']})
        return package_levels

    def write(self, vals):
        result = super(StockPackageLevel, self).write(vals)
        if vals.get('location_dest_id'):
            self.mapped('move_line_ids').write({'location_dest_id': vals['location_dest_id']})
            self.mapped('move_ids').write({'location_dest_id': vals['location_dest_id']})
        return result

    def unlink(self):
        self.mapped('move_ids').write({'package_level_id': False})
        self.mapped('move_line_ids').write({'result_package_id': False})
        return super(StockPackageLevel, self).unlink()

    def _check_move_lines_map_quant_package(self, package, field):
        return package._check_move_lines_map_quant(self.move_line_ids, field)

    @api.depends('package_id', 'state', 'is_fresh_package', 'move_ids', 'move_line_ids')
    def _compute_location_id(self):
        for pl in self:
            if pl.state == 'new' or pl.is_fresh_package:
                pl.location_id = False
            elif pl.package_id:
                pl.location_id = pl.package_id.location_id
            elif pl.state == 'confirmed' and pl.move_ids:
                pl.location_id = pl.move_ids[0].location_id
            elif pl.state in ('assigned', 'done') and pl.move_line_ids:
                pl.location_id = pl.move_line_ids[0].location_id
            else:
                pl.location_id = pl.picking_id.location_id

    def action_show_package_details(self):
        self.ensure_one()
        view = self.env.ref('stock.package_level_form_edit_view')

        return {
            'name': _('Package Content'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.package_level',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'flags': {'mode': 'readonly'},
        }
