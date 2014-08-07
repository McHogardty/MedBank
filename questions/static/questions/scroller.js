var Questions = (function (questions_module, $) {
    questions_module.globals = questions_module.globals || {};

    questions_module.globals = $.extend(questions_module.globals, {
        minimum_screen_height: 600,
        minimium_screen_width: 800,
        after_scroll_event: "quiz.after_scroll",
        before_scroll_event: "quiz.before_scroll",
        quiz_finish_event: "quiz.finish",
        check_answer_event: "quiz.check_answer",
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
        var moving_forward = true;

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

        this.get_event_arguments = function () {
            return [self.current(), self.total(), moving_forward];
        };

        this.do_transition = function() {
            $.event.trigger(questions_module.globals.before_scroll_event, self.get_event_arguments());
            $container = self.get_container();
            $container.addClass(questions_module.globals.transition_setup_class);
            self.move($container);
            setTimeout(function () {
                $container.removeClass(questions_module.globals.transition_setup_class);
                $.event.trigger(questions_module.globals.after_scroll_event, self.get_event_arguments());
            }, transition_time);
        };

        this.resize = function () {
            current_translate = 0;
            $current = self.get_current_slide();
            self.get_all_previous_slides($current).each(function () {
                current_translate += $(this).innerHeight();
            });
            this.move(self.get_container());
        };

        this.forward = function () {
            moving_forward = true;
            $current = self.get_current_slide();
            $next = self.get_next_slide($current);
            if ($next.length === 0) { return; }
            current_translate += $current.innerHeight();
            self.do_transition(current_translate);
            $current.removeClass(questions_module.globals.active_class);
            $next.addClass(questions_module.globals.active_class);
        };

        this.back = function () {
            moving_forward = false;
            $current = self.get_current_slide();
            $prev = self.get_previous_slide($current);
            if ($prev.length === 0) { return; }
            current_translate -= $prev.innerHeight();
            self.do_transition(current_translate);
            $current.removeClass(questions_module.globals.active_class);
            // $prev.addClass(questions_module.globals.active_class);
            $current.prev(questions_module.globals.screen_selector).addClass(questions_module.globals.active_class);
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

        this.total = function () {
            return $(questions_module.globals.screen_selector).length;
        };

        $(window).resize(function () { self.resize(); });
        $(questions_module.globals.screen_selector).first().addClass(questions_module.globals.active_class);
    };

    questions_module.NavigationController = function (options) {
        var self = this;
        this.scroller = null;
        this.position = 1;
        this.current_question_position = 1;
        this.at_end = false;

        options = $.extend({
            nav_widget_selector: ".nav-down",
            next_button_selector: ".btn-next",
            next_button_text: "Next question",
            previous_button_selector: ".btn-previous",
            finish_button_selector: ".btn-finish",
            finish_button_text: "Finish quiz",
            start_button_text: "Start quiz",
            total_question_number_selector: ".total-question-number",
            current_question_number_selector: ".current-question-number",
        }, options);

        this.update_position = function (current, total) {
            self.position = current;
            self.at_end = current === total;
            if (self.current_question_position < self.position) {
                self.current_question_position = self.position;
            }
        };

        this.get_next_button = function () {
            return $(options.nav_widget_selector).find(options.next_button_selector);
        };

        this.get_previous_button = function () {
            return $(options.nav_widget_selector).find(options.previous_button_selector);
        };

        this.get_finish_button = function () {
            return $(options.nav_widget_selector).find(options.finish_button_selector);
        };

        this.start_button_action = function () {
            $.event.trigger(questions_module.globals.quiz_start_event);
            self.scroller.forward();
        };

        this.finish_button_action = function () {
            $.event.trigger(questions_module.globals.quiz_finish_event);
        };

        this.update_question_number = function () {
            n = parseInt($(questions_module.globals.active_question_selector).attr(questions_module.globals.question_attribute), 10);
            n = n || "-";

            $(options.current_question_number_selector).html(n);
        };

        this.move_forward = function (e) {
            self.scroller.forward();
            e.preventDefault();
        };

        this.move_backward = function (e) {
            self.scroller.back();
            e.preventDefault();
        };

        this.update_next_button = function () {
            self.get_next_button().off('click.navigation', self.move_forward).on('click.navigation', self.move_forward);
        };

        this.update_previous_button = function () {
            self.get_previous_button().off('click.navigation', self.move_backward).on('click.navigation', self.move_backward);
        };

        this.update_finish_button = function () {
            var finish_button = self.get_finish_button();
            if (self.position === 1) {
                finish_button.html(options.start_button_text);
                finish_button.on('click', self.start_button_action);
                finish_button.off("click", self.finish_button_action);
            } else {
                finish_button.html(options.finish_button_text);
                finish_button.off("click", self.start_button_action);
                finish_button.on("click", self.finish_button_action);
            }
        };

        this.update_button_status = function () {
            if (self.position === 1) {
                self.disable_next_button();
                self.disable_previous_button();
            } else if (self.position === 2) {
                self.enable_next_button();
                self.disable_previous_button();
            } else if (self.at_end) {
                self.disable_next_button();
                self.enable_previous_button();
            } else {
                self.enable_next_button();
                self.enable_previous_button();
            }
        };

        this.update = function () {
            self.update_question_number();
            self.update_button_status();
            self.update_next_button();
            self.update_previous_button();
            self.update_finish_button();
        };

        this.enable_next_button = function () {
            self.get_next_button().prop("disabled", false);
        };

        this.disable_next_button = function () {
            self.get_next_button().prop("disabled", true);
        };

        this.enable_previous_button = function () {
            self.get_previous_button().prop("disabled", false);
        };

        this.disable_previous_button = function () {
            self.get_previous_button().prop("disabled", true);
        };

        this.enable_finish_button = function () {
            self.get_finish_button().prop("disabled", false);
        };

        this.disable_finish_button = function () {
            self.get_finish_button().prop("disabled", true);
        };

        this.disable = function () {
            self.disable_next_button();
            self.disable_previous_button();
            self.disable_finish_button();
        };

        this.enable = function () {
            self.enable_next_button();
            self.enable_previous_button();
            self.enable_finish_button();
        };

        this.scroller = new questions_module.PageScroller();

        this.start = function () {
            number_of_questions = $(questions_module.globals.question_selector).length;
            $(options.total_question_number_selector).html(number_of_questions || "-");

            $(document).on(questions_module.globals.before_scroll_event, function () {
                self.disable();
            });

            $(document).on(questions_module.globals.after_scroll_event, function (event, current, total, moving_forward) {
                self.enable();
                self.update_position(current, total);
                self.update();
            });

            this.update();
        };

    };

    questions_module.IndividualModeNavigationController = function (options) {
        var self = this;
        var navigation_controller = new questions_module.NavigationController(options);
        var question_mode = "question";
        var answer_mode = "answer";
        this.mode = question_mode;

        options = $.extend({
            next_question_text: "Next question",
            check_answer_text: "Check answer",
            loading_text: "Checking answer..."
        }, options);

        navigation_controller.update_button_status = function () {
            if (this.position === 1) {
                this.disable_next_button();
                this.disable_previous_button();
            } else if (this.position === 2) {
                this.enable_next_button();
                this.disable_previous_button();
            } else if (this.at_end) {
                if (self.mode === answer_mode) {
                    this.disable_next_button();
                } else if (self.mode === question_mode) {
                    this.enable_next_button();
                }
                this.enable_previous_button();
            } else {
                this.enable_next_button();
                this.enable_previous_button();
            }
        };

        navigation_controller.update_next_button = function () {
            enter_check_mode = self.mode === question_mode && navigation_controller.position === navigation_controller.current_question_position;
            next_button_text = (enter_check_mode) ? options.check_answer_text : options.next_question_text;
            next_button = this.get_next_button();
            next_button.html(next_button_text);

            on_action = (enter_check_mode) ? self.check_answer_action : self.next_question_action;
            off_action = (enter_check_mode) ? self.next_question_action : self.check_answer_action;

            next_button.off('click', on_action).off('click', off_action).on('click', on_action);
        };

        navigation_controller.start_button_action = function () {
            $.event.trigger(questions_module.globals.quiz_start_event);
            navigation_controller.scroller.forward();
            $(document).on(questions_module.globals.question_answered_event, self.set_answer_mode);
        };

        navigation_controller.start();

        this.check_answer_action = function () {
            $.event.trigger(questions_module.globals.check_answer_event);
            navigation_controller.disable_next_button();
            navigation_controller.get_next_button().html(options.loading_text);
        };

        this.next_question_action = function () {
            self.set_question_mode();
            navigation_controller.scroller.forward();
        };

        this.set_answer_mode = function () {
            self.mode = answer_mode;
            navigation_controller.update();
        };

        this.set_question_mode = function () {
            self.mode = question_mode;
            navigation_controller.update();
        };

        this.toggle_report_mode = function () {
            self.mode = self.mode === question_mode ? answer_mode : question_mode;
            navigation_controller.update();
        };

        this.get_finish_button = navigation_controller.get_finish_button;
    };

    return questions_module;
}(Questions || {}, jQuery));
