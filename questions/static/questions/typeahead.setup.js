$(document).ready(function () {
    $(".typeahead").each(function (i, e) {
        $element = $(e);
        var prefetch_url = $element.attr("data-prefetch");

        if (prefetch_url) {
            options = {
                datumTokenizer: Bloodhound.tokenizers.obj.whitespace("value"),
                queryTokenizer: Bloodhound.tokenizers.whitespace,
                prefetch: {
                    url: prefetch_url,
                    filter: function (list) {
                        return $.map(list, function(v) { return { "value": v }; });
                    }
                }
            };
            data_source = new Bloodhound(options);
            data_source.clearPrefetchCache();
            data_source.initialize();

            $element.typeahead({
              hint: true,
              highlight: true,
              minLength: 1
            },
            {
              name: 'data_source',
              displayKey: 'value',
              source: data_source.ttAdapter()
            });
        }
    });
});
