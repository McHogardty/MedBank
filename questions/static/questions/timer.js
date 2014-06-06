var Questions = (function (questions_module, $) {
    questions_module.Timer = function (options) {
        this.start_time = 0;
        this.elapsed = 0;
        this.is_paused = false;
        var self = this;
        this.timer_id = 0;

        options = $.extend({
            is_global: true,
            callback: null,
        }, options);

        if (options.is_global) {
            $(".timer button").click(function (e) {
                $b = $(this);
                self.complete_pause();
                if (options.callback) { options.callback(); }
                if (self.is_paused) {
                    $b.html("Resume");
                } else {
                    $b.html("Pause");
                }
                e.preventDefault();
            });
        }

        this.running = function () { return self.timer_id !== 0; };
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

        this.check_time = function () {
            if (self.is_paused) return;

            diff = self.time_since_beginning() + self.elapsed;
            self.render_time(diff);
        };
    };

    return questions_module;
}(Questions || {}, jQuery));