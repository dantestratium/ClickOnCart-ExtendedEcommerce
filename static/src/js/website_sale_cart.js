odoo.define('extended_ecommerce.website_sale_cart', function (require) {
    'use strict';

    const sAnimations = require('website.content.snippets.animation');
    const WebsiteSaleCart = require('website_sale.cart');

    sAnimations.registry.sideNavCart = sAnimations.Class.extend(WebsiteSaleCart, {
        selector: '#sidecart, #my_cart, #my_category, #my_account, .new_quantity_input',
        read_events: {
            'change input.sidecart-qty[data-product-id]': '_onChangeCartQuantity',
            'click .js_delete_product': '_onClickDeleteProduct',
            'click .sidecart-toggle': '_onClickShowSidecart',
            'click .catnav-toggle': '_onClickShowCatnav',
            'click .account-toggle': '_onClickShowAccount',
            'click .js_add_cart_json': '_updateQuantity',
            'click .xjs_add_cart_json': '_updateQuantity',
        },
        _updateQuantity: function (e) {
            let btn = $(e.currentTarget);
            let $input = btn.closest('.input-group').find("input");
            let min = parseFloat($input.data("min") || 0);
            let max = parseFloat($input.data("max") || Infinity);
            let previousQty = parseFloat($input.val() || 0, 10);
            let quantity = (btn.find('.fa-minus').length ? -1 : 1) + previousQty;
            let newQty = quantity > min ? (quantity < max ? quantity : max) : min;

            if (newQty !== previousQty) {
                $input.val(newQty).trigger('change');
            }
        },
        _onClickShowSidecart: function (ev) {
            const dom = $('#sidecart');
            const notdom1 = $('#account-div');
            const notdom2 = $('#mobile-category');

            if (notdom1.hasClass('coc-sidenav__show')) {
                notdom1.removeClass('coc-sidenav__show');
                notdom1.addClass('coc-sidenav__hide');
            }

            if (notdom2.hasClass('coc-sidenav__show')) {
                notdom2.removeClass('coc-sidenav__show');
                notdom2.addClass('coc-sidenav__hide');
            }

            if (window.location.pathname === '/shop/cart') {
                return;
            }

            if (dom.hasClass('coc-sidenav__show')) {
                openCartNav();

                return;
            }

            $.get("/shop/cart", {
                type: 'sidecart',
            }).then(function (data) {
                openCartNav();

                $('#sidecart').html(data);
            });
        },
        _onClickShowCatnav: function (ev) {
            const dom = $('#mobile-category');
            const notdom1 = $('#sidecart');
            const notdom2 = $('#account-div');

            if (notdom1.hasClass('coc-sidenav__show')) {
                notdom1.removeClass('coc-sidenav__show');
                notdom1.addClass('coc-sidenav__hide');
            }

            if (notdom2.hasClass('coc-sidenav__show')) {
                notdom2.removeClass('coc-sidenav__show');
                notdom2.addClass('coc-sidenav__hide');
            }

            if (dom.hasClass('coc-sidenav__show')) {
                dom.removeClass('coc-sidenav__show');
                dom.addClass('coc-sidenav__hide');
            } else {
                dom.addClass('coc-sidenav__show');
                dom.removeClass('coc-sidenav__hide');
            }
        },
        _onClickShowAccount: function (ev) {
            const dom = $('#account-div');
            const notdom1 = $('#sidecart');
            const notdom2 = $('#mobile-category');

            if (notdom1.hasClass('coc-sidenav__show')) {
                notdom1.removeClass('coc-sidenav__show');
                notdom1.addClass('coc-sidenav__hide');
            }

            if (notdom2.hasClass('coc-sidenav__show')) {
                notdom2.removeClass('coc-sidenav__show');
                notdom2.addClass('coc-sidenav__hide');
            }

            if (dom.hasClass('coc-sidenav__show')) {
                dom.removeClass('coc-sidenav__show');
                dom.addClass('coc-sidenav__hide');
            } else {
                dom.addClass('coc-sidenav__show');
                dom.removeClass('coc-sidenav__hide');
            }
        },
        _onChangeCartQuantity: function (ev) {
            const $input = $(ev.currentTarget);
            let value = parseInt($input.val() || 0, 10);

            if (isNaN(value)) {
                value = 1;
            }

            if ($input.data('update_change')) {
                return;
            }

            const $dom = $input.closest('div.oe_website_sale');
            const line_id = parseInt($input.data('line-id'), 10);
            const productIDs = [parseInt($input.data('product-id'), 10)];

            this._changeCartQuantity($input, $dom, value, line_id, productIDs);
        },
        _changeCartQuantity: function ($input, $dom, value, line_id, productIDs) {
            $input.data('update_change', true);

            this._rpc({
                route: "/shop/cart/update_json",
                params: {
                    line_id: line_id,
                    product_id: parseInt($input.data('product-id'), 10),
                    set_qty: value
                },
            }).then(function (data) {
                $input.data('update_change', false);

                const cart = $('#sidecart');

                if (data.cart_quantity === undefined) {
                    $(".my_cart_quantity").html(0).hide().fadeIn(300);
                    openCartNav();
                }

                let check_value = parseInt($input.val() || 0, 10);

                if (isNaN(check_value)) {
                    check_value = 1;
                }
                if (value !== check_value) {
                    $input.trigger('change');

                    return;
                }

                $(".my_cart_quantity").html(data.cart_quantity).hide().fadeIn(300);
                $(".sidecart-totalqty").html(data.cart_quantity).hide().fadeIn(300);

                cart.html(data.sidecart);

                if (!data.quantity) {
                    $dom.hide().fadeIn(300).remove();
                }
            });
        },
        _onClickDeleteProduct: function (ev) {
            ev.preventDefault();
            $(ev.currentTarget).closest('div.oe_website_sale').find('.sidecart-qty').val(0).trigger('change');
        }
    })
});