from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class FsmCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "fsm_count" in counters:
            partner = request.env.user.partner_id.commercial_partner_id
            values["fsm_count"] = request.env["expodo.fsm.order"].search_count(
                [("partner_id", "=", partner.id)]
            )
        return values

    @http.route(["/my/interventions", "/my/interventions/page/<int:page>"],
                type="http", auth="user", website=True)
    def portal_my_interventions(self, page=1, **kw):
        partner = request.env.user.partner_id.commercial_partner_id
        Order = request.env["expodo.fsm.order"]
        domain = [("partner_id", "=", partner.id)]
        total = Order.search_count(domain)
        pager = portal_pager(
            url="/my/interventions", total=total, page=page, step=20,
        )
        orders = Order.search(
            domain, limit=20, offset=pager["offset"], order="date_planned desc",
        )
        values = {
            "interventions": orders,
            "page_name": "intervention",
            "pager": pager,
            "default_url": "/my/interventions",
        }
        return request.render("expodo_fieldservice.portal_my_interventions", values)

    @http.route(["/my/intervention/<int:order_id>"],
                type="http", auth="user", website=True)
    def portal_my_intervention(self, order_id=None, **kw):
        try:
            order_sudo = self._document_check_access("expodo.fsm.order", order_id)
        except (AccessError, MissingError):
            return request.redirect("/my")
        return request.render(
            "expodo_fieldservice.portal_my_intervention",
            {"intervention": order_sudo, "page_name": "intervention"},
        )


from odoo.exceptions import AccessError, MissingError
