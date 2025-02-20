/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MessageSeenIndicator extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    get indicatorTitle() {
        if (!this.messageSeenIndicator) {
            return '';
        }
        if (this.messageSeenIndicator.hasEveryoneSeen) {
            return this.env._t("Seen by Everyone");
        }
        if (this.messageSeenIndicator.hasSomeoneSeen) {
            const partnersThatHaveSeen = this.messageSeenIndicator.partnersThatHaveSeen.map(
                partner => partner.name
            );
            if (partnersThatHaveSeen.length === 1) {
                return _.str.sprintf(
                    this.env._t("Seen by %s"),
                    partnersThatHaveSeen[0]
                );
            }
            if (partnersThatHaveSeen.length === 2) {
                return _.str.sprintf(
                    this.env._t("Seen by %s and %s"),
                    partnersThatHaveSeen[0],
                    partnersThatHaveSeen[1]
                );
            }
            return _.str.sprintf(
                this.env._t("Seen by %s, %s and more"),
                partnersThatHaveSeen[0],
                partnersThatHaveSeen[1]
            );
        }
        if (this.messageSeenIndicator.hasEveryoneFetched) {
            return this.env._t("Received by Everyone");
        }
        if (this.messageSeenIndicator.hasSomeoneFetched) {
            const partnersThatHaveFetched = this.messageSeenIndicator.partnersThatHaveFetched.map(
                partner => partner.name
            );
            if (partnersThatHaveFetched.length === 1) {
                return _.str.sprintf(
                    this.env._t("Received by %s"),
                    partnersThatHaveFetched[0]
                );
            }
            if (partnersThatHaveFetched.length === 2) {
                return _.str.sprintf(
                    this.env._t("Received by %s and %s"),
                    partnersThatHaveFetched[0],
                    partnersThatHaveFetched[1]
                );
            }
            return _.str.sprintf(
                this.env._t("Received by %s, %s and more"),
                partnersThatHaveFetched[0],
                partnersThatHaveFetched[1]
            );
        }
        return '';
    }

    /**
     * @returns {Message}
     */
    get message() {
        return this.messaging && this.messaging.models['Message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {MessageSeenIndicator}
     */
    get messageSeenIndicator() {
        if (!this.thread || this.thread.model !== 'mail.channel') {
            return undefined;
        }
        return this.messaging.models['MessageSeenIndicator'].findFromIdentifyingData({
            message: this.message,
            thread: this.thread,
        });
    }

    /**
     * @returns {Thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['Thread'].get(this.props.threadLocalId);
    }
}

Object.assign(MessageSeenIndicator, {
    props: {
        messageLocalId: String,
        threadLocalId: String,
    },
    template: 'mail.MessageSeenIndicator',
});

registerMessagingComponent(MessageSeenIndicator);
