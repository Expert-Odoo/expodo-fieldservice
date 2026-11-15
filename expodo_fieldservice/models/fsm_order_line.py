from odoo import models, fields, api


class FsmOrderLineTime(models.Model):
    _name = "expodo.fsm.order.line.time"
    _description = "Field Service Time Line"
    _order = "id"

    order_id = fields.Many2one(
        "expodo.fsm.order", string="Order", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Description")
    product_id = fields.Many2one(
        "product.product", string="Service", required=True,
        domain="[('type', '=', 'service')]",
    )
    hours = fields.Float(string="Hours", default=1.0)
    price_unit = fields.Float(string="Unit Price")
    price_subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, string="Subtotal",
    )
    currency_id = fields.Many2one(
        related="order_id.currency_id", store=True, string="Currency",
    )

    @api.depends("hours", "price_unit")
    def _compute_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.hours * rec.price_unit

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
            if not self.name:
                self.name = self.product_id.display_name


class FsmOrderLinePart(models.Model):
    _name = "expodo.fsm.order.line.part"
    _description = "Field Service Part Line"
    _order = "id"

    order_id = fields.Many2one(
        "expodo.fsm.order", string="Order", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Description")
    product_id = fields.Many2one(
        "product.product", string="Product", required=True,
    )
    quantity = fields.Float(string="Quantity", default=1.0)
    price_unit = fields.Float(string="Unit Price")
    price_subtotal = fields.Monetary(
        compute="_compute_subtotal", store=True, string="Subtotal",
    )
    currency_id = fields.Many2one(
        related="order_id.currency_id", store=True, string="Currency",
    )

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.price_unit

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
            if not self.name:
                self.name = self.product_id.display_name


class FsmOrderTask(models.Model):
    _name = "expodo.fsm.order.task"
    _description = "Field Service Checklist Task"
    _order = "sequence, id"

    order_id = fields.Many2one(
        "expodo.fsm.order", string="Order", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Step", required=True)
    sequence = fields.Integer(default=10)
    done = fields.Boolean(string="Done")
