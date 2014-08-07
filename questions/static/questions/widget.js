var Questions = (function (questions_module, $) {
    questions_module.globals = questions_module.globals || {};

    questions_module.ButtonGroupWidget = function (options) {
        var self = this;
        this.current_choice = null;
        this.answer = null;

        options = $.extend({
            widget: null,
            checked_button_class: "btn-success",
            default_button_class: "btn-default",
            value_attr: "data-option",
        }, options);

        this.buttons = function () { return options.widget.find(questions_module.globals.button_selector); };

        this.post_click_action = function () {};

        this.click = function (e) {
            $clicked = $(this);
            clicked_choice = $clicked.attr(options.value_attr);
            if (self.current_choice === clicked_choice) {
                self.current_choice = null;
            } else {
                self.current_choice = clicked_choice;
            }

            options.widget.find("." + options.checked_button_class).each(function () {
                if ($(this).attr(options.value_attr) === clicked_choice) { return; }
                self.check($(this));
            });
            self.check($clicked);
            self.post_click_action();
            e.preventDefault();
        };

        options.widget.find(questions_module.globals.button_selector).click(this.click);

        this.choice = function () { return self.current_choice; };
        this.chosen = function () { return self.current_choice !== null; };
        this.check = function(button) { button.toggleClass(options.default_button_class + " " + options.checked_button_class); };

        this.disable = function () {
            options.widget.find(questions_module.globals.button_selector)
                .addClass('btn-no-hover')
                .off('click', self.click);
        };

        this.set_choice = function (choice) {
            if (!choice) return;
            if (typeof choice === "number" || choice instanceof Number) {
                choice = choice.toString();
            }
            options.widget.find("." + options.checked_button_class).each(function () {
                if ($(this).attr(options.value_attr) === choice) return;
                self.check($(this));
            });
            options.widget.find(".btn").each(function () {
                if ($(this).attr(options.value_attr) !== choice || $(this).hasClass(options.checked_button_class)) return;
                self.check($(this));
            });
            self.current_choice = choice;
        };
    };

    return questions_module;
}(Questions || {}, jQuery));
