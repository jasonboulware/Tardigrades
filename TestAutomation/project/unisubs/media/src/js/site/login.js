
$(function() {
    if(window.location.hash == '#create-account') {
        var formTop = $('#create-account').offset().top;
        var pageStart = $('body').css('padding-top').replace('px', '');
        $('html, body').animate({scrollTop: formTop - pageStart - 20}, 300);
    }
});

