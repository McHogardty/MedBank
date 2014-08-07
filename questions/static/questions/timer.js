var Questions = (function (questions_module, $) {

    questions_module.globals = questions_module.globals || {};

    questions_module.globals = $.extend(questions_module.globals, {
        quiz_pause_event: "quiz.pause",
        quiz_resume_event: "quiz.resume",
        deactivate_pause: "quiz.deactivate_pause",
        reactivate_pause: "quiz.reactivate_pause",
    });

    questions_module.Timer = function (options) {
        this.start_time = 0;
        this.elapsed = 0;
        this.is_paused = false;
        var self = this;
        this.timer_id = 0;
        this.started = false;
        this.total = 0;

        options = $.extend({
            is_global: true,
        }, options);

        this.pause_button_callback = function (e) {
            $b = $(this);
            self.pause();
            if (self.is_paused) {
                $.event.trigger(questions_module.globals.quiz_pause_event);
                $b.html("Resume");
            } else {
                $.event.trigger(questions_module.globals.quiz_resume_event);
                $b.html("Pause");
            }
            e.preventDefault();
        };

        this.running = function () {
            return self.timer_id !== 0;
        };

        this.paused = function () {
            return self.is_paused;
        };

        this.pause = function () {
            if (self.is_paused) {
                self.restart();
            } else {
                self.elapsed += self.time_since_beginning();
            }
            self.is_paused = !self.is_paused;
        };

        this.resume = function () {
            if (self.is_paused) {
                self.restart();
                self.is_paused = !self.is_paused;
            }
        };
        
        this.reset = function () {
            self.elapsed = 0;
            self.restart();
        };

        this.restart = function () {
            self.start_time = new Date().getTime();
        };

        this.time_since_beginning = function () {
            if (self.paused()) return 0;

            return new Date().getTime() - self.start_time;
        };

        this.start = function () {
            self.started = true;
            self.reset();
            self.timer_id = window.setInterval(self.check_time, 100);
            self.is_paused = false;
        };

        this.stop_timing = function () {
            window.clearInterval(self.timer_id);
            self.timer_id = 0;
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

        this.has_started = function () {
            return this.started;
        };

        this.current_lap_length = function () {
            if (!self.has_started()) return 0;
            return self.time_since_beginning() + self.elapsed;
        };

        this.save = function () {
            self.total += self.current_lap_length();
        };

        this.lap = function () {
            self.save();
            self.pause();
            self.reset();
            self.resume();
        };

        this.check_time = function () {
            if (!options.is_global) return;
            if (self.is_paused) return;

            diff = self.time_since_beginning() + self.elapsed;
            self.render_time(diff);
        };

        if (options.is_global) {
            $(".timer button").click(this.pause_button_callback);
            $(document).on(questions_module.globals.deactivate_pause, function () { $(".timer button").prop("disabled", true); });
            $(document).on(questions_module.globals.reactivate_pause, function () { $(".timer button").prop("disabled", false); });
        }


    };

    return questions_module;
}(Questions || {}, jQuery));