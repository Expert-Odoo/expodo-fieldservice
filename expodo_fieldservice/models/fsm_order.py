from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class FsmOrder(models.Model):
    _name = "expodo.fsm.order"
    _description = "Field Service Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_planned desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda self: _("New"),
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True,
        ondelete="restrict", tracking=True,
    )
    partner_shipping_id = fields.Many2one(
        "res.partner", string="Intervention Site",
        help="Address where the intervention takes place.",
    )
    fsm_type_id = fields.Many2one(
        "expodo.fsm.type", string="Intervention Type", tracking=True,
    )
    stage_id = fields.Many2one(
        "expodo.fsm.stage", string="Stage", tracking=True,
        ondelete="restrict", index=True,
        group_expand="_read_group_stage_ids",
        default=lambda self: self._default_stage_id(),
    )
    is_closed = fields.Boolean(related="stage_id.is_closing", store=True)
    technician_id = fields.Many2one(
        "res.users", string="Technician", tracking=True, index=True,
    )
    date_planned = fields.Datetime(string="Planned Date", tracking=True)
    date_start = fields.Datetime(string="Start")
    date_end = fields.Datetime(string="End")
    duration = fields.Float(
        string="Duration (h)", compute="_compute_duration", store=True,
    )
    line_time_ids = fields.One2many(
        "expodo.fsm.order.line.time", "order_id", string="Time",
    )
    line_part_ids = fields.One2many(
        "expodo.fsm.order.line.part", "order_id", string="Parts",
    )
    task_ids = fields.One2many(
        "expodo.fsm.order.task", "order_id", string="Checklist",
    )
    amount_time = fields.Monetary(
        compute="_compute_amounts", store=True, string="Labour",
    )
    amount_parts = fields.Monetary(
        compute="_compute_amounts", store=True, string="Parts Amount",
    )
    amount_total = fields.Monetary(
        compute="_compute_amounts", store=True, string="Total",
    )
    move_id = fields.Many2one(
        "account.move", string="Invoice", readonly=True, copy=False,
    )
    invoice_state = fields.Selection(
        [("to_invoice", "To Invoice"), ("invoiced", "Invoiced")],
        string="Invoicing", default="to_invoice",
        compute="_compute_invoice_state", store=True,
    )
    signature = fields.Binary(string="Customer Signature", attachment=True)
    signed_by = fields.Char(string="Signed By")
    signed_on = fields.Datetime(string="Signed On")
    note = fields.Html(string="Notes")
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Low"), ("2", "High"), ("3", "Urgent")],
        string="Priority", default="0", index=True,
    )
    color = fields.Integer(string="Color Index")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", string="Currency", store=True,
    )

    def _default_stage_id(self):
        return self.env["expodo.fsm.stage"].search([], order="sequence, id", limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        return self.env["expodo.fsm.stage"].search([], order="sequence, id")

    @api.depends("date_start", "date_end")
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end > rec.date_start:
                delta = rec.date_end - rec.date_start
                rec.duration = delta.total_seconds() / 3600.0
            else:
                rec.duration = 0.0

    @api.depends(
        "line_time_ids.price_subtotal", "line_part_ids.price_subtotal",
    )
    def _compute_amounts(self):
        for rec in self:
            rec.amount_time = sum(rec.line_time_ids.mapped("price_subtotal"))
            rec.amount_parts = sum(rec.line_part_ids.mapped("price_subtotal"))
            rec.amount_total = rec.amount_time + rec.amount_parts

    @api.depends("move_id", "move_id.state")
    def _compute_invoice_state(self):
        for rec in self:
            if rec.move_id and rec.move_id.state != "cancel":
                rec.invoice_state = "invoiced"
            else:
                rec.invoice_state = "to_invoice"

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and not self.partner_shipping_id:
            self.partner_shipping_id = self.partner_id

    @api.onchange("fsm_type_id")
    def _onchange_fsm_type_id(self):
        if self.fsm_type_id:
            tasks = [(5, 0, 0)]
            for item in self.fsm_type_id.checklist_ids:
                tasks.append((0, 0, {"name": item.name, "sequence": item.sequence}))
            self.task_ids = tasks

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == _("New"):
                company_id = vals.get("company_id") or self.env.company.id
                seq = self.env["ir.sequence"].with_company(company_id).next_by_code(
                    "expodo.fsm.order"
                )
                vals["name"] = seq or _("New")
        return super().create(vals_list)

    def action_start(self):
        for rec in self:
            if not rec.date_start:
                rec.date_start = fields.Datetime.now()

    def action_finish(self):
        for rec in self:
            if not rec.date_end:
                rec.date_end = fields.Datetime.now()

    def action_invoice(self):
        self.ensure_one()
        if self.move_id and self.move_id.state != "cancel":
            raise UserError(_("This intervention is already invoiced."))
        if not self.line_time_ids and not self.line_part_ids:
            raise UserError(_("Add time or part lines before invoicing."))
        lines = []
        for t in self.line_time_ids:
            lines.append((0, 0, {
                "product_id": t.product_id.id,
                "name": t.name or (t.product_id.display_name or _("Labour")),
                "quantity": t.hours,
                "price_unit": t.price_unit,
            }))
        for p in self.line_part_ids:
            lines.append((0, 0, {
                "product_id": p.product_id.id,
                "name": p.name or p.product_id.display_name,
                "quantity": p.quantity,
                "price_unit": p.price_unit,
            }))
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "invoice_origin": self.name,
            "invoice_line_ids": lines,
        })
        self.move_id = move.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }

    addons_promo_html = fields.Html(
        string="Add-ons", compute="_compute_addons_promo_html", sanitize=False,
    )

    def _compute_addons_promo_html(self):
        import odoo.release
        series = "%s.0" % odoo.release.version_info[0]
        addons = [
            ("Service Team", "Put several technicians on one intervention.", "expodo_fsm_team"),
            ("Quotation before work", "Send a quote, turn it into an intervention once approved.", "expodo_fsm_sale"),
            ("Planning &amp; Dispatch", "Schedule and assign your team from one board.", "expodo_fsm_planning"),
            ("Service Contracts", "Recurring maintenance raised automatically.", "expodo_fsm_contract"),
            ("Parts &amp; Stock", "Pull parts straight from inventory.", "expodo_fsm_stock"),
            ("Online Booking", "Let customers request a visit from your website.", "expodo_fsm_portal_booking"),
            ("Timesheets", "Log time into Odoo Timesheets, no double entry.", "expodo_fsm_timesheet"),
        ]
        rows = ""
        for name, benefit, tech in addons:
            rows += (
                '<div class="d-flex align-items-center py-2 border-bottom">'
                '<div class="fw-bold" style="flex:0 0 32%%;">' + name + '</div>'
                '<div class="text-muted flex-grow-1 px-3">' + benefit + '</div>'
                '<div><a class="btn btn-sm btn-secondary" target="_blank" '
                'href="https://apps.odoo.com/apps/modules/' + series + '/' + tech + '">View on Odoo Apps</a></div>'
                '</div>'
            )
        html = (
            '<div class="alert alert-info" style="margin-bottom:16px;">'
            'These paid add-ons extend Expodo Field Service. Each one installs on top of this engine and works across every trade.'
            '</div>' + rows
        )
        for rec in self:
            rec.addons_promo_html = html
