var Questions = (function (questions_module, $) {
    questions_module.globals = questions_module.globals || {};

    questions_module.SplashScreen = function (options) {
        options = $.extend({
            to_show: [],
            to_hide: [],
            to_fade_out: [],
        }, options);

        this.show = function () {
            $.each(options.to_show, function (i, selector) {$(selector).fadeIn(600); });
            $.each(options.to_hide, function (i, selector) {
                $(selector).addClass(questions_module.globals.transition_setup_class);
                $(selector).addClass(questions_module.globals.transition_class);
            });
            $.each(options.to_fade_out, function (i, selector) { $(selector).fadeOut(600); });
        };

        this.hide = function () {
            $.each(options.to_show, function (i, selector) { $(selector).fadeOut(600); });
            $.each(options.to_hide, function (i, selector) {
                $(selector).addClass(questions_module.globals.transition_setup_class);
                $(selector).removeClass(questions_module.globals.transition_class);
            });
            $.each(options.to_fade_out, function (i, selector) { $(selector).fadeIn(600); });

             setTimeout(function () {
                 $.each(options.to_hide, function (i, selector) { $(selector).removeClass(questions_module.globals.transition_setup_class); });
            }, 600);
        };
        this.hide_immediately = function () {
            $.each(options.to_show, function (i, selector) { $(selector).fadeOut(0); });
            $.each(options.to_hide, function (i, selector) {
                $(selector).removeClass(questions_module.globals.transition_setup_class);
                $(selector).removeClass(questions_module.globals.transition_class);
            });
            $.each(options.to_fade_out, function (i, selector) { $(selector).fadeIn(0); });
        };
    };

    return questions_module;
}(Questions || {}, jQuery));

var Questions = (function (questions_module, $) {
    questions_module.SplashScreenManager = function (options) {
        var screens = {};
        var self = this;

        options = $.extend({
            screen_class: "",
            specifying_attribute: "",
            attributes: [],
            to_hide: [],
            to_fade_out: [],
        }, options);

        this.generate_selector = function (attr) { return options.screen_class + '[' + options.specifying_attribute + '="' + attr + '"]'; };
        this.show = function (attr) { screens[attr].show(); };
        this.hide = function (attr) { screens[attr].hide(); };

        $.each(options.attributes, function (i, attr) { screens[attr] = new questions_module.SplashScreen({
            to_show: [self.generate_selector(attr),],
            to_hide: options.to_hide,
            to_fade_out: options.to_fade_out,
        }); });
    };

    return questions_module;
}(Questions || {}, jQuery));