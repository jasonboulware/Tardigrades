$(document).ready(function() {
    $('input.enable-field').change(function() {
        var $field = $('#' + $(this).data('field'));
        if($(this).attr('checked')) {
            $field.attr('disabled', null);
        } else {
            $field.attr('disabled', 'disabled');
        }
    });
});
