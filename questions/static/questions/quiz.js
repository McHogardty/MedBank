var Questions = (function (questions_module, $) {

    questions_module.globals =  questions_module.globals || {};

    question_attribute = "data-question";
    question_selector = "form[" + question_attribute + "]";
    active_class = questions_module.globals.active_class;
    active_question_selector = "." + active_class + " " + question_selector;
    screen_selector = ".question-screen";
    $.extend(questions_module.globals, {
        home_url: "",
        individual_question_url: "",
        quiz_attempt_url: "",
        report_url: "",
        report_results: false,
        question_element: "form",
        question_attribute: "data-question",
        question_id_attribute: "data-question-id",
        question_selector: question_selector,
        question_body_selector: ".question-body",
        active_question_selector: active_question_selector,
        question_screen_selector: screen_selector,
        question_buttons_selector: ".buttons",
        question_unanswered_text: ".question-unanswered",
        loading_screen_selector: ".loading-screen",
        questions_remaining_selector: ".questions-remaining",
        nav_selector: ".nav-down",
        current_question_number_selector: ".current-question-number",
        total_question_number_selector: ".total-question-number",
        confidence_widget_selector: ".confidence-widget",
        confidence_attribute: "data-confidence",
        option_widget_selector: ".question-options",
        option_attribute: "data-option",
        list_screen_selector: ".questions",
        list_selector: ".questions .question-list",
        timer_selector: ".timer",
        button_selector: ".btn",
        start_button_selector: ".btn-start",
        close_button_selector: ".btn-close",
        explanation_button_selector: ".btn-explanation",
        view_button_selector: ".btn-view",
        next_button_selector: ".btn-next",
        progress_button_selector: ".btn-progress",
        previous_button_selector: ".btn-previous",
        summary_button_selector: ".btn-summary",
        finish_button_selector: ".btn-finish",
        home_button_selector: ".btn-home",
        main_screen_elements: [],
        summary_form_selector: ".summary-form",
        summary_form_question_name: "question",
        summary_form_position_name: "position",
        summary_form_time_name: "time-taken",
        summary_form_answer_name: "answer",
        summary_form_confidence_name: "confidence-rating",
    });

    questions_module.QuestionTimer = function () {
        var question_timer = new questions_module.Timer({is_global: false});
        var attempted = false;
        question_timer.total = 0;

        question_timer.render_time = function () { };
        question_timer.save = function () { question_timer.total += question_timer.time_since_beginning() + question_timer.elapsed; };
        question_timer.time_taken = function () { return question_timer.total; };

        question_timer.lap = function () {
            question_timer.save();
            question_timer.complete_pause();
            attempted = true;
            question_timer.reset();
            question_timer.complete_pause();
        };

        question_timer.stop = function () {
            if (!attempted) question_timer.save();
            question_timer.complete_pause();
            question_timer.reset();
            question_timer.stop_timing();
        };

        return question_timer;
    };

    questions_module.QuestionList = function (options) {
        var self = this;

        options = $.extend({
            progress_button_callback: null,
            close_button_callback: null,
            go_to_question: null,
            elements_to_hide: [],
        }, options);

        var list_screen = new questions_module.SplashScreen({
                to_show: [questions_module.globals.list_screen_selector,],
                to_hide: questions_module.globals.main_screen_elements,
        });

        $question_list = $(questions_module.globals.list_selector);

        this.get_list_element = function (question_number) { return $question_list.find('[' + questions_module.globals.question_attribute +'="' + question_number + '"]'); };

        this.check = function (question_number, checked) {
            $current_list_item = self.get_list_element(question_number);
            $current_list_item.toggleClass(questions_module.globals.checked_button_class, checked);
            $current_list_item.toggleClass(questions_module.globals.default_button_class, !checked);
        };

        this.toggle_active = function (list_element, active) { list_element.toggleClass(questions_module.globals.active_class, active); };

        this.make_question_active = function (question_number) {
            $(questions_module.globals.list_selector).find("li" + "." + questions_module.globals.active_class).each(function (i, element) {
                self.toggle_active($(element), false);
            });

            self.toggle_active(self.get_list_element(question_number), true);
        };

        $question_list.find(questions_module.globals.button_selector).click(function (e) {
            list_screen.hide();

            $button = $(this);
            setTimeout(function () {
                options.go_to_question(parseInt($button.attr(questions_module.globals.question_attribute), 10));
            }, 600);
            e.preventDefault();
        });

        $(questions_module.globals.progress_button_selector).click(function (e) {
            if (options.progress_button_callback) options.progress_button_callback();
            list_screen.show();
            e.preventDefault();
        });

        $(questions_module.globals.list_screen_selector).find(questions_module.globals.close_button_selector).click(function (e) {
            list_screen.hide();
            if (options.close_button_callback) options.close_button_callback();
            e.preventDefault();
        });
    };

    questions_module.QuizScroller = function (options) {
        var self = this;
        this.scroller = null;
        var question_mode = "question";
        var answer_mode = "answer";
        var next_question_text = "Next question";
        var check_answer_text = "Check answer";
        this.mode = question_mode;

        var nav_viewer = new questions_module.SplashScreen({
                to_show: [questions_module.globals.nav_selector,],
        });
        nav_viewer.hide_immediately();

        $(questions_module.globals.total_question_number_selector).html(questions_module.globals.number_of_questions);
        options = $.extend({
            before_scroll: null,
            after_scroll: null,
            answer_callback: null,
        }, options);

        this.show = function () { nav_viewer.show(); };
        this.hide = function () { nav_viewer.hide(); };
        this.get_next_button = function () { return $(questions_module.globals.next_button_selector); };
        this.update_question_number = function () {
            n = parseInt($(questions_module.globals.active_question_selector).attr(questions_module.globals.question_attribute), 10) || "-";
            $(questions_module.globals.current_question_number_selector).each(function () { $(this).html(n); });
        };

        this.update_display = function () {
            self.update_question_number();
            $(questions_module.globals.previous_button_selector).prop("disabled", self.scroller.first() || (questions_module.globals.report_results && self.scroller.current() === 2));
            $(questions_module.globals.next_button_selector).prop("disabled", this.mode === question_mode && self.scroller.last());
            if (questions_module.globals.report_results) {
                $(questions_module.globals.next_button_selector).html(self.scroller.first() ? "View questions" : "Next question");
                $(".btn-summary").prop("disabled", self.scroller.first());
            }
        };

        this.after_scroll = function () {
            if (options.after_scroll) options.after_scroll();
            self.update_display();
        };

        this.toggle_report_mode = function () {
            this.mode = this.mode === question_mode ? answer_mode : question_mode;
            report = this.mode === answer_mode;
            $next_button = self.get_next_button();
            $next_button.html(report ? check_answer_text : next_question_text);
            $next_button.off('click', report ? self.forward : options.answer_callback);
            $next_button.on('click', report ? options.answer_callback : self.forward);
            this.update_display();
        };

        this.scroller = new questions_module.PageScroller({
            after_scroll: this.after_scroll,
            before_scroll: options.before_scroll
        });

        $(questions_module.globals.previous_button_selector).click(function (e) {
            self.back();
            e.preventDefault();
        });

        if (questions_module.globals.report_results) { $(questions_module.globals.next_button_selector).html("View questions"); }

        $(questions_module.globals.summary_button_selector).click(function (e) {
            self.slide(1);
            e.preventDefault();
        });

        $(questions_module.globals.home_button_selector).click(function (e) { window.location.href = questions_module.globals.home_url; });

        this.forward = function () { self.scroller.forward(); };
        this.back = function () { self.scroller.back(); };
        this.slide = function (slide_number) { self.scroller.slide(slide_number); };
        this.last = function () { return self.scroller.last() }
        this.update_display();
        $(questions_module.globals.next_button_selector).on('click', self.forward);
    };

    questions_module.SummaryFormManager = function (options) {
        var self = this;
        options = $.extend({
            question_time_calculator: null,
            question_options_choice: null,
            question_confidence_choice: null,
        }, options);

        this.build_form_name = function (question_id, suffix) {
            if (question_id) {
                return options.question_name + "-" + question_id + "-" + suffix;
            } else {
                return suffix;
            }
        };
        this.build_form_input = function (question_id, name, value) { return $('<input type="hidden"></input>').attr("name", self.build_form_name(question_id, name)).val(value); };
        this.get_form = function () { return $(questions_module.globals.summary_form_selector); };

        this.generate_form = function () {
            $summary_form = self.get_form();
            $(questions_module.globals.question_selector).each(function () {
                $question = $(this);
                question_id = $question.attr(questions_module.globals.question_id_attribute);
                question_number = parseInt($question.attr(questions_module.globals.question_attribute), 10);
                $question_input = self.build_form_input(null, questions_module.globals.summary_form_question_name, question_id);
                $position = self.build_form_input(question_id, questions_module.globals.summary_form_position_name, question_number);
                $time_taken = self.build_form_input(question_id, questions_module.globals.summary_form_time_name, options.question_time_calculator(question_number));
                $answer = self.build_form_input(question_id, questions_module.globals.summary_form_answer_name, options.question_options_choice(question_number));
                $confidence = self.build_form_input(question_id, questions_module.globals.summary_form_confidence_name, options.question_confidence_choice(question_number));

                $summary_form.append($question_input);
                $summary_form.append($position);
                $summary_form.append($time_taken);
                $summary_form.append($answer);
                $summary_form.append($confidence);
            });
        };

        this.submit = function () { self.get_form().submit(); };
    };

    questions_module.Question = function (options) {
        var self = this;
        var confidence = null;
        var question_options = null;
        var explanation = null;
        var loading_screen = null;
        this.answer = null;
        this.id = 0;
        this.marked = false;

        options = $.extend({
            selector: "",
            confidence_button_callback: null,
            option_button_callback: null,
            quiz_attempt_generator: null,
            pause_timer: null,
        }, options);

        var question = $(options.selector);
        var question_number = question.attr(questions_module.globals.question_attribute);
        loading_selector = questions_module.globals.active_screen_selector + " " + questions_module.globals.loading_screen_selector;
        loading_screen = new questions_module.SplashScreen({
            to_show: [loading_selector, ],
            to_hide: [questions_module.globals.active_screen_selector + " " + questions_module.globals.question_screen_selector, ]
        });
        loading_screen.show();
        var timer = questions_module.QuestionTimer();
        if (!questions_module.globals.report_results) {
            confidence = new questions_module.ButtonGroupWidget({
                widget: question.find(questions_module.globals.confidence_widget_selector),
                value_attr: questions_module.globals.confidence_attribute,
                click_callback: options.confidence_button_callback,
            });
            question_options = new questions_module.ButtonGroupWidget({
                widget: question.find(questions_module.globals.option_widget_selector),
                value_attr: questions_module.globals.option_attribute,
                click_callback: options.option_button_callback,
            });
        } else {
            explanation_selector = '.explanation[' + questions_module.globals.question_attribute + '="' + question_number + '"]';
            explanation = new questions_module.SplashScreen({
                to_show: [explanation_selector,],
                to_hide: questions_module.globals.main_screen_elements,
            });
            $(explanation_selector).find(questions_module.globals.close_button_selector).click(function (e) {
                explanation.hide();
                e.preventDefault();
            });
            question.find(questions_module.globals.explanation_button_selector).click(function (e) {
                explanation.show();
                e.preventDefault();
            });
        }

        this.get_element = function () { return $(options.selector); };
        this.get_parent_element = function () { return self.get_element().parents(questions_module.globals.question_screen_selector); };
        this.get_parent_element().find(questions_module.globals.question_unanswered_text).fadeOut(0);

        this.setup = function (info) {
            $element = self.get_parent_element();
            $form = $element.find("form");
            $element.attr(questions_module.globals.question_attribute, $form.attr(questions_module.globals.question_attribute));
            $element.find(questions_module.globals.question_body_selector).html(info.body);
            this.id = info.id;

            explanation_selector = '.explanation[' + questions_module.globals.question_attribute + '="' + question_number + '"]';
            $(explanation_selector).find(".explanation-body").html(info.explanation);
            $(explanation_selector).find(".btn-close").click(function () { explanation.hide(); });
            explanation = new questions_module.SplashScreen({
                to_show: [explanation_selector,],
                to_hide: [questions_module.globals.question_screen_selector + '[' + questions_module.globals.question_attribute + '="' +  question_number + '"]',],
                to_fade_out: [questions_module.globals.nav_selector,],
            });
            $element.find(questions_module.globals.explanation_button_selector).click(function () { explanation.show(); });
            $element.find(questions_module.globals.view_button_selector).click(function () { window.open(info.url, "_blank"); });
            self.answer = info.answer;
            question_options.setup(info.options, info.answer);
            $element.find(questions_module.globals.question_buttons_selector).toggle();
            loading_screen.hide();
            setTimeout(function () {
                timer.start();
                options.pause_timer();
            }, 600);
        };

        this.error_setup = function () {
            $element = $(loading_selector);
            $element.find(".loading-message").fadeOut(600);
            setTimeout(function () {
                $element.find(".error-message").fadeIn(600);
            }, 600);
        };

        this.error = function () {
            $element = $(loading_selector);
            timeout = $element.is(":visible") ? 600 : 0;

            $element.find(".loading-message").fadeOut(timeout);
            setTimeout(function () {
                $element.find(".error-message").fadeIn(timeout);
            }, timeout);

            if (!timeout) loading_screen.show();
        };

        this.option_choice = function () { return question_options.choice(); };
        this.confidence_choice = function () { return confidence.choice(); };
        this.complete = function () { return question_options.chosen() && confidence.chosen(); };

        this.start = function (number) { timer.start(); };
        this.complete_pause = function (number) { timer.complete_pause(); };
        this.paused = function (number) { return timer.paused(); };
        this.stop = function (number) { timer.stop(); };
        this.lap = function (number) { timer.lap(); };
        this.time_taken = function (number) { return timer.time_taken(); };

        this.display_answer = function (info) {
            self.get_parent_element().find(questions_module.globals.question_buttons_selector).fadeIn(600);
            question_options.mark(info.answer);
            confidence.disable();
            if (!question_options.chosen()) { self.get_parent_element().find(questions_module.globals.question_unanswered_text).fadeIn(600); }
        };

        this.get_quiz_attempt = function () { return options.quiz_attempt_generator(); };
        this.check_answer = function () {
            attempt = self.get_quiz_attempt();
            if (!attempt) return;
            $.post(questions_module.globals.question_attempt_url, {
                quiz_attempt: attempt,
                id: self.id,
                position: self.get_parent_element().attr(questions_module.globals.question_attribute),
                choice: self.option_choice(),
                confidence: self.confidence_choice(),
                time_taken: timer.time_taken(),
            })
            .done(function (data) { self.display_answer(data); });
        };

        this.mark = function () {
            //timer.stop();
            options.pause_timer();
            self.check_answer();
            self.marked = true;
        };
    };

    questions_module.QuestionManager = function (options) {
        var self = this;

        options = $.extend({
            question_selector_generator: null,
            confidence_button_callback: null,
            option_button_callback: null,
            quiz_attempt_generator: null,
            pause_timer: null,
        }, options);

        var questions = [];

        this.generate_question_selector = function (question_number) {
            if (options.question_selector_generator) {
                return options.question_selector_generator(question_number);
            } else {
                return "";
            }
        };

        this.get_question_element = function (question_number) { return $(self.generate_question_selector(question_number)); };
        this.get_active_question_element = function () { return $(questions_module.globals.active_question_selector); };
        this.get_question_elements = function () { return $(questions_module.globals.question_selector); };
        this.get_question_number = function (question) { return parseInt(question.attr(questions_module.globals.question_attribute), 10); };
        this.get_next_question_element = function (question_element) { return self.get_question_element(self.get_question_number(question_element)).eq(1); };
        this.get_active_question_number = function () { return self.get_question_number(self.get_active_question_element()); };
        this.get_question = function (index) { return questions[index - 1]; };
        this.get_active_question = function () { return self.get_question(self.get_active_question_number()); };
        this.is_question = function (element) { return element.is("[" + questions_module.globals.question_attribute + "]"); };
        this.get_answered_questions = function () {
            to_return = [];

            $.each(questions, function (i, question) { if (question.marked) to_return.push(question); });

            return to_return;
        };

        this.finish_setup = function (index, question, error) { self.get_question(index).setup(question); };
        this.error_setup = function (index) { self.get_question(index).error_setup(); };

        this.get_next_question = function (index) {
            query = {};
            if (questions_module.globals.specification) query["specification"] = questions_module.globals.specification;
            if (self.get_answered_questions()) {
                query["done"] = [];
                $.each(self.get_answered_questions(), function (i, question) { query["done"].push(question.id); });
            }
            $.get(questions_module.globals.individual_question_url, query)
            .done(function (data) { self.finish_setup(index, data, false); });
            //.fail(function () { self.error_setup(index, {}, true); });
        };

        // this.setup_next_question = function () {
        //     $current = self.get_active_question_element();
        //     if (!self.is_question($current)) {
        //         $next = self.get_question_elements().first();
        //     } else {
        //         $next = self.get_next_question_element($current);
        //     }
        //     if ($next.length === 0) { return; }
        //     index = parseInt(self.get_question_number($next), 10);
        //     questions[index - 1] = new questions_module.Question({
        //         selector: self.generate_question_selector(index),
        //         quiz_attempt_generator: options.quiz_attempt_generator,
        //     });
        //     self.get_next_question(index);
        // };

        this.setup_current_question = function () {
            $current = self.get_active_question_element();
            if (!self.is_question($current)) { return; }
            index = parseInt(self.get_question_number($current), 10);
            if (self.get_question(index)) return;
            questions[index - 1] = new questions_module.Question({
                selector: self.generate_question_selector(index),
                quiz_attempt_generator: options.quiz_attempt_generator,
                pause_timer: options.pause_timer,
                option_button_callback: options.option_button_callback,
            });
            self.get_next_question(index);
        };

        if (questions_module.globals.individual_question_url === "") {
            $(questions_module.globals.question_selector).each(function (i, element) {
                $element = $(element);
                index = parseInt(self.get_question_number($element), 10);
                questions[index - 1] = new questions_module.Question({
                    selector: self.generate_question_selector(index),
                    confidence_button_callback: options.confidence_button_callback,
                    option_button_callback: options.option_button_callback,
                });
            });
        }

        this.question = function (index) { return questions[index - 1]; };
        this.option_choice = function(question_number) { return self.question(question_number).option_choice(); };
        this.confidence_choice = function(question_number) { return self.question(question_number).confidence_choice(); };
        this.number_complete = function () {
            n = 0;
            $.each(questions, function (i, q) { n += (q.complete() ? 1 : 0); });
            return n;
        };
        this.number_remaining = function () { return questions.length - self.number_complete(); };

        this.start = function (number) { self.get_active_question().start(); };
        this.complete_pause = function (number) { self.get_active_question().complete_pause(); };
        this.paused = function (number) { return self.get_active_question().paused(); };
        this.stop = function (number) { self.get_active_question().stop(); };
        this.lap = function (number) { self.get_active_question().lap(); };
        this.time_taken = function (number) { return self.question(number).time_taken(); };
        this.mark_current_question = function () { return self.get_active_question().mark(); };
        this.error = function () { self.get_active_question().error(); };
    };

    questions_module.Quiz = function (options) {
        $.extend(questions_module.globals, options);

        quiz = this;
        var question_manager = null;
        var self = this;
        var question_list = null;
        questions_module.globals.main_screen_elements = [questions_module.globals.container_selector, ".timer", questions_module.globals.nav_selector];

        this.generate_question_selector = function (question_number) {
            selector = questions_module.globals.question_element + "[" + questions_module.globals.question_attribute;
            if (question_number) {
                selector += '="' + question_number + '"';
            }
            selector += "]";

            return selector;
        };

        var scroller = null;
        var splash = new questions_module.SplashScreen({
                to_show: [".finish",],
                to_hide: questions_module.globals.main_screen_elements,
        });

        this.option_button_callback = function () {
            $question = $(questions_module.globals.active_question_selector);
            question_list.check($question.attr(questions_module.globals.question_attribute), $question.find("button.btn-success").length > 0);
            question_manager.lap();
            self.decide_to_finish();
        };

        this.decide_to_finish = function () {
            remaining = question_manager.number_remaining();
            ready = (remaining === 0);

            $(questions_module.globals.questions_remaining_selector).html(remaining);
            $(".plural").toggle(remaining === 1);
            $(".btn-finish").toggleClass(questions_module.globals.checked_button_class, ready);
            $(".finish .text-info").toggle(!ready);
            return ready;
        };

        question_manager = new questions_module.QuestionManager({
            question_selector_generator: this.generate_question_selector,
            confidence_button_callback: self.decide_to_finish,
            option_button_callback: this.option_button_callback,
        });

        var summary_form = new questions_module.SummaryFormManager({
            question_time_calculator: question_manager.time_taken,
            question_options_choice: question_manager.option_choice,
            question_confidence_choice: question_manager.confidence_choice,
        });

        var timer = null;

        $(".btn-finish").click(function (e) {
            timer.complete_pause();
            splash.show();
            e.preventDefault();
        });
        $(".btn-return").click(function (e) {
            splash.hide();
            timer.complete_pause();
            e.preventDefault();
        });
        $(".btn-submit").click(function (e) {
            self.finish();
            e.preventDefault();
        });

        this.start = function () {
            timer.start();
            question_manager.start();
        };
        this.complete_pause = function () {
            timer.complete_pause();
            question_manager.complete_pause();
        };
        this.paused = function () { return timer.paused(); };

        this.pause_callback = function () {
            question_manager.complete_pause();
            $(questions_module.globals.container_selector).toggle(!timer.paused());
            $(questions_module.globals.nav_selector).toggle(!timer.paused());
        };

        this.progress_button_callback = function () {
            timer.complete_pause();
            question_manager.complete_pause();
        };

        this.close_button_callback = function () {
            timer.complete_pause();
            question_manager.complete_pause();
        };

        this.forward = function () { self.scroller.forward(); };
        this.before_scroll = function () {
            if (questions_module.globals.report_results) return;
            question_manager.stop(); };
        this.after_scroll = function () {
            question_list.make_question_active(question_manager.get_active_question_number());
            if (questions_module.globals.report_results) return;
            question_manager.start();
            if (timer.paused()) timer.complete_pause();
        };

        scroller = new questions_module.QuizScroller(this.before_scroll, this.after_scroll);
        timer = new questions_module.Timer({ callback: this.pause_callback});

        question_list = new questions_module.QuestionList({
            progress_button_callback: this.progress_button_callback,
            close_button_callback: self.close_button_callback,
            go_to_question: scroller.slide,
        });

        this.finish = function () {
            summary_form.generate_form();
            summary_form.submit();
        };

        question_list.make_question_active($(questions_module.globals.question_selector).attr(questions_module.globals.question_attribute));
    };

    questions_module.IndividualQuiz = function (options) {
        $.extend(questions_module.globals, options);
        var scroller = null;
        var question_manager = null;
        var attempt = null;
        var timer = null;

        $(questions_module.globals.timer_selector).fadeOut(0);
        this.generate_question_selector = function (question_number) {
            selector = questions_module.globals.question_element + "[" + questions_module.globals.question_attribute;
            if (question_number) {
                selector += '="' + question_number + '"';
            }
            selector += "]";

            return selector;
        };

        this.decide_to_finish = function () {};
        this.option_button_callback = function () {
            question_manager.lap();
            //self.decide_to_finish();
        };

        this.generate_quiz_attempt = function () {
            //alert("Attempt is " + attempt);
            if (!attempt) {
                $.ajax({
                    type: 'POST',
                    url: questions_module.globals.quiz_attempt_url,
                    async: false,
                    data: {
                        'specification': options.specification,
                    },
                    success: function (data) {
                        attempt = data.attempt;
                        questions_module.globals.report_url = data.report_url;
                    }
                });
            }
            //alert("Returning attempt " + attempt);
            return attempt;
        };

        this.pause_timer = function () {
            if (timer.running()) {
                timer.complete_pause();
            } else {
                timer.start();
            }
        };

        question_manager = new questions_module.QuestionManager({
            question_selector_generator: this.generate_question_selector,
            confidence_button_callback: this.decide_to_finish,
            option_button_callback: this.option_button_callback,
            quiz_attempt_generator: this.generate_quiz_attempt,
            pause_timer: this.pause_timer,
        });

        this.before_scroll = function () {};

        this.after_scroll = function () {
            question_manager.setup_current_question();
            scroller.toggle_report_mode();
        };

        this.mark_answer = function () {
            question_manager.mark_current_question();
            //timer.complete_pause();
            scroller.toggle_report_mode();
            if (scroller.last()) $(questions_module.globals.finish_button_selector).prop("disabled", false);
        };

        scroller = new questions_module.QuizScroller({
            before_scroll: this.before_scroll,
            after_scroll: this.after_scroll,
            answer_callback: this.mark_answer,
        });
        $(questions_module.globals.start_button_selector).click(function (e) {
            scroller.forward();
            scroller.show();
            $(questions_module.globals.timer_selector).fadeIn(600);
        });

        this.pause_callback = function () {
            question_manager.complete_pause();
            $(questions_module.globals.container_selector).toggle(!timer.paused());
            $(questions_module.globals.nav_selector).toggle(!timer.paused());
        };

        timer = new questions_module.Timer({ callback: this.pause_callback});

        $(questions_module.globals.finish_button_selector).click(function () {
            window.location.href = questions_module.globals.report_url;
        })
        .prop('disabled', true);

        this.handle_ajax_error = function () {
            question_manager.error();
            question_manager.stop();
            timer.stop_timing();
            scroller.hide();
            $(questions_module.globals.timer_selector).hide();
        };

        $(document).ajaxError(this.handle_ajax_error);
        $.ajaxSettings.traditional = true;
    };

    questions_module.IndividualQuizReport = function (options) {
        $.extend(questions_module.globals, options);
        var scroller = null;
        var explanation = null;

        scroller = new questions_module.QuizScroller();
        explanation_attributes = [];
        $(".explanation").each(function (i, element) {
            explanation_attributes.push($(element).attr(questions_module.globals.question_attribute));
        });
        explanation = new questions_module.SplashScreenManager({
            screen_class: ".explanation",
            specifying_attribute: "data-question",
            attributes: explanation_attributes,
            to_hide: [questions_module.globals.question_screen_selector,],
            to_fade_out: [questions_module.globals.nav_selector, ],
        });
        $(questions_module.globals.explanation_button_selector).click(function () {
            explanation.show($(this).parents(questions_module.globals.question_selector).attr(questions_module.globals.question_attribute));
        });
        $(questions_module.globals.close_button_selector).click(function () {
            explanation.hide($(this).parents(".explanation").attr(questions_module.globals.question_attribute));
        });
        
        $(questions_module.globals.start_button_selector).click(function () {
            scroller.forward();
            scroller.show();
        });
    };

    return questions_module;
}(Questions || {}, jQuery));
