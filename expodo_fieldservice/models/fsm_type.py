from odoo import models, fields


class FsmType(models.Model):
    _name = "expodo.fsm.type"
    _description = "Field Service Intervention Type"
    _order = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Company",
        default=lambda self: self.env.company,
    )
    checklist_ids = fields.One2many(
        "expodo.fsm.type.checklist", "type_id", string="Default Checklist",
    )


class FsmTypeChecklist(models.Model):
    _name = "expodo.fsm.type.checklist"
    _description = "Field Service Type Checklist Item"
    _order = "sequence, id"

    type_id = fields.Many2one(
        "expodo.fsm.type", string="Type", required=True, ondelete="cascade",
    )
    name = fields.Char(string="Step", required=True)
    sequence = fields.Integer(default=10)
