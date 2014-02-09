var Questions = (function (questions_module, $) {
    questions_module.PageScroller = function (container_selector, screen_selector, active_class, active_screen_selector, transition_class) {
        var self = this;
        var transition_time = 600;

        if (document.addEventListener) {
            document.addEventListener('DOMMouseScroll', function (e) { e.preventDefault(); }, false);
            document.addEventListener('mousewheel', function (e) { e.preventDefault(); }, false);
        } else {
            document.attachEvent('onmousewheel', function (e) { e.preventDefault(); }, false);
        }

        // 33: pageup, 34: pagedown, 37: left, 38: up, 39: right, 40: down
        to_prevent = [33, 34, 38, 40];
        $(document).keydown(function (e) {
            if ($.inArray(e.keyCode, to_prevent) >= 0) { e.preventDefault(); }
        });
        $(document).on('touchmove', function (e) { e.preventDefault(); });

        this.move = function(diff) {
            $(container_selector).css({
                "transform": "translateY(-" + diff + "px)",
                "-webkit-transform": "translateY(-" + diff + "px)",
                "-moz-transform": "translateY(-" + diff + "px)",
                "-o-transform": "translateY(-" + diff + "px)",
                "-ms-transform": "translateY(-" + diff + "px)"
            });
        };

        this.do_transition = function(diff) {
            $(container_selector).addClass(transition_class);
            self.move(diff);
            setTimeout(function () {
                $(container_selector).removeClass(transition_class);
            }, transition_time);
        };

        this.set_size = function () {
            $(screen_selector).each(function () {
                $(this).height($(window).height());
            });
        };

        this.resize = function () {
            self.set_size();
            current_translate = 0;
            $current = $(active_screen_selector);
            $current.prevAll(screen_selector).each(function () {
                current_translate += $(this).height();
            });
            this.move(current_translate);
        };

        this.forward = function () {
            $current = $(active_screen_selector);
            $next = $current.next(screen_selector);
            if ($next.length === 0) { return; }
            current_translate += $current.height();
            self.do_transition(current_translate);
            $current.removeClass(active_class);
            $next.addClass(active_class);
        };
        this.back = function () {
            $current = $(active_screen_selector);
            $prev = $current.prev(screen_selector);
            if ($prev.length === 0) { return; }
            current_translate -= $prev.height();
            self.do_transition(current_translate);
            $current.removeClass(active_class);
            $prev.addClass(active_class);
        };

        $(window).resize(function () {
            self.resize();
        });

        this.set_size();
    };

    return questions_module;
}(Questions || {}, jQuery));
