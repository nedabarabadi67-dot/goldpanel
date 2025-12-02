$(function() {
    "use strict";

    $.sidebarMenu = function(menu) {
        var animationSpeed = 300,
            subMenuSelector = '.sidebar-submenu';

        $(menu).on('click', 'li a', function(e) {
            var $this = $(this);
            var checkElement = $this.next();

            if (checkElement.is(subMenuSelector) && checkElement.is(':visible')) {
                checkElement.slideUp(animationSpeed, function() {
                    checkElement.removeClass('menu-open');
                });
                checkElement.parent("li").removeClass("active");
            }
            else if ((checkElement.is(subMenuSelector)) && (!checkElement.is(':visible'))) {
                var parent = $this.parents('ul').first();
                var ul = parent.find('ul:visible').slideUp(animationSpeed);
                ul.removeClass('menu-open');

                var parent_li = $this.parent("li");

                checkElement.slideDown(animationSpeed, function() {
                    checkElement.addClass('menu-open');
                    parent.find('li.active').removeClass('active');
                    parent_li.addClass('active');

                    // RTL adjustment: move the submenu to left/right if needed
                    // فقط در صورتی که CSS شما از left/right استفاده کرده است
                    if ($('html').attr('dir') === 'rtl') {
                        checkElement.css('left', 'auto');
                        checkElement.css('right', '100%');
                    }
                });
            }

            if (checkElement.is(subMenuSelector)) {
                e.preventDefault();
            }
        });
    }

});
