var Questions = (function (questions_module, $) {
    questions_module.globals = questions_module.globals || {};

    questions_module.ButtonGroupWidget = function (options) {
        var self = this;
        this.current_choice = null;
        this.answer = null;

        options = $.extend({
            widget: null,
            value_attr: "",
            click_callback: null,
        }, options);

        this.buttons = function () { return options.widget.find(questions_module.globals.button_selector); };

        this.click = function (e) {
            $clicked = $(this);
            clicked_choice = $clicked.attr(options.value_attr);
            if (self.current_choice === clicked_choice) {
                self.current_choice = null;
            } else {
                self.current_choice = clicked_choice;
            }

            options.widget.find("." + questions_module.globals.checked_button_class).each(function () {
                if ($(this).attr(options.value_attr) === clicked_choice) { return; }
                self.check($(this));
            });
            self.check($clicked);
            if (options.click_callback) options.click_callback(self.current_choice, options.widget);
            e.preventDefault();
        };

        options.widget.find(questions_module.globals.button_selector).click(this.click);

        this.choice = function () { return self.current_choice; };
        this.chosen = function () { return self.current_choice !== null; };
        this.check = function(button) { button.toggleClass(questions_module.globals.default_button_class + " " + questions_module.globals.checked_button_class); };
        this.toggle_unsuccessful = function (button, force) {
            if (force === undefined) force = true;
            button.toggleClass(questions_module.globals.default_button_class, !force);
            button.toggleClass(questions_module.globals.unsuccessful_button_class, force);
        };

        this.setup = function (options_info, answer) {
            $.each(options_info.labels, function (i, label) {
                $outer_div = $('<div></div>').addClass("form-group");
                $inner_div = $('<div></div>').addClass("col-xs-offset-1");
                $button = $('<button></button>').attr("type", "button").addClass("btn btn-default btn-option").attr("data-option", label).html(label);
                $button.click(self.click);
                $span = $('<span></span>').html(options_info[label]).attr("style", "margin-left:45px;line-height:20px;display:block;padding:7px 12px;vertical-align:middle;");
                options.widget.append($outer_div.append($inner_div.append($button).append($span)));
            });

            self.answer = answer || null;
        };

        this.disable = function () {
            options.widget.find(questions_module.globals.button_selector)
                .addClass('btn-no-hover')
                .off('click');
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

        this.mark = function (answer) {
            self.answer = answer;
            self.buttons().addClass(questions_module.globals.transition_setup_class);
            $answer_button = options.widget.find('[' + options.value_attr + '="' + self.answer + '"]');
            if (self.current_choice !== self.answer) {
                options.widget.find('[' + options.value_attr + '="' + self.current_choice + '"]').each(function () {
                    self.check($(this));
                    self.toggle_unsuccessful($(this));
                    self.add_icon($(this), "glyphicon-remove");
                });
                self.check($answer_button);
            }

            self.add_icon($answer_button, "glyphicon-ok");
            this.disable();
        };

        this.is_correct = function () { return self.current_choice === self.answer; };
    };

    return questions_module;
}(Questions || {}, jQuery));
