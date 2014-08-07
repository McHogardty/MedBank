var Questions = (function (questions_module, $) {

    questions_module.globals =  questions_module.globals || {};

    var question_selector = ".question-screen";
    var active_selector = ".active";
    var active_question_selector = active_selector + " " + question_selector;
    questions_module.globals = $.extend(questions_module.globals, {
        question_attribute: "data-question",
        question_selector: question_selector,
        active_question_selector: active_question_selector,
        loading_screen_selector: ".loading-screen",
        finish_screen_selector: ".finish-screen",
        quiz_error_event: "quiz.error",
        quiz_complete_event: "quiz.complete",
        quiz_incomplete_event: "quiz.incomplete",
        quiz_start_event: "quiz.start",
        quiz_pause_event: "quiz.pause",
        quiz_resume_event: "quiz.resume",
        quiz_ready_event: "quiz.ready",
        question_option_selected_event: "quiz.option_selected",
        question_answered_event: "quiz.question_answered",
    });

    questions_module.QuestionOptionsWidget = function (options) {
        var self = this;
        this.button_group_widget = null;
        this.answer = null;

        options = $.extend({
            value_attr: "data-option",
        }, options);

        self.button_group_widget = new questions_module.ButtonGroupWidget(options);

        self.button_group_widget.post_click_action = function () { $.event.trigger(questions_module.globals.question_option_selected_event); };

        this.setup = function (options_info, answer) {
            $.each(options_info.labels, function (i, label) {
                $outer_div = $('<div></div>').addClass("form-group");
                $inner_div = $('<div></div>').addClass("col-xs-offset-1");
                $button = $('<button></button>').attr("type", "button").addClass("btn btn-default btn-option").attr(options.value_attr, label).html(label);
                $button.on("click", self.button_group_widget.click);
                $span = $('<span></span>').html(options_info[label]).attr("style", "margin-left:45px;line-height:20px;display:block;padding:7px 12px;vertical-align:middle;");
                options.widget.append($outer_div.append($inner_div.append($button).append($span)));
            });

            self.answer = answer || null;
        };

        this.mark = function (answer) {
            self.answer = answer;
            self.button_group_widget.buttons().addClass(questions_module.globals.transition_setup_class);
            $answer_button = options.widget.find('[' + options.value_attr + '="' + self.answer + '"]');
            if (self.button_group_widget.current_choice !== self.answer) {
                options.widget.find('[' + options.value_attr + '="' + self.button_group_widget.current_choice + '"]').each(function () {
                    self.button_group_widget.check($(this));
                    self.toggle_unsuccessful($(this));
                    self.add_icon($(this), "glyphicon-remove");
                });
                self.button_group_widget.check($answer_button);
            }

            self.add_icon($answer_button, "glyphicon-ok");
            self.button_group_widget.disable();
        };

        this.is_correct = function () { return self.button_group_widget.current_choice === self.answer; };

        this.toggle_unsuccessful = function (button, force) {
            if (force === undefined) force = true;
            button.toggleClass(questions_module.globals.default_button_class, !force);
            button.toggleClass(questions_module.globals.unsuccessful_button_class, force);
        };

        this.add_icon = function ($button, glyphicon_class) {
            $icon = $("<i></i>").addClass("glyphicon pull-right").addClass(glyphicon_class).addClass("blur");
            $button.html($icon);
            $icon = $button.find(".glyphicon");
            $icon.addClass(questions_module.globals.transition_setup_class);
            $icon.removeClass(questions_module.globals.transition_class);
            setTimeout(function () {
                $icon.removeClass(questions_module.globals.transition_setup_class);
            }, 600);
        };

        this.buttons = self.button_group_widget.buttons;
        this.click = self.button_group_widget.click;
        this.choice = self.button_group_widget.choice;
        this.chosen = self.button_group_widget.chosen;
        this.check = this.button_group_widget.check;
        this.disable = self.button_group_widget.disable;
        this.set_choice = self.button_group_widget.set_choice;
    };

    questions_module.ConfidenceWidget = function (options) {
        var self = this;
        this.button_group_widget = null;

        options = $.extend({
            value_attr: "data-confidence",
        }, options);

        this.button_group_widget = new questions_module.ButtonGroupWidget(options);
        this.buttons = this.button_group_widget.buttons;
        this.click = this.button_group_widget.click;
        this.choice = this.button_group_widget.choice;
        this.chosen = this.button_group_widget.chosen;
        this.check = this.button_group_widget.check;
        this.disable = this.button_group_widget.disable;
        this.set_choice = this.button_group_widget.set_choice;
    };

    questions_module.Question = function (options) {
        var self = this;
        this.selector = "";
        this.question_number = 0;
        this.id = 0;
        this.options_widget = null;
        this.confidence_widget = null;
        this.answer = "";
        this.timer = null;
        this.explanation_element = null;
        this.complete = false;

        options = $.extend({
            question_element: null,
            question_body_selector: ".question-body",
            option_widget_selector: ".question-options",
            confidence_widget_selector: ".confidence-widget",
        }, options);

        this.question_number = parseInt(options.question_element.attr(questions_module.globals.question_attribute), 10);
        this.selector = questions_module.globals.question_selector + "[" + questions_module.globals.question_attribute + '="' + this.question_number + '"]';
        this.add_details = function (question_info) {
            this.id = question_info["id"];
            $(this.selector).find(options.question_body_selector).html(question_info["body"]);

            this.options_widget = new questions_module.QuestionOptionsWidget({
                widget: $(this.selector).find(options.option_widget_selector)
            });
            this.options_widget.setup(question_info["options"]);

            this.confidence_widget = new questions_module.ConfidenceWidget({
                widget: $(this.selector).find(options.confidence_widget_selector),
            });

            this.timer = new questions_module.Timer({is_global: false, });
            this.unanswered_text = new questions_module.SplashScreen({to_show: [this.selector + " .question-unanswered",], });
            this.unanswered_text.hide_immediately();
            buttons_selector = this.selector + " .buttons";
            this.buttons_element = $(buttons_selector);
            this.buttons = new questions_module.SplashScreen({to_show: [buttons_selector, ], });
            this.buttons.hide_immediately();

            explanation_selector = '.explanation-screen[' +  questions_module.globals.question_attribute + '="' + this.question_number + '"]';
            this.explanation_element = $(explanation_selector);
            this.explanation = new questions_module.SplashScreen({to_show: [explanation_selector,], });
            this.explanation.hide_immediately();

            this.buttons_element.find(".btn-explanation").click(function () {
                self.explanation.show();
            });
            this.explanation_element.find(".btn-close").click(function () {
                self.explanation.hide();
            });
            if (question_info.completed) {
                this.options_widget.set_choice(question_info.choice);
                this.confidence_widget.set_choice(question_info.confidence_rating);
                this.display_answer(question_info, false);
            }
        };

        this.display_answer = function (data, display_nicely) {
            self.completed = data.completed;
            self.answer = data.answer;
            if (!self.options_widget.chosen()) {
                if (display_nicely) {
                    self.unanswered_text.show();
                } else {
                    self.unanswered_text.show_immediately();
                }
            }
            self.options_widget.mark(self.answer);
            self.confidence_widget.disable();

            $explanation_list = $("<ol></ol>").addClass("alpha");
            $.each(data.explanation.labels, function (index, label) {
                if (data.explanation[label] !== "") {
                    $list_option = $("<li>" + data.explanation[label] + "</li>");
                } else {
                    $list_option = $('<li><span class="loading">Explanation was not provided.</span></li>');
                }
                $explanation_list.append($list_option);
            });
            this.explanation_element.find(".explanation").append($explanation_list);

            this.buttons.show();

            $.event.trigger(questions_module.globals.question_answered_event, [self.question_number, ]);
        };

        this.check_answer = function () {
            params = { "question_id": self.id, };

            if (self.options_widget.chosen()) params["choice"] = self.options_widget.choice();
            if (self.confidence_widget.chosen()) params["confidence_rating"] = self.confidence_widget.choice();
            params["time_taken"] = self.timer.total;
            $.post(questions_module.globals.question_submission_url, params)
                .done(function (data) {
                    if (data["status"] === "success") {
                        self.display_answer(data);
                    } else {
                        $.event.trigger(questions_module.globals.quiz_error_event);
                    }

                })
                .fail(function (data) {
                    $.event.trigger(questions_module.globals.quiz_error_event);
                });
        };

        this.answered = function () { return self.answer !== ""; };
    };

    questions_module.QuestionManager = function (options) {
        var self = this;
        this.questions = [];

        this.add_question = function (question) { self.questions[question.question_number - 1] = question; };
        this.get_question = function (question_number) { return self.questions[question_number - 1]; };
        this.get_question_number = function (question_element) { return question_element.attr(questions_module.globals.question_attribute);};
        this.get_current_question_element = function () { return $(questions_module.globals.active_question_selector); };
        this.get_current_question_number = function () { return self.get_question_number(self.get_current_question_element()); };
        this.get_current_question = function () {
            return self.get_question(self.get_current_question_number());
        };
        
        this.add_question_details = function (question_details) {
            $.each(question_details, function (i, question_info) {
                question = self.get_question(question_info.position);
                if (typeof question === 'undefined') $.event.trigger(questions_module.globals.quiz_error_event);
                question.add_details(question_info);
            });

            $.event.trigger(questions_module.globals.quiz_ready_event);
        };

        this.setup_questions = function () {
            $(questions_module.globals.question_selector).each(function () {
                question_element = $(this);
                question = new questions_module.Question({question_element: question_element});
                if (self.get_question(question.question_number)) return;
                self.add_question(question);
            });

            $.get(questions_module.globals.all_questions_url)
                .done(function (data) {
                    if (data["status"] === "success") {
                        self.add_question_details(data["questions"]);
                    } else {
                        $.event.trigger(questions_module.globals.quiz_error_event);
                    }
                })
                .fail(function (data) {
                    $.event.trigger(questions_module.globals.quiz_error_event);
                });
        };

        this.check_current_question = function () {
            question = self.get_current_question();
            question.timer.pause();
            question.check_answer();
        };

        this.question_incomplete = function (question) {
            return !question.answered();
        };

        this.update_questions_remaining = function () {
            questions_remaining_number_selector = ".questions-remaining-number";
            var count = 0;

            $.each(self.questions, function (index, question) {
                if (self.question_incomplete(question)) {
                    count += 1;
                }
            });

            $(questions_remaining_number_selector).html(count);

            if (count === 0) {
                $.event.trigger(questions_module.globals.quiz_complete_event);
            } else {
                $.event.trigger(questions_module.globals.quiz_incomplete_event);
            }
        };

        $(document).on(questions_module.globals.before_scroll_event, function () {
            question = self.get_current_question();
            if (typeof question === "undefined") return;

            if (question.timer.running()) {
                question.timer.pause();
            }
        });

        $(document).on(questions_module.globals.quiz_pause_event, function () {
            question = self.get_current_question();
            if (!question.answered() & question.timer.running()) {
                question.timer.pause();
            }
        });
        $(document).on(questions_module.globals.quiz_resume_event, function () {
            question = self.get_current_question();
            if (!question.answered() & !question.timer.running()) {
                question.timer.resume();
            }
        });
        $(document).on(questions_module.globals.after_scroll_event, function () {
            question = self.get_current_question();
            if (!question.complete) {
                if (!question.timer.has_started()) {
                    question.timer.start();
                } else if (question.timer.paused()) {
                    question.timer.resume();
                }
            }
        });
        $(document).on(questions_module.globals.quiz_finish_event, function () {
            question = self.get_current_question();
            if (!question.timer.paused()) {
                question.timer.pause();
                $(document).one(questions_module.globals.reactivate_pause, function () {
                    question.timer.resume();
                });
            }
        });
        $(document).on(questions_module.globals.check_answer_event, self.check_current_question);
        $(document).on(questions_module.globals.question_answered_event, function () {self.update_questions_remaining(); });
        $(document).on(questions_module.globals.question_option_selected_event, function () {
            question = self.get_current_question();
            if (question.timer.running()) {
                question.timer.lap();
            }
            self.update_questions_remaining();
        });

        this.setup_questions();
        this.update_questions_remaining();
    };

    questions_module.PresetQuiz = function (options) {
        var self = this;

        $.extend(questions_module.globals, options);
        var question_manager = null;
        var ready_to_finish = true;

        var finish_screen = new questions_module.SplashScreen({ to_show: [questions_module.globals.finish_screen_selector, ], });
        var error_screen = new questions_module.SplashScreen({ to_show: [".error-screen", ], });
        var pause_screen = new questions_module.SplashScreen({ to_show: [".pause-screen", ], });
        var timer_screen = new questions_module.SplashScreen({ to_show: [".timer", ], });
        var loading_screen = new questions_module.SplashScreen({ to_show: [questions_module.globals.loading_screen_selector, ], });
        var navigation_controller = new questions_module.IndividualModeNavigationController();
        var timer = new questions_module.Timer();

        finish_screen.hide_immediately();
        error_screen.hide_immediately();
        pause_screen.hide_immediately();
        timer_screen.hide_immediately();


        this.finish = function () { window.location.href = questions_module.globals.finish_url; };
        $(questions_module.globals.finish_screen_selector).find(".btn-finish").click(this.finish);

        $(document).on(questions_module.globals.quiz_error_event, function () { error_screen.show(); });
        $(document).on(questions_module.globals.quiz_pause_event, function () { pause_screen.show_immediately(); });
        $(document).on(questions_module.globals.quiz_resume_event, function () { pause_screen.hide_immediately(); });
        $(document).one(questions_module.globals.quiz_start_event, function () { timer_screen.show(); });
        $(document).one(questions_module.globals.quiz_ready_event, function () {loading_screen.hide(); });
        $(document).on(questions_module.globals.quiz_complete_event, function () { ready_to_finish = true; });
        $(document).on(questions_module.globals.quiz_incomplete_event, function () { ready_to_finish = false; });
        $(document).on(questions_module.globals.after_scroll_event, function () {
            if (question_manager.get_current_question().answered()) {
                $.event.trigger(questions_module.globals.deactivate_pause);
                $.event.trigger(questions_module.globals.question_answered_event);
            } else {
                if (timer.has_started()) {
                    timer.resume();
                } else {
                    timer.start();
                }
                $.event.trigger(questions_module.globals.reactivate_pause);
            }
        });
        $(document).on(questions_module.globals.check_answer_event, function () {
            $.event.trigger(questions_module.globals.deactivate_pause);
            timer.pause();
        });
        $(document).on(questions_module.globals.quiz_finish_event, function () {
            if (ready_to_finish) return self.finish();

            $.event.trigger(questions_module.globals.deactivate_pause);
            var is_paused = timer.paused();
            if (!is_paused) {
                timer.pause();
            }
            $(questions_module.globals.finish_screen_selector).find(".btn-return").one('click', function () {
                finish_screen.hide();
                window.setTimeout(function () {
                    if (!is_paused) {
                        timer.resume();
                    }
                    $.event.trigger(questions_module.globals.reactivate_pause);
                }, 600);
            });
            finish_screen.show();
        });
        question_manager = new questions_module.QuestionManager();
    };

    questions_module.SubmissionManager = function (options) {
        var self = this;
        var form_element = $(".submission-form");

        this.get_prefix = function () {
            return "question";
        };

        this.build_input_name = function (question_id, attribute) {
            return self.get_prefix() + "-" + question_id + "-" + attribute;
        };

        this.add_question_info = function (question_info) {
            question_id = $('<input type="hidden" />');
            question_id.attr('value', question_info.question_id);
            question_id.attr("name", self.get_prefix());

            choice = $('<input type="hidden" />');
            choice.attr("name", self.build_input_name(question_info.question_id, "choice"));
            choice.attr("value", question_info.choice);

            confidence_rating = $('<input type="hidden" />');
            confidence_rating.attr("name", self.build_input_name(question_info.question_id, "confidence_rating"));
            confidence_rating.attr("value", question_info.confidence_rating);

            time_taken = $('<input type="hidden" />');
            time_taken.attr("name", self.build_input_name(question_info.question_id, "time_taken"));
            time_taken.attr("value", question_info.time_taken);

            form_element.append(question_id);
            form_element.append(choice);
            form_element.append(confidence_rating);
            form_element.append(time_taken);
        };

        this.submit = function () {
            form_element.submit();
        };
    };

    questions_module.ClassicQuiz = function (options) {
        $.extend(questions_module.globals, options);
        var self = this;

        var ready_to_finish = true;
        var question_manager = null;
        var loading_screen = new questions_module.SplashScreen({ to_show: [questions_module.globals.loading_screen_selector, ], });
        var error_screen = new questions_module.SplashScreen({ to_show: [".error-screen", ], });
        var pause_screen = new questions_module.SplashScreen({ to_show: [".pause-screen", ], });
        var finish_screen = new questions_module.SplashScreen({ to_show: [questions_module.globals.finish_screen_selector, ], });
        var submission_manager = new questions_module.SubmissionManager();
        var timer_screen = new questions_module.SplashScreen({ to_show: [".timer", ], });
        var timer = new questions_module.Timer();
        var navigation_controller = new questions_module.NavigationController();

        error_screen.hide_immediately();
        pause_screen.hide_immediately();
        finish_screen.hide_immediately();
        timer_screen.hide_immediately();

        this.finish = function () {
            $.each(question_manager.questions, function (index, question) {
                question_info = {
                    question_id: question.id,
                    choice: question.options_widget.choice() || "",
                    confidence_rating: question.confidence_widget.choice() || "",
                    time_taken: question.timer.total,
                };
                submission_manager.add_question_info(question_info);
            });
            submission_manager.submit();
        };

        $(questions_module.globals.finish_screen_selector).find(".btn-finish").click(function () {
            self.finish();
        });

        $(document).on(questions_module.globals.quiz_error_event, function () { error_screen.show(); });
        $(document).one(questions_module.globals.quiz_ready_event, function () { loading_screen.hide(); });
        $(document).on(questions_module.globals.quiz_pause_event, function () { pause_screen.show_immediately(); });
        $(document).on(questions_module.globals.quiz_resume_event, function () { pause_screen.hide_immediately(); });
        $(document).on(questions_module.globals.quiz_complete_event, function () { ready_to_finish = true; });
        $(document).on(questions_module.globals.quiz_incomplete_event, function () { ready_to_finish = false; });
        $(document).one(questions_module.globals.quiz_start_event, function () { timer_screen.show(); });
        $(document).one(questions_module.globals.after_scroll_event, function () {
            timer.start();
        });
        $(document).on(questions_module.globals.quiz_finish_event, function () {
            if (ready_to_finish) return self.finish();

            $.event.trigger(questions_module.globals.deactivate_pause);
            var is_paused = timer.paused();
            if (!is_paused) {
                timer.pause();
            }
            $(questions_module.globals.finish_screen_selector).find(".btn-return").one('click', function () {
                 finish_screen.hide();
                 window.setTimeout(function () {
                     if (!is_paused) {
                         timer.resume();
                     }
                     $.event.trigger(questions_module.globals.reactivate_pause);
                 }, 600);
            });
            finish_screen.show();
        });

        navigation_controller.start();
        question_manager = new questions_module.QuestionManager();
        question_manager.question_incomplete = function (question) {
            return !question.options_widget.chosen();
        };
    };

    return questions_module;
}(Questions || {}, jQuery));
