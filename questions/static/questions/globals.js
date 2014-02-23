var Questions = (function (questions_module, $) {
    questions_module.globals = questions_module.globals || {};
    $.extend(questions_module.globals, {
        default_button_class: "btn-default",
        checked_button_class: "btn-success",
        unsuccessful_button_class: "btn-danger",
        active_class: "active",
        transition_setup_class: "pre-blur",
        transition_class: "blur",
    });

    return questions_module;
}(Questions || {}, jQuery));
