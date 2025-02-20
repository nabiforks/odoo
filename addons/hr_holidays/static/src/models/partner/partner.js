/** @odoo-module **/

import { addFields, addRecordMethods, patchModelMethods, patchRecordMethods } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/partner/partner';

import { str_to_date } from 'web.time';

patchModelMethods('Partner', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('out_of_office_date_end' in data) {
            data2.outOfOfficeDateEnd = data.out_of_office_date_end ? data.out_of_office_date_end : clear();
        }
        return data2;
    },
});

addRecordMethods('Partner', {
    /**
     * @private
     */
    _computeOutOfOfficeText() {
        if (!this.outOfOfficeDateEnd) {
            return clear();
        }
        if (!this.messaging.locale || !this.messaging.locale.language) {
            return clear();
        }
        const currentDate = new Date();
        const date = str_to_date(this.outOfOfficeDateEnd);
        const options = { day: 'numeric', month: 'short' };
        if (currentDate.getFullYear() !== date.getFullYear()) {
            options.year = 'numeric';
        }
        const localeCode = this.messaging.locale.language.replace(/_/g, '-');
        const formattedDate = date.toLocaleDateString(localeCode, options);
        return _.str.sprintf(this.env._t("Out of office until %s"), formattedDate);
    },
});

patchRecordMethods('Partner', {
    /**
     * @override
     */
    _computeIsOnline() {
        if (['leave_online', 'leave_away'].includes(this.im_status)) {
            return true;
        }
        return this._super();
    },
});

addFields('Partner', {
    /**
     * Date of end of the out of office period of the partner as string.
     * String is expected to use Odoo's date string format
     * (examples: '2011-12-01' or '2011-12-01').
     */
    outOfOfficeDateEnd: attr(),
    /**
     * Text shown when partner is out of office.
     */
    outOfOfficeText: attr({
        compute: '_computeOutOfOfficeText',
    }),
});
