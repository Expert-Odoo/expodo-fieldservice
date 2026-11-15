from odoo import models, fields


class FsmStage(models.Model):
    _name = "expodo.fsm.stage"
    _description = "Field Service Stage"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string="Folded in Kanban")
    is_closing = fields.Boolean(
        string="Closing Stage",
        help="Interventions in this stage are considered done.",
    )
