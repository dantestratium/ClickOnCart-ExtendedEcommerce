odoo.define('extended_ecommerce.website_sale_wishlist', function (require) {
    'use strict';

    const sAnimations = require('website.content.snippets.animation');
    const wSaleUtils = require('website_sale.utils');
    const WebsiteSaleWishlist = require('website_sale_wishlist.wishlist');

    sAnimations.registry.AddToCartAjax = sAnimations.Class.extend(WebsiteSaleWishlist, {
        selector: '.oe_website_sale',
        read_events: {
                'click .ajax_add_cart': '_addToCart',
                'click .update_sticky_wishlist': '_updateStickyWishlist',
                'click .js_add_cart_json': '_updateQuantity',
                'click .scroll-to-left': '_scrollToLeft',
                'click .scroll-to-right': '_scrollToRight'
            },
        start: function () {
            $('#homeModal').modal('show')
        },
        events: sAnimations.Class.events,
        _scrollToLeft: function (e) {
            let dom = $(e.currentTarget);

            dom.parent().parent().parent().find('.coc-wrapper__more-category, .scrollable').animate({
                scrollLeft: '-=778px'
            }, 100)
        },
        _scrollToRight: function (e) {
            let dom = $(e.currentTarget);

            dom.parent().parent().parent().find('.coc-wrapper__more-category, .scrollable').animate({
                scrollLeft: '+=778px'
            }, 100)
        },
        _addToCart: function (e) {
            let btn = $(e.currentTarget);
            let qty = 1;

            $('#my_cart, #top_menu_collapse_clone #my_cart').removeClass('coc-glow__cart');
            btn.blur();
            btn.attr('disabled', 'disabled');
            btn.css('font-weight: 700;');
            btn.html('ADDING');
            btn.addClass('coc-loading');

            let productId = $(e.currentTarget).data('product-id');
            let addQty = btn.parent().parent().find('input[name=add_qty]').val();

            if (addQty > 0) {
                qty = addQty
            }

            return this._rpc({
                route: "/shop/cart/update_json",
                params: {
                    product_id: parseInt(productId, 10),
                    add_qty: qty,
                    display: false,
                },
            }).then(function (resp) {
                const cart = $('#sidecart');

                $('.my_cart_quantity').html(resp.cart_quantity);
                $('#my_cart, #top_menu_collapse_clone #my_cart').removeClass('d-none');

                $('#my_cart, #top_menu_collapse_clone #my_cart').addClass('coc-glow__cart');

                btn.removeAttr('disabled');
                btn.removeClass('coc-loading');
                btn.html('<span class="fa fa-shopping-cart" /> ADD TO CART');

                openCartNav(true);

                cart.html(resp.sidecart);

                cart.find(`input[data-product-id=${productId}]`).closest('.oe_website_sale').addClass('coc-glow__cart');
            });
        },
        _updateStickyWishlist: function () {
            $('#my_wish, #top_menu_collapse_clone #my_wish').addClass('coc-glow__wish');
            $('#top_menu_collapse_clone #my_wish').show();

            setTimeout(() => {
                $('#my_wish, #top_menu_collapse_clone #my_wish').removeClass('coc-glow__wish');
            }, 1000)
        }
    })
});
