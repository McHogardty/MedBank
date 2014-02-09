var Questions = (function (questions_module, $) {
    questions_module.SplashScreen = function (to_show, to_hide) {
        set_up_class = "pre-blur";
        transition_class = "blur";
        this.show = function () {
            $.each(to_show, function (i, selector) {$(selector).fadeIn(600); });
            $.each(to_hide, function (i, selector) {
                $(selector).addClass(set_up_class);
                $(selector).addClass(transition_class);
            });
        };

        this.hide = function () {
            $.each(to_show, function (i, selector) { $(selector).fadeOut(600); });
            $.each(to_hide, function (i, selector) { $(selector).removeClass(transition_class); });

             setTimeout(function () {
                 $.each(to_hide, function (i, selector) { $(selector).removeClass(set_up_class); });
            }, 600);
        };
    };

    return questions_module;
}(Questions || {}, jQuery));

var Questions = (function (questions_module, $) {
    questions_module.SplashScreenManager = function (screen_class, specifying_attribute, attributes, to_hide) {
        var screens = {};
        var self = this;

        this.generate_selector = function (attr) { return screen_class + '[' + specifying_attribute + '="' + attr + '"]'; };
        this.show = function (attr) { screens[attr].show(); };
        this.hide = function (attr) { screens[attr].hide(); };

        $.each(attributes, function (i, attr) { screens[attr] = new questions_module.SplashScreen([self.generate_selector(attr),], to_hide); });
    };

    return questions_module;
}(Questions || {}, jQuery));