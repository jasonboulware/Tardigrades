(function() {
    (function($) {
        return $.fn.ajaxChosen = function(options, callback) {
            var select;
            select = this;
            this.chosen().change(function() {
                $select = $(this);

                // New message
                if ($('body').hasClass('new-message')) {
                    $option = $('option:selected', $select);
                    if ($select.attr('id') === 'id_user') {
                        if ($option.val() !== '') {
                            $('div.team, div.or').addClass('disabled');
                            $('select#id_team').attr('disabled', 'disabled').trigger('liszt:updated');
                            $('select#id_language').attr('disabled', 'disabled').trigger('liszt:updated');
                        } else {
                            $('div.team, div.or').removeClass('disabled');
                            $('select#id_team').removeAttr('disabled').trigger('liszt:updated');
                            $('select#id_language').removeAttr('disabled').trigger('liszt:updated');
                        }
                    }
                }
            });
            return this.next('.chzn-container').find(".chzn-search > input").bind('keyup', function() {
                var field, val;
                val = $.trim($(this).attr('value'));
                if (val === $(this).data('prevVal')) {
                    return false;
                }
                if (val.length < 1) {
                    $sel = $('ul.chzn-results', select.next('.chzn-container'));
                    $lis = $sel.children('li');

                    if ($lis.length === 1) {
                        $lis.remove();
                    }

                    if ($('li.no-results', $sel).length === 0) {
                        $sel.prepend($('<li class="no-results">Begin typing to search.</li>'));
                    }

                    $lis.removeClass('highlighted');

                    return false;
                }
                $(this).data('prevVal', val);
                field = $(this);
                options.data = {
                    term: val,

                    // New tasks.
                    task_type: $('select#id_type option:selected').val(),
                    team_video: $('input[name="id_team_video"]').val(),
                    task_lang: $('input[name="language"]').val()

                };
                if (!options.data['task_type']) {

                    // Existing tasks.
                    options.data = {
                        term: val,
                        task_type: field.parents('form.assign-form').children('input[name="task_type"]').val(),
                        team_video: field.parents('form.assign-form').children('input[name="task_video"]').val(),
                        task: field.parents('form.assign-form').children('input[name="task"]').val(),
                        task_lang: field.parents('form.assign-form').children('input[name="task_lang"]').val()
                    }

                }
                if (typeof success !== "undefined" && success !== null) {
                    success;
                } else {
                    success = options.success;
                }
                options.success = function(data) {
                    var items;
                    if (!(data != null)) {
                        return;
                    }
                    select.find('option').each(function() {
                        if (!$(this).is(":selected")) {
                            return $(this).remove();
                        }
                    });
                    items = callback(data);
                    $.each(items, function(value, text) {
                        return $("<option />", {'value': value, 'html': text}).appendTo(select);
                    });
                    var rem = field.attr('value');

                    select.trigger("liszt:updated");
                    field.attr('value', rem);
                    field.keyup();

                    if (typeof success !== "undefined" && success !== null) {
                        field.keyup();
                        return success();
                    }
                };
                if (window.chosenAjaxInProgress) {
                    window.chosenAjaxInProgress.abort();
                }
                window.chosenAjaxInProgress = $.ajax(options);
                return window.chosenAjaxInProgress;
            });
        };
    })(jQuery);
}).call(this);
