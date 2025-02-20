/** @odoo-module **/

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/mobile_messaging_navbar_view/mobile_messaging_navbar_view';

patchRecordMethods('MobileMessagingNavbarView', {
    /**
     * @override
     */
    _computeTabs() {
        const res = this._super();
        if (this.messaging.pinnedLivechats.length > 0) {
            return [...res, {
                icon: 'fa fa-comments',
                id: 'livechat',
                label: this.env._t("Livechat"),
            }];
        }
        return res;
    },
});
