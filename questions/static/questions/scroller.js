var Questions = (function (questions_module, $) {
    questions_module.globals = questions_module.globals || {};

    questions_module.globals = $.extend(questions_module.globals, {
        minimum_screen_height: 600,
        minimium_screen_width: 800,
    });

    var container_selector = ".container.main";
    var screen_selector = container_selector + " .section";
    $.extend(questions_module.globals, {
        container_selector: container_selector,
        screen_selector: screen_selector,
        active_screen_selector: screen_selector + "." + questions_module.globals.active_class,
    });

    questions_module.PageScroller = function (options) {
        var self = this;
        var transition_time = 600;
        var current_translate = 0;

        options = $.extend({
            before_scroll: null,
            after_scroll: null,
        }, options);

        // if (document.addEventListener) {
        //     document.addEventListener('DOMMouseScroll', function (e) { e.preventDefault(); }, false);
        //     document.addEventListener('mousewheel', function (e) { e.preventDefault(); }, false);
        // } else {
        //     document.attachEvent('onmousewheel', function (e) { e.preventDefault(); }, false);
        // }

        // 33: pageup, 34: pagedown, 37: left, 38: up, 39: right, 40: down
        // to_prevent = [33, 34, 38, 40];
        // $(document).keydown(function (e) { if ($.inArray(e.keyCode, to_prevent) >= 0) { e.preventDefault(); } });
        // $(document).on('touchmove', function (e) { e.preventDefault(); });

        this.get_container = function () { return $(questions_module.globals.container_selector); };
        this.get_current_slide = function () { return $(questions_module.globals.active_screen_selector); };
        this.get_previous_slide = function (slide) { return slide.prev(questions_module.globals.screen_selector); };
        this.get_next_slide = function (slide) { return slide.next(questions_module.globals.screen_selector); };
        this.get_all_previous_slides = function (slide) { return slide.prevAll(questions_module.globals.screen_selector); };

        this.move = function(container) {
            container.css({
                "transform": "translateY(-" + current_translate + "px)",
                "-webkit-transform": "translateY(-" + current_translate + "px)",
                "-moz-transform": "translateY(-" + current_translate + "px)",
                "-o-transform": "translateY(-" + current_translate + "px)",
                "-ms-transform": "translateY(-" + current_translate + "px)"
            });
        };

        this.do_transition = function() {
            if (options.before_scroll) options.before_scroll();
            $container = self.get_container();
            $container.addClass(questions_module.globals.transition_setup_class);
            self.move($container);
            setTimeout(function () {
                $container.removeClass(questions_module.globals.transition_setup_class);
                if (options.after_scroll) options.after_scroll();
            }, transition_time);
        };

        this.set_size = function () {
            // new_height = $(window).height();
            // if (new_height < questions_module.globals.minimum_screen_height) new_height = questions_module.globals.minimum_screen_height;
            // $(questions_module.globals.screen_selector).each(function () { $(this).innerHeight(new_height); });
            // $("body").innerHeight(new_height);
        };

        this.resize = function () {
            self.set_size();
            current_translate = 0;
            $current = self.get_current_slide();
            self.get_all_previous_slides($current).each(function () {
                current_translate += $(this).innerHeight();
            });
            this.move(self.get_container());
        };

        this.forward = function () {
            $current = self.get_current_slide();
            $next = self.get_next_slide($current);
            if ($next.length === 0) { return; }
            current_translate += $current.innerHeight();
            self.do_transition(current_translate);
            $current.removeClass(questions_module.globals.active_class);
            $next.addClass(questions_module.globals.active_class);
        };

        this.back = function () {
            $current = self.get_current_slide();
            $prev = self.get_previous_slide($current);
            if ($prev.length === 0) { return; }
            current_translate -= $prev.innerHeight();
            self.do_transition(current_translate);
            $current.removeClass(questions_module.globals.active_class);
            $prev.addClass(questions_module.globals.active_class);
        };

        this.slide = function (index) {
            $current = self.get_current_slide();
            $slide = $(questions_module.globals.screen_selector + ":eq(" + (index - 1) + ")");
            current_translate = 0;
            $slide.prevAll(questions_module.globals.screen_selector).each(function () {
                current_translate += $(this).innerHeight();
            });
            self.do_transition(current_translate);
            $current.removeClass(questions_module.globals.active_class);
            $slide.addClass(questions_module.globals.active_class);
        };

        this.first = function () {
            $current = self.get_current_slide();
            $prev = self.get_previous_slide($current);
            return $prev.length === 0;
        };

        this.last = function () {
            $current = self.get_current_slide();
            $next = self.get_next_slide($current);
            return $next.length === 0;
        };

        this.current = function () {
            $current = self.get_current_slide();
            $prev = self.get_all_previous_slides($current);
            return $prev.length + 1;
        };

        $(window).resize(function () { self.resize(); });
        this.set_size();
        $(questions_module.globals.screen_selector).first().addClass(questions_module.globals.active_class);
    };

    return questions_module;
}(Questions || {}, jQuery));
