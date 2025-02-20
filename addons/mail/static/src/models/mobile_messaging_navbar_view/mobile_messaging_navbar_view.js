/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'MobileMessagingNavbarView',
    identifyingFields: [['discuss', 'messagingMenu']],
    recordMethods: {
        /**
         * @param {string} tabId
         */
        onClick(tabId) {
            if (this.discuss) {
                if (this.discuss.activeMobileNavbarTabId === tabId) {
                    return;
                }
                this.discuss.update({ activeMobileNavbarTabId: tabId });
                if (
                    this.discuss.activeMobileNavbarTabId === 'mailbox' &&
                    (!this.discuss.thread || this.discuss.thread.model !== 'mailbox')
                ) {
                    this.discuss.update({ thread: replace(this.messaging.inbox) });
                }
                if (this.discuss.activeMobileNavbarTabId !== 'mailbox') {
                    this.discuss.update({ thread: clear() });
                }
                if (this.discuss.activeMobileNavbarTabId !== 'chat') {
                    this.discuss.update({ isAddingChat: false });
                }
                if (this.discuss.activeMobileNavbarTabId !== 'channel') {
                    this.discuss.update({ isAddingChannel: false });
                }
            }
            if (this.messagingMenu) {
                this.messagingMenu.update({ activeTabId: tabId });
            }
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeActiveTabId() {
            if (this.discuss) {
                return this.discuss.activeMobileNavbarTabId;
            }
            if (this.messagingMenu) {
                return this.messagingMenu.activeTabId;
            }
            return clear();
        },
        /**
         * @private
         * @returns {Object[]}
         */
        _computeTabs() {
            if (this.discuss) {
                return [{
                    icon: 'fa fa-inbox',
                    id: 'mailbox',
                    label: this.env._t("Mailboxes"),
                }, {
                    icon: 'fa fa-user',
                    id: 'chat',
                    label: this.env._t("Chat"),
                }, {
                    icon: 'fa fa-users',
                    id: 'channel',
                    label: this.env._t("Channel"),
                }];
            }
            if (this.messagingMenu) {
                return [{
                    icon: 'fa fa-envelope',
                    id: 'all',
                    label: this.env._t("All"),
                }, {
                    icon: 'fa fa-user',
                    id: 'chat',
                    label: this.env._t("Chat"),
                }, {
                    icon: 'fa fa-users',
                    id: 'channel',
                    label: this.env._t("Channel"),
                }];
            }
            return [];
        },
    },
    fields: {
        /**
         * Tab selected in this navbar.
         * Either 'all', 'mailbox', 'chat' or 'channel'.
         */
        activeTabId: attr({
            compute: '_computeActiveTabId',
        }),
        discuss: one2one('Discuss', {
            inverse: 'mobileMessagingNavbarView',
            readonly: true,
        }),
        messagingMenu: one2one('MessagingMenu', {
            inverse: 'mobileMessagingNavbarView',
            readonly: true,
        }),
        /**
         * Ordered list of tabs that this navbar has.
         * Format of tab:
         * {
         *   icon: <the classname for this tab>
         *   id: <the id for this tab>
         *   label: <the label/name of this tab>
         * }
         */
        tabs: attr({
            compute: '_computeTabs',
        }),
    },
});
