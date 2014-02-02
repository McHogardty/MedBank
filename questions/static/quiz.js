var Questions = (function (questions_module, $) {

    var block_details = [];
    var to_hide = null;
    var base_questions_url = "";
    var quiz = null;
    var report_results = false;


    questions_module.Timer = function (callback) {
        this.start_time = 0;
        this.elapsed = 0;
        this.is_paused = false;
        var self = this;
        this.timer_id = 0;

        $(".timer button").unbind("click");
        $(".timer button").click(function (e) {
            $b = $(this);
            self.complete_pause();
            if (callback) { callback(); };
            if (self.is_paused) {
                $b.html("Resume");
            } else {
                $b.html("Pause");
            }
            e.preventDefault();
        });

        this.paused = function () { return self.is_paused; };

        this.complete_pause = function () {
            if (self.is_paused) {
                self.restart();
            } else {
                self.elapsed += self.time_since_beginning();
            }
            self.is_paused = !self.is_paused;
        };
        
        this.reset = function () {
            self.elapsed = 0;
            self.restart();
        };

        this.restart = function () { self.start_time = new Date().getTime(); };

        this.time_since_beginning = function () {
            if (self.paused()) return 0;

            return new Date().getTime() - self.start_time;
        };

        this.start = function () {
            self.reset();
            timer_id = window.setInterval(self.check_time, 100);
            self.is_paused = false;
        };

        this.stop_timing = function () {
            window.clearInterval(timer_id);
            timer_id = 0;
        };

        this.render_time = function (time) {
            $h = $('.timer h1');
            time = Math.round(Math.floor(time/100)/10);
            minutes = Math.floor(time/60);
            s = "";
            if (minutes < 10) s += "0";
            s += minutes;
            s += ":";
            seconds = time % 60;
            if (seconds < 10) s += "0";
            s += seconds % 60;
            $h.html(s);
        };

        this.check_time = function () {
            if (self.is_paused) return;

            diff = self.time_since_beginning() + self.elapsed;
            self.render_time(diff);
        };
    };

    questions_module.QuestionTimer = function () {
        var question_timer = new questions_module.Timer();
        var attempted = false;
        question_timer.total = 0;


        question_timer.render_time = function () { };

        question_timer.save = function () {
            question_timer.total += question_timer.time_since_beginning() + question_timer.elapsed;
        };

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

        question_timer.time_taken = function () {
            return question_timer.total;
        };

        return question_timer;
    };

    questions_module.QuestionTimerManager = function (question_selector, active_selector, question_attribute) {
        var self = this;

        var question_timers = [$(question_selector).length];

        $(question_selector).each(function (i, element) {
            $element = $(element);
            index = parseInt($element.attr(question_attribute));
            question_timers[index] = questions_module.QuestionTimer();
        });

        this.active_question_timer = function () {
            $active_question = $(active_selector);
            index = parseInt($active_question.attr(question_attribute));
            return question_timers[index];
        };

        this.get_question = function (number) { return question_timers[number]; };
        this.start = function () { self.active_question_timer().start(); };
        this.complete_pause = function () { self.active_question_timer().complete_pause(); };
        this.paused = function () { return self.active_question_timer().paused(); };
        this.stop = function () { self.active_question_timer().stop(); };
        this.lap = function () { self.active_question_timer().lap(); };
        this.time_taken = function (number) { return self.get_question(number).time_taken(); };

    };

    questions_module.ConfidenceWidget = function (widget, default_class, checked_class, value_attr) {
        var self = this;

        widget.find(".btn").click(function (e) {
            $clicked = $(this);
            widget.find("." + checked_class).each(function () {
                if ($(this).attr(value_attr) === $clicked.attr(value_attr)) {
                    return;
                }
                self.check($(this));
            });
            self.check($clicked);
        });

        this.choice = function () {
            return widget.find(".btn-success").attr(value_attr);
        };

        this.check = function(button) {
            button.toggleClass(default_class + " " + checked_class);
        };

    };

    questions_module.ConfidenceManager = function (widget_selector, question_selector, question_attribute, value_attr) {
        var widgets = [$(widget_selector).length];
        var self = this;

        this.default_class = "btn-default";
        this.checked_class = "btn-success";
        this.value_attr = value_attr || "data-confidence";


        $(widget_selector).each(function (i, element) {
            $element = $(element);
            index = parseInt($element.parents(question_selector).attr(question_attribute));
            widgets[index] = new questions_module.ConfidenceWidget($element, self.default_class, self.checked_class, self.value_attr);
        });

        this.choice = function(question_number) {
            return widgets[question_number].choice();
        };
    };

    questions_module.QuestionOptionsManager = function (widget_selector, question_selector, question_attribute) {
        var options_manager = new questions_module.ConfidenceManager(widget_selector, question_selector, question_attribute, "data-option");

        return options_manager;
    };


    questions_module.QuestionList = function (question_selector) {
        var self = this;
        // This attribute is used to make the button a particular colour during report mode, depending on how the user answered.
        var report_type_attribute = "data-type";
        var report_type_selector = "[" + report_type_attribute + "]";
        var default_class = "btn-default";
        var active_class = "btn-active";
        var active_selector = "." + active_class;
        var good_class = "btn-success";

        this.class_from_type = function ($li) {
            return "btn-" + $li.attr(report_type_attribute);
        };

        this.make_list_active = function ($li) {
            if ($li.is(report_type_selector)) {
                $li.removeClass(self.class_from_type($li));
            }
            $li.addClass(active_class + " " + default_class);
            $li.removeClass(good_class);
        };

         this.unmake_list_active = function ($li) {
            if ($li.is(report_type_selector)) {
                $li.removeClass(default_class);
                $li.addClass(self.class_from_type($li));
            }
            $li.removeClass(active_class);
        };

        this.make_list_successful = function ($li) {
            $li.addClass(good_class);
            $li.removeClass(active_class);
        };

        this.make_active = function () {
            self.unmake_list_active($("." + active_class));

            if (!report_results) {
                $(question_selector).each(function () {
                    if ($(this).find(".btn-success").length > 0) {
                        self.make_list_successful($('li[data-question="' + $(this).attr("data-question") + '"]'));
                    }
                });
            }
            self.make_list_active($('li[data-question="' + $(".active").find("form").attr("data-question") + '"]'));


            if ($(".active").hasClass("last")) {
                $(".btn-next").attr("disabled", "disabled");
            } else {
                $(".btn-next").removeAttr("disabled");
            }
            if ($(".active").hasClass("first") || $(".active form").attr("data-question") == 1) {
                $(".btn-previous").attr("disabled", "disabled");
            } else {
                $(".btn-previous").removeAttr("disabled");
            }

            if (report_results) {
                if ($(".active").hasClass("first")) {
                    $(".btn-summary").attr("disabled", "disabled");
                } else {
                    $(".btn-summary").removeAttr("disabled");
                }
            }
        };
        if (report_results) {
            $("li[data-type]").each(function () {
                $(this).addClass("btn-" + $(this).attr("data-type"));
            });
        }


        $("li.btn").click(function (e) {
            quiz.hide_progress();

            $button = $(this);
            setTimeout(function () {
                quiz.slide(parseInt($button.attr("data-question"), 10));
            }, 600);
            e.preventDefault();
        });
    };

    questions_module.QuizScroller = function (active_selector, question_attribute, before_scroll, after_scroll) {
        var self = this;
        next_button_selector = ".btn-next";
        previous_button_selector = ".btn-previous";
        summary_button_selector = ".summary";

        $.fn.fullpage({
            css3: true,
            resize: false,
            verticalCentered: false,
            afterLoad: function (anchorLink, index) {
                if (after_scroll) after_scroll();
                self.update_question_number();
                if (report_results) {
                    if (index > 1) {
                        $(next_button_selector).html("Next question");
                    } else {
                        $(next_button_selector).html("View questions");
                    }
                }
            },
            manual: false,
        });

        $(previous_button_selector).click(function (e) {
            self.back();
            e.preventDefault();
        });

        if (report_results) {
            $(next_button_selector).html("View questions");
        }
        $(next_button_selector).click(function (e) {
            self.forward();
            e.preventDefault();
        });

        $(summary_button_selector).click(function (e) {
            self.slide(1);
            e.preventDefault();
        });

        this.forward = function () {
            if (before_scroll) before_scroll();
            $.fn.fullpage.moveSlideDown();
        };
        this.back = function () {
            if (before_scroll) before_scroll();
            $.fn.fullpage.moveSlideUp();
        };
        this.slide = function (slide_number) {
            if (before_scroll) before_scroll();
            $.fn.fullpage.moveToSlide(slide_number);
        };
        this.update_question_number = function () {
            n = $(active_selector).attr(question_attribute);
            if (n === 0) n = "-";
            $(".question-number").each(function () { $(this).html(n); });
        };

        self.update_question_number();
    };

    questions_module.Quiz = function (report) {
        report_results = report;
        quiz = this;
        var self = this;
        question_attr = "data-question";
        question_selector = "form[" + question_attr + "]";
        active_question_selector = ".active " + question_selector;
        main_screen_elements = [".active", ".timer", ".nav-down"];

        var scroller = null;
        var splash = new questions_module.SplashScreen([".finish",], main_screen_elements);
        var explanation = new questions_module.SplashScreen(["",], ["",]);
        var progress = new questions_module.SplashScreen([".questions"], main_screen_elements);
        var question_timer = new questions_module.QuestionTimerManager(question_selector, active_question_selector, question_attr);
        var question_list = new questions_module.QuestionList();
        var confidence_widget = new questions_module.ConfidenceManager(".confidence-widget", question_selector, question_attr);
        var options_widget = questions_module.QuestionOptionsManager(".question-options", question_selector, question_attr);
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
        $(".btn-progress").click(function (e) {
            timer.complete_pause();
            question_timer.stop();
            progress.show();
            e.preventDefault();
        });
        $(".btn-close").click(function (e) {
            progress.hide();
            timer.complete_pause();
            e.preventDefault();
        });
        $(".btn-submit").click(function (e) {
            self.finish();
            e.preventDefault();
        });
        $(".btn-home").click(function (e) {
            window.location.href = "{% url 'dashboard' %}";
            e.preventDefault();
        });
        $(".btn-explanation").click(function () {
            $b = $(this);
            $d = $b.parents("div.scroller");
            show_explanation($d.find(".explanation"));
            return false;
        });

        this.hide = function () {
            $(".active").css({visibility: "hidden", });
            $(".nav-down").css({visibility: "hidden", });
        };
        this.show = function () {
            $(".active").css({visibility: "visible", });
            $(".nav-down").css({visibility: "visible", });
        };

        this.start = function () {
            timer.start();
            question_timer.start();
        };
        this.complete_pause = function () {
            timer.complete_pause();
            question_timer.complete_pause();
        }
        this.paused = function () { return timer.paused(); };
        this.start_question = function () { question_timer.start(); };
        this.complete_pause_question = function () { question_timer.complete_pause(); };
        this.stop_question = function () { question_timer.stop(); };
        this.lap_question = function () { question_timer.lap(); };

        this.pause_callback = function () {
            self.complete_pause_question();
            if (timer.paused()) {
                self.hide();
            } else {
                self.show();
            }
        };
        this.forward = function () { self.scroller.forward() };
        this.before_scroll = function () { self.stop_question(); };
        this.after_scroll = function () {
            self.start_question();
            question_list.make_active();
            if (self.paused()) {
                timer.complete_pause();
            }
        };
        this.slide = function (number) { scroller.slide(number); };
        this.hide_progress = function () { progress.hide(); };

        scroller = new questions_module.QuizScroller(active_question_selector, question_attr, this.before_scroll, this.after_scroll);
        timer = new questions_module.Timer(this.pause_callback);

        this.decide_to_finish = function () {
            remaining = $(question_selector).length - $("form[data-question] .question-options .btn.btn-success").length;
            ready = (remaining === 0);

            $(".question-remaining").html(remaining);
            if (remaining == 1) {
                $(".plural").hide();
            } else {
                $(".plural").show();
            }
            if (!ready) {
                $(".btn-finish").removeClass("btn-success");
                return ready;
            }
            $(".finish .text-info").hide();
            $(".btn-finish").addClass("btn-success");
            return ready;
        };

        this.finish = function () {
            $summary_form = $(".summary-form");
            $("form[data-question]").each(function () {
                $f = $(this);
                $('input[name="question-' + $f.attr("data-question-id") + '-answer"]').val($f.find(".btn-success").attr("data-option"));
                question_number = parseInt($f.attr("data-question"));
                $('input[name="question-' + $f.attr("data-question-id") + '-time-taken"]').val(question_timer.time_taken(question_number));
                $('input[name="question-' + $f.attr("data-question-id") + '-confidence-rating"]').val(confidence_widget.choice(question_number));
            });
            $summary_form.submit();
        };

        this.uncheck = function (button) {
            button.removeClass("btn-success");
            button.html(button.attr("data-option"));
        };

        this.check = function(button) {
            $icon = $('<i class="glyphicon glyphicon-ok pull-right" style="line-height:20px;top:-1px;"></i>');
            $b.html($icon);
            $b.toggleClass("btn-success");
        };

        this.unmake_list_active = function ($li) { question_list.unmake_list_active($li) ;};
        this.make_list_active = function ($li) { question_list.make_list_active($li) ;};
        this.make_list_successful = function ($li) { question_list.make_list_successful($li) ;};
        this.make_active = function () { question_list.make_active(); };
        this.make_active();

        $(".btn-option").click(function () {
            $f = $(this).parents("form[data-question]");
            $l = $('.questions ol li[data-question="' + $f.attr("data-question") + '"]');
            if ($f.find("button.btn-success").length > 0) {
                $l.addClass("btn-success");
                $l.removeClass("btn-default btn-active");
            } else {
                $l.removeClass("btn-success");
                $l.addClass("btn-default");
                self.make_active();
            }
            self.lap_question();
            self.decide_to_finish();
        });
    };

    return questions_module;
}(Questions || {}, jQuery));
