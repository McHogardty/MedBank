var Questions = (function (questions_module, $) {
    questions_module.globals = questions_module.globals || {};
    $.extend(questions_module.globals, {
        default_button_class: "btn-default",
        unsuccessful_button_class: "btn-danger",
        checked_button_class: "btn-success",
        active_class: "active",
        transition_setup_class: "pre-blur",
        transition_class: "blur",
        button_selector: ".btn",
    });

    return questions_module;
}(Questions || {}, jQuery));
