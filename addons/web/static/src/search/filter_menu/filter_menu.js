/** @odoo-module **/

import { CustomFilterItem } from "./custom_filter_item";
import { FACET_ICONS } from "../utils/misc";
import { useBus } from "@web/core/utils/hooks";

const { Component } = owl;

export class FilterMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.filter;

        useBus(this.env.searchModel, "update", this.render);
    }

    /**
     * @returns {Object[]}
     */
    get items() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["filter", "dateFilter"].includes(searchItem.type)
        );
    }

    /**
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onFilterSelected({ itemId, optionId }) {
        if (optionId) {
            this.env.searchModel.toggleDateFilter(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }
}

FilterMenu.components = { CustomFilterItem };
FilterMenu.template = "web.FilterMenu";
