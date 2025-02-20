# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase


@tagged("post_install", "-at_install")
class WebSuite(HttpCase):
    def setUp(self):
        super().setUp()
        env = self.env(user=self.env.ref('base.user_admin'))
        self.main_pos_config = env.ref('point_of_sale.pos_config_main')

    def test_pos_js(self):
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.open_session_cb()

        # point_of_sale desktop test suite
        self.browser_js("/pos/ui/tests?mod=web", "", "", login="admin", timeout=1800)
